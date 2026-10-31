"""Device-policy and API-configuration tests; no claim of real HIP execution."""
import sys
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch
from flamoris_cinema.render_device import choose_hip_device, configure_cycles, verify_selection, validate_options


class DevicePolicyTests(unittest.TestCase):
    def test_hip_requires_gpu_and_rejects_ambiguous_selection(self):
        cpu = {'id': 'cpu', 'name': 'Processor', 'type': 'CPU'}
        with self.assertRaisesRegex(ValueError, 'CPU fallback is disabled'):
            choose_hip_device([cpu])
        devices = [cpu, {'id': 'hip1', 'name': 'AMD RX 9060 XT', 'type': 'HIP'},
                   {'id': 'hip2', 'name': 'AMD RX 7900', 'type': 'HIP'}]
        with self.assertRaisesRegex(ValueError, 'multiple'):
            choose_hip_device(devices)
        self.assertEqual(choose_hip_device(devices, '9060')['id'], 'hip1')
        self.assertEqual(choose_hip_device(devices, 'HIP2')['id'], 'hip2')

    def test_invalid_options(self):
        for backend, name, threads in [('CUDA', None, 2), ('CPU', 'AMD', 2),
                                       ('HIP', ' ', 2), ('HIP', None, 0), ('HIP', None, True)]:
            with self.subTest(backend=backend, threads=threads), self.assertRaises(ValueError):
                validate_options(backend, name, threads)

    def test_hip_configuration_excludes_cpu_and_other_devices(self):
        devices = [NS(id='cpu', name='CPU', type='CPU', use=True),
                   NS(id='hip1', name='AMD RX 9060 XT', type='HIP', use=False),
                   NS(id='hip2', name='AMD RX 7900', type='HIP', use=True)]
        prefs = NS(devices=devices, refresh_devices=lambda: None, compute_device_type='NONE', use_hiprt=True)
        bpy = NS(context=NS(preferences=NS(addons={'cycles': NS(preferences=prefs)})))
        scene = NS(render=NS(), cycles=NS(device='CPU'))
        with patch.dict(sys.modules, {'bpy': bpy}):
            report = configure_cycles(scene, 'HIP', '9060', 2)
            self.assertEqual(scene.cycles.device, 'GPU')
            self.assertEqual(scene.render.threads, 2)
            self.assertEqual([d.use for d in devices], [False, True, False])
            self.assertFalse(report['cpu_render_enabled'])
            self.assertTrue(report['hiprt'])
            devices[0].use = True
            with self.assertRaisesRegex(ValueError, 'CPU render device enabled'):
                verify_selection(scene, report)

    def test_cpu_limit_does_not_query_gpu_preferences(self):
        scene = NS(render=NS(), cycles=NS(device='GPU'))
        with patch.dict(sys.modules, {'bpy': NS()}):
            report = configure_cycles(scene, threads=2)
        self.assertEqual(scene.cycles.device, 'CPU')
        self.assertEqual(scene.render.threads_mode, 'FIXED')
        self.assertEqual(scene.render.threads, 2)
        self.assertEqual(report['backend'], 'CPU')
