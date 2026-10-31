"""Configuración, estado, rutas, idiomas y CLI."""
import json, os, re, unittest

import _setup
from aura import cli, config, i18n, paths, state


class ConfigTests(unittest.TestCase):
    def setUp(self): _setup.reset_data()

    def test_defaults(self):
        c = config.load()
        self.assertEqual(c['scene'], 'estela'); self.assertEqual(len(c['palette']), 4); self.assertFalse(c['first_run_done'])

    def test_palette_validation(self):
        self.assertEqual(config.check_palette(['#0E0E18', 'd97757', '1d1b3a', '3a1b2a'])[0], '0e0e18')
        for bad in (['zz', '1', '2', '3'], ['0e0e18'] * 3, ['0e0e18', 'd97757', '1d1b3a', '3a1b2a;rm']):
            with self.assertRaises(ValueError): config.check_palette(bad)

    def test_corrupt_file_falls_back_and_is_kept(self):
        paths.ensure_dirs(); paths.CONF.write_text('{no es json')
        self.assertEqual(config.load()['scene'], 'estela'); self.assertTrue(os.path.exists(str(paths.CONF) + '.bad'))

    def test_invalid_values_are_sanitized(self):
        paths.ensure_dirs(); paths.CONF.write_text(json.dumps({'palette': ['x'] * 4, 'lang': 'klingon', 'widgets': 5, 'scene': ''}))
        c = config.load()
        self.assertEqual(c['palette'], config.DEFAULT_PALETTE); self.assertEqual(c['lang'], 'auto'); self.assertEqual(c['widgets'], {}); self.assertEqual(c['scene'], 'estela')

    def test_migrates_1x_format(self):
        paths.ensure_dirs(); paths.CONF.write_text(json.dumps({'mode': 'video', 'video': 'wall/media/cristal.mp4', 'speed': 0.01}))
        c = config.load(); self.assertEqual(c['scene'], 'video:cristal.mp4'); self.assertNotIn('speed', c)

    def test_save_is_atomic_and_unknown_keys_dropped(self):
        config.save({**config.load(), 'basura': 1})
        self.assertFalse(os.path.exists(str(paths.CONF) + '.tmp')); self.assertNotIn('basura', json.loads(paths.CONF.read_text()))


class StateTests(unittest.TestCase):
    def setUp(self): _setup.reset_data()

    def test_roundtrip_and_handover(self):
        self.assertEqual(state.read_state(), {})
        state.write_state(daemon=os.getpid(), file='live:estela')
        self.assertEqual(state.read_state()['file'], 'live:estela')
        self.assertFalse(state.handed_over(os.getpid())); self.assertTrue(state.handed_over(os.getpid() + 1))
        state.write_state(); self.assertFalse(state.handed_over(os.getpid() + 1))

    def test_wall_running_detects_dead_pid(self):
        state.write_state(daemon=2 ** 22 + 7); self.assertFalse(state.wall_running())
        state.write_state(daemon=os.getpid()); self.assertTrue(state.wall_running())


class PathsTests(unittest.TestCase):
    def test_data_is_isolated_and_assets_exist(self):
        self.assertTrue(str(paths.DATA).startswith(_setup.DATA))
        for d in (paths.SCENES, paths.LIB, paths.MEDIA, paths.FONTS, paths.ICONS, paths.LOCALES): self.assertTrue(d.is_dir(), d)
        self.assertTrue((paths.ICONS / 'aura.ico').is_file())


class I18nTests(unittest.TestCase):
    def setUp(self): self.en, self.es = i18n._read('en'), i18n._read('es')

    def test_same_keys_in_every_language(self):
        self.assertEqual(set(self.en), set(self.es))

    def test_no_empty_values_and_matching_placeholders(self):
        ph = lambda s: sorted(re.findall(r'\{(\w+)', s))
        for k in self.en:
            self.assertTrue(self.en[k].strip() and self.es[k].strip(), k)
            self.assertEqual(ph(self.en[k]), ph(self.es[k]), k)

    def test_every_scene_has_a_name_and_description(self):
        for p in paths.SCENES.glob('*.html'):
            if p.stem != 'video': self.assertIn(f'scene.{p.stem}.name', self.en); self.assertIn(f'scene.{p.stem}.desc', self.en)

    def test_fallback_and_formatting(self):
        i18n.setup('es'); self.assertEqual(i18n.t('tab.overview'), 'Resumen'); self.assertEqual(i18n.t('no.existe'), 'no.existe')
        self.assertIn('2.0', i18n.t('up.available', version='2.0')); i18n.setup('en')


class CliTests(unittest.TestCase):
    def setUp(self): _setup.reset_data()

    def test_scene_catalog(self):
        s = cli.scenes()
        for name in ('estela', 'aurora', 'orbes', 'malla', 'constelacion', 'degradado'): self.assertIn(name, s)
        self.assertNotIn('video', s)

    def test_unknown_scene_and_bad_video_are_rejected(self):
        with self.assertRaises(ValueError): cli.apply_scene('no-existe')
        with self.assertRaises(ValueError): cli.apply_scene('video:../../secreto.mp4')
        with self.assertRaises(ValueError): cli.add_video(os.path.join(_setup.DATA, 'nada.mp4'))

    def test_doctor_runs(self):
        self.assertIn(cli.doctor(), (0, 1))

    def test_widgets_not_running_without_pidfile(self):
        self.assertEqual(cli.desk_pids(), [])


if __name__ == '__main__':
    unittest.main()
