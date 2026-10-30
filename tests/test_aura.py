import _setup  # noqa: F401  (debe ir primero)
import json, os, tempfile, unittest
from unittest import mock

import aura


class ConfBase(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(dir=_setup.TMP)
        self.conf = os.path.join(self.d, 'aura.json')
        p = mock.patch.object(aura, 'CONF', self.conf); p.start(); self.addCleanup(p.stop)

    def write(self, text):
        with open(self.conf, 'w', encoding='utf-8') as f: f.write(text)


class TestPalette(unittest.TestCase):
    def test_valida(self):
        self.assertEqual(aura.check_palette(['#0E0E18', 'd97757', '1d1b3a', '3A1B2A']), ['0e0e18', 'd97757', '1d1b3a', '3a1b2a'])

    def test_invalida(self):
        for bad in (['0e0e18'] * 3, ['0e0e18'] * 5, ['zzzzzz'] + ['0e0e18'] * 3, ['0e0e1'] + ['0e0e18'] * 3):
            with self.assertRaises(ValueError): aura.check_palette(bad)


class TestLoadConf(ConfBase):
    def test_sin_archivo(self):
        self.assertEqual(aura.load_conf(), aura.DEFAULT)

    def test_json_corrupto(self):
        self.write('{no es json')
        self.assertEqual(aura.load_conf(), aura.DEFAULT)
        self.assertTrue(os.path.exists(self.conf + '.bad'))
        self.assertFalse(os.path.exists(self.conf))

    def test_paleta_mala(self):
        self.write(json.dumps({'palette': ['x', 'y']}))
        self.assertEqual(aura.load_conf()['palette'], aura.DEFAULT['palette'])

    def test_velocidad_acotada(self):
        self.write(json.dumps({'speed': 99})); self.assertEqual(aura.load_conf()['speed'], 0.05)
        self.write(json.dumps({'speed': -1})); self.assertEqual(aura.load_conf()['speed'], 0.003)
        self.write(json.dumps({'speed': 'rapido'})); self.assertEqual(aura.load_conf()['speed'], aura.DEFAULT['speed'])

    def test_video_fuera_del_proyecto(self):
        self.write(json.dumps({'video': '../../../etc/evil.mp4'}))
        self.assertEqual(aura.load_conf()['video'], aura.DEFAULT['video'])

    def test_video_dentro(self):
        self.write(json.dumps({'video': 'wall/media/otro.mp4'}))
        self.assertEqual(aura.load_conf()['video'], 'wall/media/otro.mp4')


class TestSaveConf(ConfBase):
    def test_atomico(self):
        aura.save_conf({'speed': 0.02})
        with open(self.conf, encoding='utf-8') as f: self.assertEqual(json.load(f), {'speed': 0.02})
        self.assertEqual(os.listdir(self.d), ['aura.json'])


class TestScenes(ConfBase):
    def test_incluye(self):
        s = aura.scenes()
        self.assertIn('estela', s); self.assertIn('godot-cristal', s)

    def test_escena_desconocida(self):
        with self.assertRaises(ValueError): aura.apply_scene('nope')

    def test_video_inexistente(self):
        with self.assertRaises(ValueError): aura.apply_video(os.path.join(self.d, 'no-existe.mp4'))


if __name__ == '__main__':
    unittest.main()
