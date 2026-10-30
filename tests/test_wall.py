import _setup  # noqa: F401
import os, tempfile, unittest
from unittest import mock

import aurawall as w


class TestState(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(dir=_setup.TMP)
        for n, v in (('STATE_DIR', self.dir), ('STATE', os.path.join(self.dir, 'state.json'))):
            p = mock.patch.object(w, n, v); p.start(); self.addCleanup(p.stop)

    def test_vacio(self):
        self.assertEqual(w.read_state(), {})

    def test_roundtrip_sin_tmp(self):
        w.write_state(daemon=123, file='x.mp4')
        self.assertEqual(w.read_state(), {'daemon': 123, 'file': 'x.mp4'})
        self.assertEqual(os.listdir(self.dir), ['state.json'])

    def test_corrupto(self):
        with open(w.STATE, 'w') as f: f.write('{')
        self.assertEqual(w.read_state(), {})

    def test_handed_over(self):
        self.assertFalse(w.handed_over(1))            # sin estado
        w.write_state(daemon=1); self.assertFalse(w.handed_over(1))
        w.write_state(daemon=2); self.assertTrue(w.handed_over(1))
        w.write_state(); self.assertFalse(w.handed_over(1))


if __name__ == '__main__':
    unittest.main()
