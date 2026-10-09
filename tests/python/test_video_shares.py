"""Share only synthetic MP4 fixtures; no real visitor content is accessed."""
import hashlib
import os
import tempfile
import time
import unittest
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlsplit

from fastapi.testclient import TestClient
from backend.app import app, ShareAccessLimiter, SHARE_COOKIE_NAME, shared_video_path
from backend.database import Database
from backend.worker import cleanup_expired_outputs


class VideoShareTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_url = f"sqlite:///{self.tmp.name}/jobs.db"
        self.db = Database(self.db_url)
        self.db_patch = patch('backend.database._DB_INSTANCE', self.db)
        self.db_patch.start()
        self.limit_patch = patch('backend.app._share_access_limiter', ShareAccessLimiter())
        self.limit_patch.start()
        self.owner = TestClient(app)
        self.viewer = TestClient(app)
        self.owner.get('/api/styles')
        self.session = self.owner.cookies['calligraphy_session']
        self.path = Path(self.tmp.name) / 'fixture.mp4'
        self.path.write_bytes(b'synthetic-video-' * 100)
        self.job('one')

    def tearDown(self):
        self.limit_patch.stop()
        self.db_patch.stop()
        self.owner.close()
        self.viewer.close()
        self.tmp.cleanup()

    def job(self, job_id, **kwargs):
        return self.db.create_job(job_id, self.session, kwargs.get('job_type', 'render'), 'private text', 'kai', {}, output_path=str(kwargs.get('path', self.path)), status=kwargs.get('status', 'succeeded'))

    def issue(self, job_id='one'):
        response = self.owner.post(f'/api/jobs/{job_id}/share-link')
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        url = urlsplit(data['url'])
        self.assertEqual(url.path, '/watch.html')
        self.assertFalse(url.query)
        self.assertFalse(url.netloc)
        self.assertLessEqual(data['expires_at'], time.time() + 72 * 3600)
        self.assertGreater(data['expires_at'], time.time() + 72 * 3600 - 5)
        self.assertIn('no-store', response.headers['cache-control'])
        token = url.fragment.split('.')[1]
        self.assertEqual(len(token), 43)
        return token, data

    def access(self, token, job_id='one', client=None, **kwargs):
        return (client or self.viewer).post(f'/api/shares/{job_id}/access', data={'token': token}, **kwargs)

    def video(self, job_id='one', **kwargs):
        return self.viewer.get(f'/api/shares/{job_id}/video', **kwargs)

    def assertUnavailable(self, response):
        self.assertEqual(response.status_code, 404, response.text)
        self.assertIn('no-store', response.headers['cache-control'])
        self.assertEqual(response.headers['referrer-policy'], 'no-referrer')
        self.assertNotIn('private text', response.text)

    def test_fresh_viewer_plays_and_downloads_only_the_shared_video(self):
        token, data = self.issue()
        self.assertEqual(self.db.get_video_share('one')['token_hash'], hashlib.sha256(token.encode()).hexdigest())
        response = self.access(token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['video_url'], '/api/shares/one/video')
        self.assertEqual(response.json()['expires_at'], data['expires_at'])
        self.assertNotIn(token, response.text)
        self.assertNotIn('calligraphy_session', response.headers['set-cookie'])
        cookie = response.headers['set-cookie']
        for attribute in ('HttpOnly', 'SameSite=strict', 'Path=/api/shares/one', 'Max-Age=', 'expires='):
            self.assertIn(attribute, cookie)
        self.assertNotIn('Secure', cookie)
        video = self.video()
        self.assertEqual(video.status_code, 200)
        self.assertEqual(video.content, self.path.read_bytes())
        self.assertEqual(video.headers['content-type'], 'video/mp4')
        self.assertNotIn('content-disposition', video.headers)
        self.assertNotIn('set-cookie', video.headers)
        attachment = self.video(params={'download': '1'})
        self.assertIn('attachment', attachment.headers['content-disposition'])
        self.assertEqual(attachment.content, video.content)
        for suffix in ('', '/video', '/download', '/image'):
            self.assertEqual(self.viewer.get('/api/jobs/one' + suffix).status_code, 404)
        self.assertEqual(self.viewer.get('/api/jobs').json()['jobs'], [])
        self.assertEqual(self.viewer.post('/api/jobs/one/share-link').status_code, 404)
        self.assertEqual(self.viewer.delete('/api/jobs/one/share-link').status_code, 404)

    def test_public_page_assets_access_and_media_never_create_owner_sessions(self):
        token, _ = self.issue()
        for path in ('/watch.html', '/watch.js', '/watch.css'):
            response = self.viewer.get(path)
            self.assertEqual(response.status_code, 200)
            self.assertNotIn('set-cookie', response.headers)
            self.assertEqual(response.headers['referrer-policy'], 'no-referrer')
            self.assertIn('no-store', response.headers['cache-control'])
        page = self.viewer.get('/watch.html')
        for directive in ("default-src 'none'", "connect-src 'self'", "media-src 'self'", "frame-ancestors 'none'", "base-uri 'none'"):
            self.assertIn(directive, page.headers['content-security-policy'])
        self.assertIn('autoplay=()', page.headers['permissions-policy'])
        self.access(token)
        self.video()
        self.assertNotIn('calligraphy_session', self.viewer.cookies)
        self.assertEqual(self.db._get_sqlite_conn().execute('SELECT COUNT(*) FROM sessions').fetchone()[0], 1)

    def test_owner_cookie_and_url_token_never_authorize_public_media(self):
        token, _ = self.issue()
        self.assertUnavailable(self.owner.get('/api/shares/one/video'))
        self.assertUnavailable(self.video(params={'token': token}))
        self.assertNotIn('calligraphy_session', self.viewer.cookies)
        response = self.viewer.post('/api/shares/one/access?token=' + token)
        self.assertUnavailable(response)
        self.assertNotIn(token, response.text)

    def test_cookie_scope_isolates_multiple_videos_and_wrong_capabilities(self):
        self.job('two')
        one, _ = self.issue()
        two, _ = self.issue('two')
        self.access(one)
        self.assertUnavailable(self.video('two'))
        self.assertUnavailable(self.access(one, 'two'))
        self.access(two, 'two')
        self.assertEqual(self.video().status_code, 200)
        self.assertEqual(self.video('two').status_code, 200)
        paths = {cookie.path for cookie in self.viewer.cookies.jar if cookie.name == SHARE_COOKIE_NAME}
        self.assertEqual(paths, {'/api/shares/one', '/api/shares/two'})
        self.assertUnavailable(self.viewer.get('/api/shares/two/video', headers={'Cookie': f'{SHARE_COOKIE_NAME}={one}'}))
        self.job('one-extra')
        self.assertUnavailable(self.video('one-extra'))

    def test_rotation_and_revocation_invalidate_previously_issued_cookies(self):
        old, _ = self.issue()
        self.access(old)
        token, _ = self.issue()
        self.assertUnavailable(self.video())
        self.assertUnavailable(self.access(old))
        self.assertEqual(self.access(token).status_code, 200)
        self.assertEqual(self.owner.delete('/api/jobs/one/share-link').status_code, 204)
        self.assertUnavailable(self.video())
        self.assertUnavailable(self.access(token))
        self.assertEqual(self.owner.delete('/api/jobs/one/share-link').status_code, 204)

    def test_expired_capability_missing_file_and_deleted_history_revalidate(self):
        token, _ = self.issue()
        self.access(token)
        self.db.set_video_share('one', self.session, hashlib.sha256(token.encode()).hexdigest(), time.time() - 1)
        self.assertUnavailable(self.video())
        self.assertUnavailable(self.access(token))
        token, _ = self.issue()
        self.access(token)
        self.path.unlink()
        self.assertUnavailable(self.video())
        self.assertUnavailable(self.access(token))
        self.path.write_bytes(b'fixture')
        token, _ = self.issue()
        self.access(token)
        self.assertEqual(self.owner.delete('/api/jobs/one').status_code, 204)
        self.assertIsNone(self.db.get_video_share('one'))
        self.assertUnavailable(self.video())
        self.assertUnavailable(self.access(token))

    def test_only_completed_real_mp4_artifacts_can_be_shared(self):
        for state in ('queued', 'rendering', 'running', 'failed'):
            self.job(state, status=state)
            self.assertUnavailable(self.owner.post(f'/api/jobs/{state}/share-link'))
        self.job('preview', job_type='preview')
        self.assertUnavailable(self.owner.post('/api/jobs/preview/share-link'))
        for name, path in [('nonvideo', self.path.with_suffix('.svg')), ('missing', self.path.parent / 'missing.mp4')]:
            self.job(name, path=path)
            self.assertUnavailable(self.owner.post(f'/api/jobs/{name}/share-link'))
        symlink = self.path.parent / 'link.mp4'
        symlink.symlink_to(self.path)
        self.job('symlink', path=symlink)
        self.assertUnavailable(self.owner.post('/api/jobs/symlink/share-link'))
        token, _ = self.issue()
        self.access(token)
        self.db.update_job('one', status='failed')
        self.assertUnavailable(self.video())
        self.assertUnavailable(self.access(token))

    def test_share_lease_extends_ordinary_retention_without_resurrecting_expired_files(self):
        old = time.time() - 86350
        os.utime(self.path, (old, old))
        token, data = self.issue()
        self.assertGreater(data['expires_at'], time.time() + 72 * 3600 - 5)
        self.access(token)
        old = time.time() - 86401
        os.utime(self.path, (old, old))
        self.assertEqual(self.video().status_code, 200)
        token, _ = self.issue()  # An active lease can be rotated after the first day.
        self.access(token)
        self.owner.delete('/api/jobs/one/share-link')
        self.assertUnavailable(self.video())
        self.assertUnavailable(self.owner.post('/api/jobs/one/share-link'))
        os.utime(self.path, None)
        with patch.dict(os.environ, {'CALLIGRAPHY_RETENTION_SECONDS': '30'}):
            token, data = self.issue()
            self.assertGreater(data['expires_at'], time.time() + 72 * 3600 - 5)
        with self.db._get_sqlite_conn() as conn:
            conn.execute('UPDATE jobs SET completed_at = ?, expires_at = ? WHERE job_id = ?', (
                datetime.now(timezone.utc).isoformat(), datetime.fromtimestamp(time.time() + 10, timezone.utc).isoformat(), 'one'))
        token, data = self.issue()
        self.assertGreater(data['expires_at'], time.time() + 72 * 3600 - 5)
        self.access(token)
        with self.db._get_sqlite_conn() as conn:
            conn.execute('UPDATE jobs SET completed_at = ? WHERE job_id = ?', (datetime.fromtimestamp(time.time() - 86401, timezone.utc).isoformat(), 'one'))
        self.assertEqual(self.video().status_code, 200)
        self.owner.delete('/api/jobs/one/share-link')
        self.assertUnavailable(self.owner.post('/api/jobs/one/share-link'))

    def test_separate_export_tokens_and_lifetimes_remain_unchanged(self):
        exported = self.owner.post('/api/jobs/one/export-link').json()
        export_token = urlsplit(exported['url']).fragment.split('.')[1]
        share_token, shared = self.issue()
        self.assertLessEqual(exported['expires_at'], time.time() + 600)
        self.assertGreater(shared['expires_at'], exported['expires_at'] + 1000)
        self.assertUnavailable(self.access(export_token))
        self.assertEqual(self.viewer.post('/api/exports/one/download', data={'token': share_token}).status_code, 404)
        self.owner.delete('/api/jobs/one/share-link')
        self.assertEqual(self.viewer.post('/api/exports/one/download', data={'token': export_token}).status_code, 200)
        share_token, _ = self.issue()
        self.owner.delete('/api/jobs/one/export-link')
        self.assertEqual(self.access(share_token).status_code, 200)

    def test_native_ranges_head_and_invalid_ranges(self):
        token, _ = self.issue()
        self.access(token)
        size = self.path.stat().st_size
        for header, expected in [('bytes=5-19', self.path.read_bytes()[5:20]), ('bytes=-10', self.path.read_bytes()[-10:])]:
            response = self.video(headers={'Range': header})
            self.assertEqual(response.status_code, 206)
            self.assertEqual(response.content, expected)
            self.assertIn('content-range', response.headers)
            self.assertEqual(response.headers['accept-ranges'], 'bytes')
        head = self.viewer.head('/api/shares/one/video')
        self.assertEqual(head.status_code, 200)
        self.assertEqual(head.content, b'')
        self.assertEqual(int(head.headers['content-length']), size)
        self.assertEqual(self.video(headers={'Range': f'bytes={size + 1}-'}).status_code, 416)
        self.owner.delete('/api/jobs/one/share-link')
        self.assertEqual(self.viewer.head('/api/shares/one/video').status_code, 404)

    def test_ten_minute_export_of_shared_retained_video_rechecks_its_lease(self):
        token, shared = self.issue()
        self.access(token)
        self.age_job('one', self.path)
        exported = self.owner.post('/api/jobs/one/export-link')
        self.assertEqual(exported.status_code, 200)
        data = exported.json()
        self.assertLessEqual(data['expires_at'], time.time() + 600)
        export_token = urlsplit(data['url']).fragment.split('.')[1]
        self.assertNotEqual(export_token, token)
        self.assertUnavailable(self.access(export_token))
        path = '/api/exports/one/download'
        self.assertEqual(self.viewer.post(path, data={'token': export_token}).status_code, 200)
        self.owner.delete('/api/jobs/one/share-link')
        self.assertEqual(self.viewer.post(path, data={'token': export_token}).status_code, 404)
        self.assertEqual(self.owner.post('/api/jobs/one/export-link').status_code, 404)

    def test_bounded_body_validation_and_generic_errors_never_echo_tokens(self):
        token, _ = self.issue()
        path = '/api/shares/one/access'
        bodies = [b'', b'token=', b'token=a&token=b', b'token=' + token.encode() + b'&extra=x', b'token=' + b'a' * 1024, b'\xff', b'token=%00', b'token=' + b'!' * 43]
        for body in bodies:
            response = self.viewer.post(path, content=body, headers={'content-type': 'application/x-www-form-urlencoded'})
            self.assertUnavailable(response)
            self.assertNotIn(token, response.text)
        self.assertUnavailable(self.viewer.post(path, json={'token': token}))
        self.assertUnavailable(self.access('bad'))
        self.assertUnavailable(self.access(token, 'a' * 65))
        self.assertUnavailable(self.access(token, 'bad.name'))
        for method in ('GET', 'PUT', 'DELETE'):
            response = self.viewer.request(method, path)
            self.assertIn(response.status_code, (404, 405))
            self.assertNotIn('set-cookie', response.headers)

    def test_cross_origin_exchange_and_management_are_denied(self):
        token, _ = self.issue()
        for response in (
            self.access(token, headers={'Origin': 'https://evil.test'}),
            self.owner.post('/api/jobs/one/share-link', headers={'Origin': 'https://evil.test'}),
            self.owner.delete('/api/jobs/one/share-link', headers={'Origin': 'https://evil.test'}),
        ):
            self.assertEqual(response.status_code, 403)
            self.assertIn('no-store', response.headers['cache-control'])
            self.assertNotIn(token, response.text)
        self.assertEqual(self.access(token, headers={'Origin': 'http://testserver'}).status_code, 200)

    def test_https_and_configured_secure_cookies(self):
        token, _ = self.issue()
        secure = TestClient(app, base_url='https://testserver')
        self.addCleanup(secure.close)
        response = self.access(token, client=secure)
        self.assertIn('Secure', response.headers['set-cookie'])
        self.assertEqual(secure.get('/api/shares/one/video').status_code, 200)
        with patch.dict(os.environ, {'CALLIGRAPHY_SECURE_COOKIES': '1'}):
            self.assertIn('Secure', self.access(token).headers['set-cookie'])

    def test_restart_rotation_revocation_and_cleanup_across_database_instances(self):
        token, _ = self.issue()
        self.access(token)
        second = Database(self.db_url)
        with patch('backend.database._DB_INSTANCE', second):
            self.assertEqual(self.video().status_code, 200)
            self.assertFalse(second.set_video_share('one', 'wrong-owner', 'unused', time.time() + 60))
            self.assertFalse(second.revoke_video_share('one', 'wrong-owner'))
            self.assertEqual(self.video().status_code, 200)
            replacement = 'b' * 43
            self.assertTrue(second.set_video_share('one', self.session, hashlib.sha256(replacement.encode()).hexdigest(), time.time() + 60))
            self.assertUnavailable(self.video())
            self.assertEqual(self.access(replacement).status_code, 200)
            self.assertTrue(second.revoke_video_share('one', self.session))
            self.assertUnavailable(self.video())
        token, _ = self.issue()
        second.set_video_share('one', self.session, hashlib.sha256(token.encode()).hexdigest(), time.time() - 1)
        second.prune_history('2000-01-01T00:00:00+00:00')
        self.assertIsNone(self.db.get_video_share('one'))
        token, _ = self.issue()
        with second._get_sqlite_conn() as conn:
            conn.execute('DELETE FROM jobs WHERE job_id = ?', ('one',))
        second.prune_history('2000-01-01T00:00:00+00:00')
        self.assertIsNone(self.db.get_video_share('one'))

    def test_exchange_rate_limit_never_blocks_native_seeking(self):
        token, _ = self.issue()
        for _ in range(60):
            self.assertEqual(self.access(token).status_code, 200)
        blocked = self.access(token)
        self.assertEqual(blocked.status_code, 429)
        self.assertIn('retry-after', blocked.headers)
        self.assertIn('no-store', blocked.headers['cache-control'])
        for _ in range(65):
            self.assertEqual(self.video(headers={'Range': 'bytes=0-9'}).status_code, 206)

    def cleanup_fixture(self):
        root = Path(self.tmp.name) / 'outputs'
        (root / 'videos').mkdir(parents=True)
        destination = root / 'videos' / self.path.name
        self.path.rename(destination)
        self.path = destination
        self.db.update_job('one', output_path=str(self.path))
        return root

    def age_job(self, job_id, path, seconds=2 * 86400):
        old = time.time() - seconds
        os.utime(path, (old, old))
        with self.db._get_sqlite_conn() as conn:
            conn.execute('UPDATE jobs SET completed_at = ? WHERE job_id = ?', (datetime.fromtimestamp(old, timezone.utc).isoformat(), job_id))

    def test_active_share_preserves_only_its_video_and_history_during_cleanup(self):
        root = self.cleanup_fixture()
        token, data = self.issue()
        self.access(token)
        self.age_job('one', self.path)
        ordinary = root / 'videos' / 'ordinary.mp4'
        ordinary.write_bytes(b'ordinary')
        self.job('ordinary', path=ordinary)
        self.age_job('ordinary', ordinary)
        orphan = root / 'videos' / 'orphan.mp4'
        orphan.write_bytes(b'orphan')
        os.utime(orphan, (time.time() - 90000,) * 2)
        with patch('backend.worker.output_root', return_value=root):
            cleanup_expired_outputs(Database(self.db_url))
        self.assertTrue(self.path.exists())
        self.assertIsNotNone(self.db.get_job('one'))
        self.assertEqual(self.video().status_code, 200)
        self.assertIsNone(self.db.get_job('ordinary'))
        self.assertFalse(ordinary.exists())
        self.assertFalse(orphan.exists())
        # A full 72-hour lease is readable after ordinary 24-hour retention.
        with patch('backend.app.time.time', return_value=data['expires_at'] - 1):
            self.assertEqual(self.video().status_code, 200)
        with patch('backend.app.time.time', return_value=data['expires_at'] + 1):
            self.assertUnavailable(self.video())
            with patch('backend.worker.output_root', return_value=root):
                cleanup_expired_outputs(self.db)
        self.assertFalse(self.path.exists())
        self.assertIsNone(self.db.get_job('one'))
        self.assertIsNone(self.db.get_video_share('one'))

    def test_revocation_ends_extended_retention_and_cleanup_removes_old_video(self):
        root = self.cleanup_fixture()
        token, _ = self.issue()
        self.access(token)
        self.age_job('one', self.path)
        self.assertEqual(self.owner.delete('/api/jobs/one/share-link').status_code, 204)
        self.assertUnavailable(self.video())
        self.assertUnavailable(self.owner.post('/api/jobs/one/share-link'))
        with patch('backend.worker.output_root', return_value=root):
            cleanup_expired_outputs(self.db)
        self.assertFalse(self.path.exists())
        self.assertIsNone(self.db.get_job('one'))

    def test_deleted_history_removes_share_lease_and_orphan_is_cleaned_normally(self):
        root = self.cleanup_fixture()
        token, _ = self.issue()
        self.access(token)
        self.age_job('one', self.path)
        self.assertEqual(self.owner.delete('/api/jobs/one').status_code, 204)
        self.assertUnavailable(self.video())
        with patch('backend.worker.output_root', return_value=root):
            cleanup_expired_outputs(self.db)
        self.assertFalse(self.path.exists())
        self.assertIsNone(self.db.get_video_share('one'))

    def test_share_creation_reservation_wins_race_against_file_cleanup(self):
        root = self.cleanup_fixture()
        second = Database(self.db_url)
        validated = threading.Event()
        release = threading.Event()
        cleanup_started = threading.Event()

        def validate(job, previous):
            shared_video_path(job)
            validated.set()
            self.assertTrue(release.wait(5))

        def cleanup():
            cleanup_started.set()
            cleanup_expired_outputs(second)

        with patch('backend.worker.output_root', return_value=root), ThreadPoolExecutor(max_workers=2) as pool:
            creation = pool.submit(self.db.set_video_share, 'one', self.session, 'digest', time.time() + 72 * 3600, validate)
            try:
                self.assertTrue(validated.wait(5))
                # Simulate crossing the ordinary retention boundary after file
                # validation, while issuance still holds its write reservation.
                os.utime(self.path, (time.time() - 90000,) * 2)
                removal = pool.submit(cleanup)
                self.assertTrue(cleanup_started.wait(5))
                time.sleep(.05)
                self.assertFalse(removal.done())
            finally:
                release.set()
            self.assertTrue(creation.result(5))
            removal.result(5)
        self.assertTrue(self.path.exists())
        self.assertIsNotNone(self.db.get_video_share('one'))

    def test_cleanup_reservation_wins_race_and_no_dangling_share_is_issued(self):
        root = self.cleanup_fixture()
        self.age_job('one', self.path)
        second = Database(self.db_url)
        deleting = threading.Event()
        release = threading.Event()
        creation_started = threading.Event()
        validated = threading.Event()
        original_unlink = Path.unlink

        def unlink(path, *args, **kwargs):
            if path == self.path:
                deleting.set()
                self.assertTrue(release.wait(5))
            return original_unlink(path, *args, **kwargs)

        def create():
            creation_started.set()
            return second.set_video_share('one', self.session, 'digest', time.time() + 72 * 3600, lambda *_: validated.set())

        with patch('backend.worker.output_root', return_value=root), patch.object(Path, 'unlink', unlink), ThreadPoolExecutor(max_workers=2) as pool:
            removal = pool.submit(cleanup_expired_outputs, self.db)
            try:
                self.assertTrue(deleting.wait(5))
                creation = pool.submit(create)
                self.assertTrue(creation_started.wait(5))
                time.sleep(.05)
                self.assertFalse(creation.done())
                self.assertFalse(validated.is_set())
            finally:
                release.set()
            removal.result(5)
            self.assertFalse(creation.result(5))
        self.assertFalse(self.path.exists())
        self.assertIsNone(self.db.get_video_share('one'))


if __name__ == '__main__':
    unittest.main()
