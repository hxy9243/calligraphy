"""Storage policy regression tests; isolated databases and synthetic artifacts only."""
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from backend.app import app
from backend.database import Database, SavedWorkLimitError
from backend.retention import DEFAULT_RETENTION_SECONDS, job_share_token
from backend.worker import cleanup_expired_outputs


class StoragePolicyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.url = f"sqlite:///{self.tmp.name}/jobs.db"
        self.db = Database(self.url)
        self.config = patch.dict(os.environ)
        self.config.start()
        self.addCleanup(self.config.stop)
        os.environ.pop('CALLIGRAPHY_RETENTION_SECONDS', None)
        self.db_patch = patch('backend.database._DB_INSTANCE', self.db)
        self.db_patch.start()
        self.addCleanup(self.db_patch.stop)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)
        self.client.get('/api/jobs')
        self.session = self.client.cookies['calligraphy_session']

    def create(self, job_id, status='succeeded', job_type='render', db=None, session=None, path=None):
        return (db or self.db).create_job(job_id, session or self.session, job_type,
                                        job_id, 'kai', {}, status=status,
                                        output_path=str(path) if path else None)

    def fill(self, count):
        for n in range(count):
            self.create(f'work-{n}')

    def quota(self):
        return self.client.get('/api/jobs').json()['storage_quota']

    def test_default_sixty_days_and_quota_contract(self):
        self.assertEqual(DEFAULT_RETENTION_SECONDS, 60 * 86400)
        self.assertEqual(self.quota(), {'used': 0, 'limit': 30, 'scope': 'browser_session'})
        for status in ('queued', 'rendering', 'running', 'succeeded', 'failed'):
            self.create(status, status=status)
        self.create('still', job_type='preview')
        self.assertEqual(self.quota()['used'], 5)
        self.assertEqual(self.client.get('/api/jobs').json()['retention_seconds'], 60 * 86400)

    def test_concurrent_independent_connections_cannot_overfill_last_slot(self):
        self.fill(29)
        databases = [Database(self.url) for _ in range(8)]
        start = threading.Barrier(len(databases))
        def save(index):
            start.wait(timeout=10)
            try:
                if index % 2:
                    databases[index].enqueue_render(f'new-{index}', self.session, f'text-{index}', 'kai', {})
                else:
                    self.create(f'new-{index}', db=databases[index], job_type='preview', status='rendering')
                return 'saved'
            except SavedWorkLimitError:
                return 'full'
        with ThreadPoolExecutor(max_workers=len(databases)) as pool:
            results = list(pool.map(save, range(len(databases))))
        self.assertEqual(results.count('saved'), 1)
        self.assertEqual(results.count('full'), 7)
        self.assertEqual(self.quota()['used'], 30)

    def test_full_quota_allows_dedup_but_not_new_work_and_isolates_sessions(self):
        original = self.db.enqueue_render('active', self.session, '山水', 'kai', {})
        self.fill(29)
        duplicate = Database(self.url).enqueue_render('duplicate', self.session, '山水', 'kai', {})
        self.assertEqual(duplicate['job_id'], original['job_id'])
        self.assertIsNone(self.db.get_job('duplicate'))
        with self.assertRaises(SavedWorkLimitError):
            self.db.enqueue_render('new', self.session, '新', 'kai', {})
        with self.assertRaises(SavedWorkLimitError):
            self.create('new-still', job_type='preview')
        self.create('other-owner', session='independent-session')
        self.assertEqual(self.quota()['used'], 30)

    def test_failure_and_owner_deletion_release_slots_but_foreign_deletion_does_not(self):
        self.fill(30)
        self.assertEqual(self.db.delete_history_job('work-0', 'foreign-session'), 'missing')
        self.assertEqual(self.quota()['used'], 30)
        self.db.update_job('work-0', status='failed', completed=True)
        self.assertEqual(self.quota()['used'], 29)
        self.create('after-failure')
        self.assertEqual(self.db.delete_history_job('work-1', self.session), 'deleted')
        self.create('after-delete')
        self.assertEqual(self.quota()['used'], 30)

    def test_late_success_cannot_reacquire_a_released_slot_at_capacity(self):
        self.create('failed-job', status='failed')
        self.fill(30)
        for status in ('queued', 'rendering', 'running', 'succeeded'):
            with self.subTest(status=status), self.assertRaises(SavedWorkLimitError):
                Database(self.url).update_job('failed-job', status=status, completed=True)
            self.assertEqual(self.db.get_job('failed-job')['status'], 'failed')
            self.assertEqual(self.quota()['used'], 30)
        self.db.delete_history_job('work-0', self.session)
        self.db.update_job('failed-job', status='succeeded', completed=True)
        self.assertEqual(self.quota()['used'], 30)

    def test_finite_share_expires_at_exact_deadline(self):
        artifact = Path(self.tmp.name) / 'finite.mp4'
        artifact.write_bytes(b'finite')
        self.create('finite', path=artifact)
        token = 'a' * 43
        deadline = time.time() + 600
        self.db.set_video_share('finite', self.session, hashlib.sha256(token.encode()).hexdigest(), deadline)
        viewer = TestClient(app)
        self.addCleanup(viewer.close)
        with patch('time.time', return_value=deadline - .001):
            response = viewer.post('/api/shares/finite/access', data={'token': token})
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()['expires_at'], deadline)
        with patch('time.time', return_value=deadline):
            response = viewer.post('/api/shares/finite/access', data={'token': token})
            self.assertEqual(response.status_code, 404)
            self.db.prune_history('2000-01-01T00:00:00+00:00')
        self.assertIsNone(self.db.get_video_share('finite'))
        self.assertIsNotNone(self.db.get_job('finite'))

    def test_pre_upgrade_jobs_without_live_share_get_issuance_marker(self):
        self.create('previously-revoked')
        # Emulate the old schema: it could not distinguish never-shared jobs
        # from revoked shares after restart. No token is stored in this fixture.
        with self.db._get_sqlite_conn() as conn:
            conn.execute('DROP TABLE video_share_issuance')
        migrated = Database(self.url)
        self.assertIsNone(migrated.get_video_share('previously-revoked'))
        row = migrated._get_sqlite_conn().execute(
            'SELECT job_id FROM video_share_issuance WHERE job_id = ?',
            ('previously-revoked',),
        ).fetchone()
        self.assertEqual(row['job_id'], 'previously-revoked')
        was_issued = []
        def issue_token(issued):
            was_issued.append(issued)
            return 'b' * 43
        migrated.set_video_share('previously-revoked', self.session, None, issue_token=issue_token)
        self.assertEqual(was_issued, [True])
        self.assertTrue(migrated.get_video_share('previously-revoked')['is_permanent'])

    def test_api_rejects_both_creation_endpoints_before_rendering_at_capacity(self):
        self.fill(30)
        with patch('backend.app.execute_job') as execute, patch('backend.app.get_runner') as runner:
            for route in ('/api/previews', '/api/renders'):
                response = self.client.post(route, json={'text': '山水', 'style': 'kai'})
                self.assertEqual(response.status_code, 409, response.text)
                self.assertIn('30', response.text)
            execute.assert_not_called()
            runner.assert_not_called()
        self.assertEqual(self.quota()['used'], 30)
        self.assertEqual(self.db._get_sqlite_conn().execute('SELECT COUNT(*) FROM creation_events').fetchone()[0], 0)

    def test_sharing_at_capacity_consumes_no_extra_slot_and_survives_reopen(self):
        root = Path(self.tmp.name) / 'outputs'
        (root / 'videos').mkdir(parents=True)
        artifact = root / 'videos' / 'one.mp4'
        artifact.write_bytes(b'synthetic-video')
        self.create('one', path=artifact)
        ordinary = root / 'videos' / 'ordinary.mp4'
        ordinary.write_bytes(b'ordinary-video')
        self.create('ordinary', path=ordinary)
        self.fill(28)
        response = self.client.post('/api/jobs/one/share-link')
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIsNone(response.json()['expires_at'])
        self.assertTrue(response.json()['is_permanent'])
        token = response.json()['url'].split('.')[-1]
        second = Database(self.url)
        share = second.get_video_share('one')
        self.assertEqual(share['token_hash'], hashlib.sha256(token.encode()).hexdigest())
        self.assertIsNone(share['expires_at'])
        self.assertTrue(share['is_permanent'])
        self.assertEqual(self.quota()['used'], 30)
        # A fresh interpreter cannot see an in-memory instance or connection.
        reopened = subprocess.run(
            [sys.executable, '-c',
             'import json,sys; from pathlib import Path; from backend.database import Database; '
             'db=Database(sys.argv[1]); job=db.get_job("one"); ordinary=db.get_job("ordinary"); '
             'print(json.dumps({"share":db.get_video_share("one"), '
             '"artifact":Path(job["output_path"]).read_bytes().decode(), '
             '"owner":job["session_id"], "ordinary":ordinary, '
             '"ordinary_artifact":Path(ordinary["output_path"]).read_bytes().decode(), '
             '"ordinary_share":db.get_video_share("ordinary")}))', self.url],
            check=True, capture_output=True, text=True, timeout=20,
        )
        persisted = json.loads(reopened.stdout)
        self.assertEqual(persisted['share'], share)
        self.assertEqual(persisted['artifact'], 'synthetic-video')
        self.assertEqual(persisted['owner'], self.session)
        self.assertEqual(persisted['ordinary']['session_id'], self.session)
        self.assertEqual(persisted['ordinary']['text'], 'ordinary')
        self.assertEqual(persisted['ordinary']['status'], 'succeeded')
        self.assertEqual(persisted['ordinary_artifact'], 'ordinary-video')
        self.assertIsNone(persisted['ordinary_share'])
        future = time.time() + 25 * 365 * 86400
        with patch('backend.database._DB_INSTANCE', second), patch('time.time', return_value=future), patch('backend.worker.output_root', return_value=root):
            cleanup_expired_outputs(second)
            self.assertIsNotNone(second.get_job('one'))
            self.assertEqual(artifact.read_bytes(), b'synthetic-video')
            viewer = TestClient(app)
            self.addCleanup(viewer.close)
            access = viewer.post('/api/shares/one/access', data={'token': token})
            self.assertEqual(access.status_code, 200, access.text)
            self.assertIsNone(access.json()['expires_at'])
            self.assertTrue(access.json()['is_permanent'])
            self.assertEqual(viewer.get('/api/shares/one/video').content, b'synthetic-video')
        self.assertTrue(Database(self.url).get_video_share('one')['is_permanent'])

    def test_cleanup_sixty_day_boundary(self):
        root = Path(self.tmp.name) / 'outputs'
        (root / 'videos').mkdir(parents=True)
        completed = 1800000000.0
        deadline = completed + 60 * 86400
        artifact = root / 'videos' / 'boundary.mp4'
        artifact.write_bytes(b'boundary')
        self.create('boundary', path=artifact)
        os.utime(artifact, (completed, completed))
        with self.db._get_sqlite_conn() as conn:
            conn.execute('UPDATE jobs SET completed_at = ? WHERE job_id = ?',
                         (datetime.fromtimestamp(completed, timezone.utc).isoformat(), 'boundary'))
        with patch('backend.worker.output_root', return_value=root):
            with patch('time.time', return_value=deadline - .001):
                cleanup_expired_outputs(self.db)
                self.assertIsNotNone(self.db.get_job('boundary'))
                self.assertTrue(artifact.exists())
            with patch('time.time', return_value=deadline):
                cleanup_expired_outputs(self.db)
                self.assertIsNone(self.db.get_job('boundary'))
                self.assertFalse(artifact.exists())

    def test_legacy_over_quota_rows_are_preserved_on_reopen(self):
        self.fill(30)
        conn = self.db._get_sqlite_conn()
        with conn:
            conn.execute("INSERT INTO jobs SELECT 'legacy-extra',session_id,job_type,status,text,style,params_json,output_path,error_message,warning_message,progress,created_at,updated_at,completed_at,expires_at FROM jobs WHERE job_id='work-0'")
        second = Database(self.url)
        self.assertEqual(len(second.list_jobs(self.session)), 31)
        with self.assertRaises(SavedWorkLimitError):
            self.create('new-over-limit', db=second)
        self.assertIsNotNone(second.get_job('legacy-extra'))

    def test_legacy_live_link_survives_migration_and_never_shared_job_rotates_qr_token(self):
        active_artifact = Path(self.tmp.name) / 'legacy-active.mp4'
        never_artifact = Path(self.tmp.name) / 'legacy-never.mp4'
        active_artifact.write_bytes(b'legacy-active-video')
        never_artifact.write_bytes(b'legacy-never-video')
        self.create('legacy-active', path=active_artifact)
        self.create('legacy-never', path=never_artifact)
        old_token = 'c' * 43
        with self.db._get_sqlite_conn() as conn:
            conn.execute('DROP TABLE video_shares')
            conn.execute('CREATE TABLE video_shares (job_id TEXT PRIMARY KEY, token_hash TEXT NOT NULL, expires_at REAL NOT NULL)')
            conn.execute('INSERT INTO video_shares VALUES (?, ?, ?)',
                         ('legacy-active', hashlib.sha256(old_token.encode()).hexdigest(), time.time() + 600))
            conn.execute('DROP TABLE video_share_issuance')
        migrated = Database(self.url)
        viewer = TestClient(app)
        self.addCleanup(viewer.close)
        with patch('backend.database._DB_INSTANCE', migrated):
            access = viewer.post('/api/shares/legacy-active/access', data={'token': old_token})
            self.assertEqual(access.status_code, 200, access.text)
            self.assertTrue(access.json()['is_permanent'])
            self.assertIsNone(access.json()['expires_at'])
            self.assertEqual(viewer.get('/api/shares/legacy-active/video').content, b'legacy-active-video')
            old_qr_token = job_share_token('legacy-never')
            issued = self.client.post('/api/jobs/legacy-never/share-link')
            self.assertEqual(issued.status_code, 200, issued.text)
            fresh_token = issued.json()['url'].split('.')[-1]
            self.assertNotEqual(fresh_token, old_qr_token)
            self.assertEqual(viewer.post('/api/shares/legacy-never/access', data={'token': old_qr_token}).status_code, 404)
            self.assertEqual(viewer.post('/api/shares/legacy-never/access', data={'token': fresh_token}).status_code, 200)
            self.assertEqual(viewer.get('/api/shares/legacy-never/video').content, b'legacy-never-video')

    def test_legacy_share_migration_is_additive_idempotent_and_does_not_revive_expired(self):
        url = f'sqlite:///{self.tmp.name}/legacy.db'
        filename = Path(self.tmp.name) / 'legacy.db'
        now = time.time()
        with sqlite3.connect(filename) as conn:
            conn.execute('CREATE TABLE video_shares (job_id TEXT PRIMARY KEY, token_hash TEXT NOT NULL, expires_at REAL NOT NULL)')
            conn.executemany('INSERT INTO video_shares VALUES (?, ?, ?)',
                             [('active', 'active-digest', now + 600), ('expired', 'expired-digest', now - 1)])
        migrated = Database(url)
        active = migrated.get_video_share('active')
        expired = migrated.get_video_share('expired')
        self.assertTrue(active['is_permanent'])
        self.assertIsNone(active['expires_at'])
        self.assertEqual(active['token_hash'], 'active-digest')
        self.assertFalse(expired['is_permanent'])
        self.assertEqual(expired['expires_at'], now - 1)
        # Reopening never promotes a timed share created after migration.
        with migrated._get_sqlite_conn() as conn:
            conn.execute("UPDATE video_shares SET is_permanent = 0, expires_at = ? WHERE job_id = 'active'", (now + 100,))
        reopened = Database(url)
        self.assertFalse(reopened.get_video_share('active')['is_permanent'])
        self.assertEqual(reopened._get_sqlite_conn().execute('SELECT COUNT(*) FROM video_shares').fetchone()[0], 2)


if __name__ == '__main__':
    unittest.main()
