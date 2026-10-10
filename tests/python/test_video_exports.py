"""Synthetic artifacts only: never create links to a user's private videos."""
import hashlib
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlsplit

from fastapi.testclient import TestClient
from backend.app import app, ShareAccessLimiter, EXPORT_COOKIE_NAME, SHARE_COOKIE_NAME
from backend.database import Database


class VideoExportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_url = f"sqlite:///{self.tmp.name}/jobs.db"
        self.db = Database(self.db_url)
        self.patch = patch('backend.database._DB_INSTANCE', self.db)
        self.patch.start()
        self.limit_patch = patch("backend.app._share_access_limiter", ShareAccessLimiter())
        self.limit_patch.start()
        self.owner = TestClient(app)
        self.other = TestClient(app)
        self.owner.get('/api/styles')
        self.session = self.owner.cookies['calligraphy_session']
        self.path = Path(self.tmp.name) / 'fixture.mp4'
        self.path.write_bytes(b'synthetic-video-' * 100)
        self.job('one')

    def tearDown(self):
        self.limit_patch.stop()
        self.patch.stop()
        self.owner.close()
        self.other.close()
        self.tmp.cleanup()

    def job(self, job_id, **kwargs):
        return self.db.create_job(job_id, self.session, kwargs.pop('job_type', 'render'), '永', 'kai', {}, output_path=str(kwargs.pop('path', self.path)), status=kwargs.pop('status', 'succeeded'))

    def issue(self, job_id='one'):
        response = self.owner.post(f'/api/jobs/{job_id}/export-link')
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        self.assertIn('no-store', response.headers['cache-control'])
        self.assertLessEqual(data['expires_at'], time.time() + 600)
        url = urlsplit(data['url'])
        self.assertEqual(url.path, '/export.html')
        self.assertFalse(url.query)
        return url.fragment.split('.')[1], data

    def download(self, token, job_id='one', **kwargs):
        return self.other.post(f'/api/exports/{job_id}/download', data={'token': token}, **kwargs)

    def test_cookie_free_download_is_one_artifact_only_and_private(self):
        token, _ = self.issue()
        self.assertEqual(len(token), 43)
        self.assertEqual(self.db.get_video_export('one')['token_hash'], hashlib.sha256(token.encode()).hexdigest())
        response = self.download(token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, self.path.read_bytes())
        self.assertEqual(response.headers['content-type'], 'video/mp4')
        self.assertIn('attachment', response.headers['content-disposition'])
        self.assertIn('no-store', response.headers['cache-control'])
        self.assertEqual(response.headers['referrer-policy'], 'no-referrer')
        self.assertNotIn('set-cookie', response.headers)
        for suffix in ('', '/video', '/download', '/image'):
            self.assertEqual(self.other.get('/api/jobs/one' + suffix).status_code, 404)
        self.assertEqual(self.other.post('/api/jobs/one/export-link').status_code, 404)
        self.assertEqual(self.other.delete('/api/jobs/one/export-link').status_code, 404)
        self.assertEqual(self.other.get('/api/jobs').json()['jobs'], [])

    def test_invalid_expired_rotated_wrong_job_and_revoked(self):
        old, _ = self.issue()
        token, _ = self.issue()
        self.assertEqual(self.download(old).status_code, 404)
        self.assertEqual(self.download('invalid').status_code, 404)
        self.job('two')
        self.assertEqual(self.download(token, 'two').status_code, 404)
        self.assertEqual(self.owner.delete('/api/jobs/one/export-link').status_code, 204)
        self.assertEqual(self.download(token).status_code, 404)
        token, _ = self.issue()
        self.db.set_video_export('one', self.session, hashlib.sha256(token.encode()).hexdigest(), time.time() - 1)
        expired = self.download(token)
        self.assertEqual(expired.status_code, 404)
        self.assertIn('no-store', expired.headers['cache-control'])

    def test_missing_unfinished_non_video_symlink_and_deleted_jobs(self):
        for state in ('queued', 'rendering', 'running', 'failed'):
            self.job(state, status=state)
            self.assertEqual(self.owner.post(f'/api/jobs/{state}/export-link').status_code, 404)
        self.job('preview', job_type='preview')
        self.assertEqual(self.owner.post('/api/jobs/preview/export-link').status_code, 404)
        wrong = self.path.with_suffix('.svg')
        wrong.write_text('<svg/>')
        self.job('wrong', path=wrong)
        self.assertEqual(self.owner.post('/api/jobs/wrong/export-link').status_code, 404)
        symlink = self.path.parent / 'link.mp4'
        symlink.symlink_to(self.path)
        self.job('symlink', path=symlink)
        self.assertEqual(self.owner.post('/api/jobs/symlink/export-link').status_code, 404)
        token, _ = self.issue()
        self.path.unlink()
        self.assertEqual(self.download(token).status_code, 404)
        self.assertEqual(self.owner.post('/api/jobs/one/export-link').status_code, 404)
        self.path.write_bytes(b'video')
        token, _ = self.issue()
        self.assertEqual(self.owner.delete('/api/jobs/one').status_code, 204)
        self.assertEqual(self.download(token).status_code, 404)
        self.assertIsNone(self.db.get_video_export('one'))

    def test_retention_bounds_and_restart_persistence(self):
        os.utime(self.path, (time.time() - 86350, time.time() - 86350))
        token, data = self.issue()
        self.assertLess(data['expires_at'], time.time() + 51)
        with patch('backend.database._DB_INSTANCE', Database(self.db_url)):
            self.assertEqual(self.download(token).status_code, 200)
        os.utime(self.path, (time.time() - 86401, time.time() - 86401))
        self.assertEqual(self.download(token).status_code, 404)
        self.assertEqual(self.owner.post('/api/jobs/one/export-link').status_code, 404)

    def test_rotation_and_revocation_across_database_instances_and_cleanup(self):
        token, _ = self.issue()
        second = Database(self.db_url)
        replacement = 'b' * 43
        self.assertFalse(second.set_video_export('one', 'wrong-owner', 'unused', time.time() + 600))
        self.assertEqual(self.download(token).status_code, 200)
        self.assertTrue(second.set_video_export('one', self.session, hashlib.sha256(replacement.encode()).hexdigest(), time.time() + 600))
        self.assertEqual(self.download(token).status_code, 404)
        self.assertEqual(self.download(replacement).status_code, 200)
        second.revoke_video_export('one')
        self.assertEqual(self.download(replacement).status_code, 404)
        token, _ = self.issue()
        second.set_video_export('one', self.session, hashlib.sha256(token.encode()).hexdigest(), time.time() - 1)
        second.prune_history('2000-01-01T00:00:00+00:00')
        self.assertIsNone(self.db.get_video_export('one'))
        token, _ = self.issue()
        second.update_job('one', status='failed')
        self.assertEqual(self.download(token).status_code, 404)

    def test_range_request_streams_native_attachment(self):
        token, _ = self.issue()
        response = self.download(token, headers={'Range': 'bytes=5-19'})
        self.assertEqual(response.status_code, 206)
        self.assertEqual(response.content, self.path.read_bytes()[5:20])
        self.assertEqual(response.headers['content-range'], f'bytes 5-19/{self.path.stat().st_size}')
        self.assertIn('attachment', response.headers['content-disposition'])

    def test_body_limits_methods_origin_and_landing_page(self):
        token, _ = self.issue()
        path = '/api/exports/one/download'
        self.assertEqual(self.other.get(path + '?token=' + token).status_code, 404)
        self.assertEqual(self.other.post(path, json={'token': token}).status_code, 404)
        self.assertEqual(self.other.post(path, data={'token': 'a' * 1024}).status_code, 404)
        self.assertEqual(self.other.post(path, content='token=a&token=b', headers={'content-type': 'application/x-www-form-urlencoded'}).status_code, 404)
        self.assertEqual(self.owner.post('/api/jobs/one/export-link', headers={'Origin': 'https://evil.test'}).status_code, 403)
        self.assertEqual(self.download(token, headers={'Origin': 'https://evil.test'}).status_code, 403)
        page = self.other.get('/export.html')
        self.assertEqual(page.status_code, 200)
        self.assertNotIn('set-cookie', page.headers)
        self.assertIn("form-action 'none'", page.headers['content-security-policy'])
        self.assertIn('no-store', page.headers['cache-control'])
        for asset in ('export.js', 'export.css'):
            self.assertNotIn('set-cookie', self.other.get('/' + asset).headers)

    def access(self, token, job_id='one', client=None, **kwargs):
        return (client or self.other).post(f'/api/exports/{job_id}/access', data={'token': token}, **kwargs)

    def video(self, job_id='one', **kwargs):
        return self.other.get(f'/api/exports/{job_id}/video', **kwargs)

    def test_artwork_viewer_exchanges_token_for_scoped_native_media(self):
        token, data = self.issue()
        response = self.access(token, headers={'Origin': 'http://testserver', 'Sec-Fetch-Site': 'same-origin'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'video_url': '/api/exports/one/video', 'expires_at': data['expires_at']})
        cookie = response.headers['set-cookie']
        for attribute in (EXPORT_COOKIE_NAME, 'HttpOnly', 'SameSite=strict', 'Path=/api/exports/one', 'Max-Age=', 'expires='):
            self.assertIn(attribute, cookie)
        self.assertNotIn(token, response.text)
        self.assertNotIn('calligraphy_session', cookie)
        self.assertEqual(self.video().content, self.path.read_bytes())
        self.assertNotIn('content-disposition', self.video().headers)
        download = self.video(params={'download': '1'})
        self.assertEqual(download.content, self.path.read_bytes())
        self.assertIn('attachment', download.headers['content-disposition'])
        self.assertIn('no-store', download.headers['cache-control'])
        self.assertEqual(download.headers['referrer-policy'], 'no-referrer')
        partial = self.video(headers={'Range': 'bytes=5-19'})
        self.assertEqual(partial.status_code, 206)
        self.assertEqual(partial.content, self.path.read_bytes()[5:20])
        self.assertEqual(self.other.head('/api/exports/one/video').status_code, 200)
        self.assertEqual(self.video(headers={'Range': 'bytes=99999-'}).status_code, 416)
        self.assertNotIn('calligraphy_session', self.other.cookies)
        self.assertIsNone(self.db.get_video_share('one'), 'access never upgrades to a 72-hour share')

    def test_export_viewer_isolation_no_owner_url_or_share_cookie_fallback(self):
        token, _ = self.issue()
        self.job('two')
        other_token, _ = self.issue('two')
        for suffix in ('/video', '/video?download=1', '/video?token=' + token):
            self.assertEqual(self.owner.get('/api/exports/one' + suffix).status_code, 404)
        self.assertEqual(self.access(token, 'two').status_code, 404)
        self.assertEqual(self.access(token).status_code, 200)
        self.assertEqual(self.video('two').status_code, 404)
        self.assertEqual(self.other.get('/api/shares/one/video').status_code, 404)
        self.assertEqual(self.access(other_token, 'two').status_code, 200)
        self.assertEqual(self.video().status_code, 200)
        self.assertEqual(self.video('two').status_code, 200)
        paths = {cookie.path for cookie in self.other.cookies.jar if cookie.name == EXPORT_COOKIE_NAME}
        self.assertEqual(paths, {'/api/exports/one', '/api/exports/two'})
        self.assertEqual(self.video('two', headers={'Cookie': f'{EXPORT_COOKIE_NAME}={token}'}).status_code, 404)
        self.assertEqual(self.video(headers={'Cookie': f'{SHARE_COOKIE_NAME}={token}'}).status_code, 404)
        shared = self.owner.post('/api/jobs/one/share-link').json()
        share_token = urlsplit(shared['url']).fragment.split('.')[1]
        self.assertEqual(self.access(share_token).status_code, 404)
        self.assertEqual(self.other.post('/api/shares/one/access', data={'token': token}).status_code, 404)
        for suffix in ('', '/video', '/download', '/image'):
            self.assertEqual(self.other.get('/api/jobs/one' + suffix).status_code, 404)
        self.assertEqual(self.other.get('/api/jobs').json()['jobs'], [])

    def test_native_media_rechecks_rotation_revocation_expiry_retention_and_deletion(self):
        token, _ = self.issue()
        self.access(token)
        replacement, _ = self.issue()
        self.assertEqual(self.video().status_code, 404)
        self.assertEqual(self.access(token).status_code, 404)
        self.access(replacement)
        self.assertEqual(self.video().status_code, 200)
        self.owner.delete('/api/jobs/one/export-link')
        self.assertEqual(self.video().status_code, 404)
        token, _ = self.issue()
        self.access(token)
        self.db.set_video_export('one', self.session, hashlib.sha256(token.encode()).hexdigest(), time.time() - 1)
        self.assertEqual(self.video().status_code, 404)
        token, _ = self.issue()
        self.access(token)
        os.utime(self.path, (time.time() - 86401, time.time() - 86401))
        self.assertEqual(self.video().status_code, 404)
        os.utime(self.path, None)
        self.assertEqual(self.video().status_code, 200)
        self.path.unlink()
        self.assertEqual(self.video().status_code, 404)
        self.path.write_bytes(b'fixture')
        token, _ = self.issue()
        self.access(token)
        self.owner.delete('/api/jobs/one')
        self.assertEqual(self.video().status_code, 404)
        self.assertEqual(self.other.head('/api/exports/one/video').status_code, 404)

    def test_secure_proxy_style_exchange_and_null_origin_stays_denied(self):
        token, _ = self.issue()
        # TLS terminates at the reverse proxy; Host remains the public origin.
        with TestClient(app, base_url='https://studio.example') as secure:
            good = self.access(token, client=secure, headers={
                'Origin': 'https://studio.example', 'Sec-Fetch-Site': 'same-origin',
                'X-Forwarded-Proto': 'https', 'X-Forwarded-Host': 'studio.example',
            })
            self.assertEqual(good.status_code, 200)
            self.assertIn('Secure', good.headers['set-cookie'])
            self.assertEqual(secure.get('/api/exports/one/video?download=1').status_code, 200)
        for route in ('/api/exports/one/access', '/api/exports/one/download', '/api/shares/one/access', '/api/jobs/one/export-link', '/api/jobs/one/share-link'):
            for origin in ('null', 'https://evil.test'):
                response = self.other.post(route, data={'token': token}, headers={
                    'Origin': origin, 'Sec-Fetch-Site': 'same-origin', 'X-Forwarded-Host': 'evil.test',
                })
                self.assertEqual(response.status_code, 403)
        # Non-browser clients without Origin retain their body-token API.
        self.assertEqual(self.access(token).status_code, 200)

    def test_export_access_body_bounds_rate_limit_and_artwork_page(self):
        token, _ = self.issue()
        path = '/api/exports/one/access'
        for body in ('token=' + 'a' * 129, 'token=a&token=b', 'token=' + token + '&other=x', 'other=x', 'token=%FF'):
            response = self.other.post(path, content=body, headers={'Content-Type': 'application/x-www-form-urlencoded'})
            self.assertEqual(response.status_code, 404)
            self.assertNotIn('set-cookie', response.headers)
        self.assertEqual(self.other.post(path, json={'token': token}).status_code, 404)
        self.assertEqual(self.other.post(path + '?token=' + token).status_code, 404)
        self.assertEqual(self.other.get(path).status_code, 404)
        for _ in range(60):
            last = self.access(token)
        self.assertEqual(last.status_code, 429)
        self.assertIn('retry-after', last.headers)
        for path in ('/export.html', '/watch.js', '/watch.css'):
            response = self.other.get(path)
            self.assertEqual(response.status_code, 200)
            self.assertNotIn('set-cookie', response.headers)
            self.assertIn('no-store', response.headers['cache-control'])
        page = self.other.get('/export.html')
        self.assertIn('data-video-kind="export"', page.text)
        self.assertIn('<video', page.text)
        self.assertNotIn('<form', page.text)
        self.assertIn('10 分鐘', page.text)
        self.assertNotIn('72 小時', page.text)
        for directive in ("connect-src 'self'", "media-src 'self'", "form-action 'none'", "frame-ancestors 'none'"):
            self.assertIn(directive, page.headers['content-security-policy'])


if __name__ == '__main__':
    unittest.main()
