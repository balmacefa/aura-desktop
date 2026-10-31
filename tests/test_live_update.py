"""Puente local (seguridad del servidor), actualizador, widgets y utilidades de Windows."""
import hashlib, http.client, io, json, threading, unittest
from http.server import ThreadingHTTPServer
from unittest import mock

import _setup
from aura import desk, live, paths, update, win


class BridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = ThreadingHTTPServer(('127.0.0.1', 0), live.Handler)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start(); cls.port = cls.srv.server_address[1]
        paths.USER_MEDIA.mkdir(parents=True, exist_ok=True); (paths.USER_MEDIA / 'mio.mp4').write_bytes(b'0' * 16)

    @classmethod
    def tearDownClass(cls): cls.srv.shutdown()

    def get(self, path, host=None, method='GET'):
        c = http.client.HTTPConnection('127.0.0.1', self.port, timeout=5)
        c.putrequest(method, path, skip_host=True); c.putheader('Host', host or f'127.0.0.1:{self.port}'); c.endheaders()
        r = c.getresponse(); body = r.read(); c.close(); return r, body

    def test_state_has_the_contract_keys(self):
        r, body = self.get('/state'); self.assertEqual(r.status, 200)
        self.assertTrue({'x', 'y', 'down', 'click', 'cpu', 'ram', 'bat', 'hour'} <= set(json.loads(body)))

    def test_foreign_host_is_rejected(self):
        for host in ('evil.example', 'evil.example:80', '127.0.0.1.evil.example'): self.assertEqual(self.get('/state', host)[0].status, 403, host)

    def test_only_scenes_lib_and_media_are_served(self):
        self.assertEqual(self.get('/scenes/estela.html')[0].status, 200)
        r, _ = self.get('/lib/aura.js'); self.assertEqual(r.status, 200); self.assertIn("connect-src 'self'", r.getheader('Content-Security-Policy'))
        self.assertEqual(self.get('/media/cristal.mp4')[0].status, 200); self.assertEqual(self.get('/media/mio.mp4')[0].status, 200)
        for bad in ('/live.py', '/cli.py', '/', '/config.py', '/../aura/live.py', '/media/../../aura.json', '/scenes/../live.py', '/media/%2e%2e/%2e%2e/aura.json'):
            self.assertEqual(self.get(bad)[0].status, 404, bad)

    def test_head_requests_follow_the_same_rules(self):
        self.assertEqual(self.get('/scenes/estela.html', method='HEAD')[0].status, 200)
        self.assertEqual(self.get('/live.py', method='HEAD')[0].status, 404)
        self.assertEqual(self.get('/state', host='evil.example', method='HEAD')[0].status, 403)

    def test_scene_url_and_validation(self):
        self.assertIn('/scenes/video.html?src=/media/mio.mp4', live.scene_url(1, 'video:mio.mp4'))
        self.assertTrue(live.valid_scene('video:mio.mp4')); self.assertFalse(live.valid_scene('video:../x.mp4')); self.assertFalse(live.valid_scene('x'))


def fake_response(payload, headers=None):
    r = io.BytesIO(payload if isinstance(payload, bytes) else json.dumps(payload).encode()); r.headers = headers or {}
    r.__enter__ = lambda s=r: s; r.__exit__ = lambda *a: None
    return r


class UpdateTests(unittest.TestCase):
    def test_versions(self):
        self.assertEqual(update.parse_version('v2.10.3'), (2, 10, 3)); self.assertIsNone(update.parse_version('latest'))
        self.assertTrue(update.is_newer('2.0.1', '2.0.0')); self.assertTrue(update.is_newer('v2.10.0', '2.9.9'))
        self.assertFalse(update.is_newer('2.0.0', '2.0.0')); self.assertFalse(update.is_newer('1.9.9', '2.0.0')); self.assertFalse(update.is_newer('garbage', '2.0.0'))

    def test_asset_name_is_strict(self):
        self.assertTrue(update.ASSET_RE.match('Aura-Setup-2.0.1.exe'))
        for bad in ('Aura-Setup-2.0.1.exe.zip', 'aura-setup-2.0.1.exe', '../Aura-Setup-2.0.1.exe', 'Aura-Setup-2.0.exe', 'Evil.exe'): self.assertFalse(update.ASSET_RE.match(bad), bad)

    def release_json(self, url=None):
        base = update.DOWNLOAD_PREFIX + 'v9.0.0/'
        return {'tag_name': 'v9.0.0', 'html_url': 'https://github.com/x', 'body': 'notas', 'draft': False, 'prerelease': False,
                'assets': [{'name': 'Aura-Setup-9.0.0.exe', 'size': 10, 'browser_download_url': url or base + 'Aura-Setup-9.0.0.exe'},
                           {'name': 'SHA256SUMS.txt', 'size': 90, 'browser_download_url': base + 'SHA256SUMS.txt'}]}

    def test_latest_parses_a_valid_release(self):
        with mock.patch.object(update, '_get', return_value=fake_response(self.release_json())):
            rel = update.latest()
        self.assertEqual(rel.version, '9.0.0')

    def test_latest_rejects_a_foreign_download_url(self):
        with mock.patch.object(update, '_get', return_value=fake_response(self.release_json('https://evil.example/Aura-Setup-9.0.0.exe'))):
            self.assertIsNone(update.latest())

    def test_untrusted_hosts_are_never_contacted(self):
        for url in ('http://github.com/x', 'https://evil.example/x', 'file:///c:/x'):
            with self.assertRaises(ValueError): update._get(url)

    def test_download_verifies_the_checksum(self):
        data = b'instalador-falso' * 100; good = hashlib.sha256(data).hexdigest()
        rel = update.Release('9.0.0', 'v9.0.0', update.DOWNLOAD_PREFIX + 'v9.0.0/Aura-Setup-9.0.0.exe', update.DOWNLOAD_PREFIX + 'v9.0.0/SHA256SUMS.txt', len(data), '', '')

        def run(sha):
            sums = fake_response(f'{sha}  Aura-Setup-9.0.0.exe\n'.encode()); exe = fake_response(data, {'Content-Length': str(len(data))})
            with mock.patch.object(update, '_get', side_effect=[sums, exe]): return update.download(rel)
        self.assertTrue(run(good).exists())
        with self.assertRaises(ValueError): run('0' * 64)


class WidgetAndWinTests(unittest.TestCase):
    def test_helpers(self):
        self.assertEqual(desk.fmt_rate(512), '512 B/s'); self.assertEqual(desk.fmt_rate(2048), '2.0 KB/s')
        self.assertEqual(desk.level_color(10), desk.ACCENT); self.assertEqual(desk.level_color(90), desk.WARN); self.assertEqual(desk.level_color(99), desk.BAD)

    def test_widget_positions_roundtrip(self):
        _setup.reset_data(); desk.save_cfg({'clock': [1, 2]}); self.assertEqual(desk.load_cfg(), {'clock': [1, 2]})

    def test_win_helpers(self):
        self.assertIsInstance(win.covered_by_fullscreen(), bool); self.assertTrue(0 <= win.battery_pct() <= 100)
        self.assertTrue(win.alive(__import__('os').getpid())); self.assertFalse(win.alive(2 ** 22 + 5))


if __name__ == '__main__':
    unittest.main()
