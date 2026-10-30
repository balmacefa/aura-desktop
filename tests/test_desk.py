import _setup  # noqa: F401
import json, os, tempfile, unittest
from unittest import mock

import auradesk as d


class TestFmt(unittest.TestCase):
    def test_fmt_rate(self):
        self.assertEqual(d.fmt_rate(0), '0 B/s')
        self.assertEqual(d.fmt_rate(512), '512 B/s')
        self.assertEqual(d.fmt_rate(2048), '2.0 KB/s')
        self.assertEqual(d.fmt_rate(3 * 2**20), '3.0 MB/s')

    def test_level_color(self):
        self.assertEqual(d.level_color(10), d.ACCENT)
        self.assertEqual(d.level_color(85), d.WARN)
        self.assertEqual(d.level_color(94.9), d.WARN)
        self.assertEqual(d.level_color(95), d.BAD)


class TestCfg(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(dir=_setup.TMP)
        for n, v in (('CFG_DIR', self.dir), ('CFG', os.path.join(self.dir, 'config.json'))):
            p = mock.patch.object(d, n, v); p.start(); self.addCleanup(p.stop)

    def test_load_sin_archivo(self):
        self.assertEqual(d.load_cfg(), {})

    def test_roundtrip_sin_tmp(self):
        d.save_cfg({'clock': [10, 20]})
        self.assertEqual(d.load_cfg(), {'clock': [10, 20]})
        self.assertEqual(os.listdir(self.dir), ['config.json'])

    def test_load_corrupto(self):
        with open(d.CFG, 'w') as f: f.write('{')
        self.assertEqual(d.load_cfg(), {})

    def test_enabled_widgets(self):
        root = tempfile.mkdtemp(dir=_setup.TMP)
        with mock.patch.object(d, 'ROOT', root):
            self.assertEqual(d.enabled_widgets(), {})
            with open(os.path.join(root, 'aura.json'), 'w', encoding='utf-8') as f: json.dump({'widgets': {'clock': True}}, f)
            self.assertEqual(d.enabled_widgets(), {'clock': True})
            with open(os.path.join(root, 'aura.json'), 'w') as f: f.write('nope')
            self.assertEqual(d.enabled_widgets(), {})


if __name__ == '__main__':
    unittest.main()
