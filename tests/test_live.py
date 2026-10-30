import _setup  # noqa: F401
import http.client, json, threading, unittest
from http.server import ThreadingHTTPServer

import live


class TestLive(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = ThreadingHTTPServer(('127.0.0.1', 0), live.Handler)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown(); cls.srv.server_close()

    def get(self, path, host=None):
        c = http.client.HTTPConnection('127.0.0.1', self.port, timeout=10)
        try:
            c.putrequest('GET', path, skip_host=True)
            c.putheader('Host', host or f'127.0.0.1:{self.port}')
            c.endheaders()
            r = c.getresponse(); body = r.read()
            return r, body
        finally:
            c.close()

    def test_state(self):
        r, body = self.get('/state')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.getheader('Content-Type'), 'application/json')
        data = json.loads(body)
        for k in ('x', 'y', 'down', 'click', 'cpu', 'ram', 'bat', 'hour'):
            self.assertIn(k, data)

    def test_host_ajeno(self):
        for h in ('evil.com', 'evil.com:80', '127.0.0.1.evil.com'):
            self.assertEqual(self.get('/state', host=h)[0].status, 403, h)
        self.assertEqual(self.get('/state', host=f'localhost:{self.port}')[0].status, 200)

    def test_no_sirve_codigo(self):
        self.assertEqual(self.get('/live.py')[0].status, 404)

    def test_lib(self):
        r, _ = self.get('/lib/aura.js')
        self.assertEqual(r.status, 200)
        self.assertIsNotNone(r.getheader('Content-Security-Policy'))

    def test_scenes(self):
        s = live.scenes()
        self.assertIn('estela', s); self.assertIn('godot-cristal', s)


if __name__ == '__main__':
    unittest.main()
