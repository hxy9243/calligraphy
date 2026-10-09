import os
import signal
import subprocess
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import numpy as np

from backend.editor_preview import glyph_worker_count
from calligraphy.kai_scene import prepare_kai
from calligraphy.renderer import create_scene
from calligraphy.spec import SceneSpec


class WorkerBudgetTests(unittest.TestCase):
    def budget(self, files=None, configured='2', cpus=8, affinity=8):
        files = files or {}
        def read(path, *args, **kwargs):
            relative = str(path).removeprefix('/sys/fs/cgroup/')
            if relative not in files:
                raise FileNotFoundError(relative)
            return str(files[relative])
        with patch.dict(os.environ, {'CALLIGRAPHY_PREVIEW_WORKERS': configured}), \
             patch('os.cpu_count', return_value=cpus), \
             patch('os.sched_getaffinity', return_value=set(range(affinity)), create=True), \
             patch.object(Path, 'read_text', read):
            return glyph_worker_count()

    def test_hard_cap_affinity_and_explicit_serial(self):
        self.assertEqual(self.budget(configured='99'), 2)
        self.assertEqual(self.budget(configured='1'), 1)
        self.assertEqual(self.budget(configured='invalid'), 1)
        self.assertEqual(self.budget(affinity=1), 1)
        self.assertEqual(self.budget(cpus=1), 1)

    def test_cpu_quota_v1_v2_and_memory_limits(self):
        self.assertEqual(self.budget({'cpu.max': '150000 100000'}), 1)
        self.assertEqual(self.budget({'cpu.max': '200000 100000'}), 2)
        self.assertEqual(self.budget({'cpu.max': 'max 100000'}), 2)
        self.assertEqual(self.budget({'cpu/cpu.cfs_quota_us': 100000,
                                     'cpu/cpu.cfs_period_us': 100000}), 1)
        self.assertEqual(self.budget({'memory.max': 512 * 1024**2}), 1)
        self.assertEqual(self.budget({'memory.max': 1024 * 1024**2}), 2)
        self.assertEqual(self.budget({'memory/memory.limit_in_bytes': 512 * 1024**2}), 1)
        self.assertEqual(self.budget({'memory.max': 'max'}), 2)

    def test_nested_cgroup_and_ancestor_limits(self):
        self.assertEqual(self.budget({'/proc/self/cgroup': '0::/app/worker',
                                     'app/cpu.max': '100000 100000'}), 1)
        self.assertEqual(self.budget({'/proc/self/cgroup': '0::/app/worker',
                                     'app/worker/memory.max': 512 * 1024**2}), 1)
        self.assertEqual(self.budget({'/proc/self/cgroup': '2:cpu,cpuacct:/app/worker',
                                     'cpu,cpuacct/app/cpu.cfs_quota_us': 100000,
                                     'cpu,cpuacct/app/cpu.cfs_period_us': 100000}), 1)

    def test_platform_without_affinity_and_unreadable_limits(self):
        from backend import editor_preview
        operating_system = Mock(spec=['cpu_count', 'environ'])
        operating_system.cpu_count.return_value = 4
        operating_system.environ = {}
        with patch.object(editor_preview, 'os', operating_system), \
             patch.object(Path, 'read_text', side_effect=OSError):
            self.assertEqual(glyph_worker_count(), 2)


class PreviewDeadlineTests(unittest.TestCase):
    def test_deadline_kills_process_group_including_fitting_children(self):
        from backend.editor_preview import cached_preview
        process = Mock(pid=1234)
        process.communicate.side_effect = [subprocess.TimeoutExpired('preview', 30), (b'', b'')]
        cached_preview.cache_clear()
        with patch('backend.editor_preview.subprocess.Popen', return_value=process) as launch, \
             patch('backend.editor_preview.os.killpg') as kill:
            with self.assertRaises(TimeoutError):
                cached_preview('{}')
        kill.assert_called_once_with(1234, signal.SIGKILL)
        self.assertEqual(process.communicate.call_count, 2)
        self.assertTrue(launch.call_args.kwargs['start_new_session'])
        self.assertEqual(launch.call_args.kwargs['env']['OPENBLAS_NUM_THREADS'], '1')
        self.assertEqual(cached_preview.cache_info().currsize, 0)


class DispatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.cache = str(Path(self.temp.name) / 'geometry.db')
        # Deliberately non-lexicographic input; mock fitting, not scheduling.
        self.glyphs = {c: {'strokes': [0] * 16} for c in '月明松照永'}

    def fake_executor(self, fail=False):
        class Executor:
            def __init__(self, **kwargs):
                self.options = kwargs
                self.active = 0
                self.maximum = 0
                self.futures = []
                self.closed = None
            def submit(self, function, task):
                self.active += 1
                self.maximum = max(self.maximum, self.active)
                future = Mock()
                def result():
                    self.active -= 1
                    if fail:
                        raise ValueError('glyph fit failed')
                    return {'character': task[0]}
                future.result.side_effect = result
                self.futures.append(future)
                return future
            def shutdown(self, **kwargs):
                self.closed = kwargs
        instance = Executor()
        return instance

    def test_bounded_dispatch_order_and_shutdown(self):
        executor = self.fake_executor()
        with patch('concurrent.futures.ProcessPoolExecutor', return_value=executor) as factory, \
             patch('concurrent.futures.wait', side_effect=lambda pending, **kw: ({next(iter(pending))}, set())):
            result = prepare_kai(self.glyphs, self.cache, workers=50)
        self.assertEqual(list(result), list(self.glyphs))
        self.assertEqual(len(executor.futures), len(self.glyphs))
        self.assertEqual(executor.maximum, 2)
        self.assertEqual(factory.call_args.kwargs['max_workers'], 2)
        self.assertEqual(factory.call_args.kwargs['mp_context'].get_start_method(), 'spawn')
        self.assertEqual(executor.closed, {'wait': True, 'cancel_futures': True})

    def test_errors_stop_submission_and_cancel_queued_work(self):
        executor = self.fake_executor(fail=True)
        with patch('concurrent.futures.ProcessPoolExecutor', return_value=executor), \
             patch('concurrent.futures.wait', side_effect=lambda pending, **kw: ({next(iter(pending))}, set())):
            with self.assertRaisesRegex(ValueError, 'glyph fit failed'):
                prepare_kai(self.glyphs, self.cache, workers=2)
        self.assertEqual(len(executor.futures), 2)
        executor.futures[1].cancel.assert_called_once()
        self.assertEqual(executor.closed, {'wait': True, 'cancel_futures': True})

    def test_short_work_and_one_worker_never_start_a_pool(self):
        for glyphs, workers in [(self.glyphs, 1), ({'永': {'strokes': [0] * 5}}, 2)]:
            with patch('concurrent.futures.ProcessPoolExecutor', side_effect=AssertionError('pool')), \
                 patch('calligraphy.kai_scene._prepare_one', side_effect=lambda task: {'character': task[0]}) as fit:
                self.assertEqual(list(prepare_kai(glyphs, self.cache, workers=workers)), list(glyphs))
                self.assertEqual(fit.call_count, len(glyphs))


class ParallelPixelsTests(unittest.TestCase):
    def test_real_processes_preserve_partial_final_order_duplicates_and_warm_cache(self):
        with tempfile.TemporaryDirectory() as folder:
            # 73 unique strokes triggers bounded processes. 處's repeated counterpart
            # 处 is deliberately repeated in the poem and must be fitted only once.
            spec = SceneSpec(text='春眠不觉晓，处处闻啼鸟',
                             layout={'width': 240, 'height': 320})
            with patch.dict(os.environ, {'CALLIGRAPHY_KAI_CACHE': folder + '/serial.db'}):
                serial = create_scene(spec)
            with patch.dict(os.environ, {'CALLIGRAPHY_KAI_CACHE': folder + '/parallel.db'}):
                parallel = create_scene(spec, glyph_workers=2)
                with patch('concurrent.futures.ProcessPoolExecutor', side_effect=AssertionError('warm pool')), \
                     patch('calligraphy.kai_scene._prepare_one', side_effect=AssertionError('warm fit')):
                    warm = create_scene(spec, glyph_workers=2)
            self.assertEqual(list(serial.programs), list(parallel.programs))
            self.assertEqual(len(parallel.programs), 9)
            self.assertEqual(serial.plan, parallel.plan)
            for char in serial.programs:
                self.assertEqual(serial.programs[char]['strokes'], parallel.programs[char]['strokes'])
            # Include a backwards seek after completing a frame.
            for time in (serial.duration * .13, serial.duration, serial.duration * .43):
                np.testing.assert_array_equal(serial.frame(time), parallel.frame(time))
                np.testing.assert_array_equal(serial.frame(time), warm.frame(time))


if __name__ == '__main__':
    unittest.main()
