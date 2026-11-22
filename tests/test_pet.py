"""Unit tests for Gemini Catgirl Desktop Pet."""
import json
import os
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from catgirl_pet import autostart, monitor
from catgirl_pet.animation import ANIMATIONS, AnimationSchedule, roam_x
from catgirl_pet.dialogue import DIALOGUE, format_context_usage, pick_line, read_antigravity_status
from catgirl_pet.speech import SpeechQueue
from catgirl_pet.state import PetState
from catgirl_pet.task_activity import ActivityTracker


class TestPetCore(unittest.TestCase):
    def test_state_sleep_wake_and_working(self):
        state = PetState(idle_seconds=300)
        state.tick(299)
        self.assertEqual(state.mode, 'idle')
        state.tick(300)
        self.assertEqual(state.mode, 'sleeping')
        state.set_working(True, 305)
        self.assertEqual(state.mode, 'waking')
        self.assertEqual(state.frame(305), 10)
        self.assertEqual(state.frame(307.9), 15)
        state.tick(308)
        self.assertEqual(state.mode, 'idle')

    def test_animation_schedule_and_roam(self):
        sched = AnimationSchedule()
        sched.play('jumping', 10, duration=4)
        self.assertEqual(sched.current(11, False), 'jumping')
        self.assertNotEqual(sched.current(15, True), 'jumping')
        self.assertIn(sched.current(15, True), ('running', 'waiting', 'review'))
        self.assertEqual(roam_x(100, 300, 0, 1920, 1), 102)
        self.assertEqual(roam_x(0, 300, 0, 1920, -1), 0)

    def test_speech_priority(self):
        q = SpeechQueue()
        q.add('ambient', 0, priority=0)
        self.assertEqual(q.current(0), 'ambient')
        q.add('urgent', 1, priority=2)
        self.assertEqual(q.current(1), 'urgent')

    def test_dialogue_covers_all_animations(self):
        for key in ANIMATIONS:
            self.assertIn(key, DIALOGUE)
            self.assertTrue(pick_line(key))

    def test_monitor_process_detection(self):
        self.assertTrue(
            monitor.is_antigravity_main(
                ['/home/ls/Antigravity/Antigravity-x64/antigravity', '--no-sandbox']
            )
        )
        self.assertFalse(
            monitor.is_antigravity_main(
                ['/home/ls/Antigravity/Antigravity-x64/antigravity', '--type=renderer']
            )
        )
        self.assertFalse(
            monitor.is_antigravity_main(
                [
                    '/home/ls/Antigravity/Antigravity-x64/antigravity',
                    '--import=file:///home/ls/.gemini/antigravity/lib/node_modules/sidecar_sdk/register_loader.js',
                    'main.mjs',
                ]
            )
        )
        self.assertEqual(monitor.next_action(False, True, False, False), 'start')
        self.assertEqual(monitor.next_action(True, False, True, False), 'stop')
        self.assertIsNone(monitor.next_action(False, True, False, True))

    def test_activity_tracker_hooks_and_transcripts(self):
        with tempfile.TemporaryDirectory() as tmp:
            hook_dir = Path(tmp) / 'hooks'
            hook_dir.mkdir()
            brain_dir = Path(tmp) / 'brain'
            tr_dir = brain_dir / 'conv-1/.system_generated/logs'
            tr_dir.mkdir(parents=True)

            hook_file = hook_dir / 'sess.jsonl'
            hook_file.write_text('', encoding='utf-8')
            tr_file = tr_dir / 'transcript.jsonl'
            tr_file.write_text('', encoding='utf-8')

            tracker = ActivityTracker(
                hook_roots=[hook_dir],
                brain_root=brain_dir,
                pulse_history_root=Path(tmp) / 'pulse-history',
            )
            self.assertEqual(tracker.poll(), (False, 0, 0, 0))

            with hook_file.open('a', encoding='utf-8') as f:
                f.write(json.dumps({'type': 'event_msg', 'payload': {'type': 'task_started'}}) + '\n')
            self.assertEqual(tracker.poll(), (True, 0, 0, 0))

            with hook_file.open('a', encoding='utf-8') as f:
                f.write(json.dumps({'type': 'event_msg', 'payload': {'type': 'task_complete'}}) + '\n')
            self.assertEqual(tracker.poll(), (False, 1, 0, 0))

            with tr_file.open('a', encoding='utf-8') as f:
                f.write(json.dumps({'type': 'USER_INPUT', 'status': 'DONE'}) + '\n')
            self.assertEqual(tracker.poll(), (True, 0, 0, 0))
            usage = tracker.context_usage()
            self.assertEqual(usage['kind'], 'transcript')
            self.assertIn('累计记录 1 步', format_context_usage(usage))

    def test_autostart_linux(self):
        with tempfile.TemporaryDirectory() as tmp:
            old = os.environ.get('XDG_CONFIG_HOME')
            os.environ['XDG_CONFIG_HOME'] = tmp
            try:
                self.assertFalse(autostart.is_enabled('linux'))
                autostart.set_enabled(True, 'linux')
                self.assertTrue(autostart.is_enabled('linux'))
                autostart.set_enabled(False, 'linux')
                self.assertFalse(autostart.is_enabled('linux'))
            finally:
                if old is None:
                    os.environ.pop('XDG_CONFIG_HOME', None)
                else:
                    os.environ['XDG_CONFIG_HOME'] = old

    def test_transparent_sprites_have_alpha(self):
        for rel, extras in (('assets/transparent', {}), ('assets/transparent-v2', {'sleep': 16})):
            root = Path(__file__).resolve().parent.parent / rel
            checks = {state: count for state, (count, _) in ANIMATIONS.items()}
            checks.update(extras)
            for state, count in checks.items():
                for idx in range(count):
                    path = root / state / f'{idx:02d}.png'
                    self.assertTrue(path.is_file(), f'Missing {path}')
                    im = Image.open(path)
                    self.assertEqual(im.mode, 'RGBA')
                    self.assertEqual(im.size, (768, 832))
                    alpha = np.array(im)[:, :, 3]
                    self.assertGreater((alpha == 0).sum(), 100000, f'{path} is not transparent')

    def test_stale_activity_tool_calls_and_sleep_mode(self):
        import json
        import os
        import tempfile
        import time
        from PyQt5.QtWidgets import QApplication
        from catgirl_pet.task_activity import ActivityTracker
        from catgirl_pet.app import PetWindow

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            hook_root = tmp_path / 'hooks'
            brain_root = tmp_path / 'brain'
            conv_dir = brain_root / 'conv-1' / '.system_generated' / 'logs'
            hook_root.mkdir(parents=True)
            conv_dir.mkdir(parents=True)

            # Stale unclosed hook & transcript older than STALE_INITIAL_SECONDS must NOT block sleep
            stale_hook = hook_root / 'stale.jsonl'
            stale_hook.write_text(json.dumps({'type': 'task_started'}) + '\n', encoding='utf-8')
            old_ts = time.time() - (ActivityTracker.STALE_INITIAL_SECONDS + 30)
            os.utime(stale_hook, (old_ts, old_ts))

            stale_tx = conv_dir / 'transcript.jsonl'
            stale_tx.write_text(
                json.dumps({'type': 'USER_INPUT', 'status': 'DONE', 'step_index': 0}) + '\n',
                encoding='utf-8',
            )
            os.utime(stale_tx, (old_ts, old_ts))

            tracker = ActivityTracker(hook_roots=[hook_root], brain_root=brain_root)
            working, started, completed, failed = tracker.poll()
            self.assertFalse(working)
            self.assertEqual((started, completed, failed), (0, 0, 0))

            # Active transcript: USER_INPUT -> working=True; PLANNER_RESPONSE with tool_calls keeps working=True
            tx_file = brain_root / 'conv-2' / '.system_generated' / 'logs' / 'transcript.jsonl'
            tx_file.parent.mkdir(parents=True)
            tx_file.write_text(
                json.dumps({'type': 'USER_INPUT', 'status': 'DONE', 'step_index': 0}) + '\n',
                encoding='utf-8',
            )
            working, *_ = tracker.poll()
            self.assertTrue(working)

            with tx_file.open('a', encoding='utf-8') as fh:
                fh.write(
                    json.dumps({
                        'type': 'PLANNER_RESPONSE',
                        'status': 'DONE',
                        'step_index': 1,
                        'tool_calls': [{'name': 'run_command'}],
                    }) + '\n'
                )
            working, *_ = tracker.poll()
            self.assertTrue(working)

            # Final PLANNER_RESPONSE without tool_calls ends turn (working=False)
            with tx_file.open('a', encoding='utf-8') as fh:
                fh.write(
                    json.dumps({
                        'type': 'PLANNER_RESPONSE',
                        'status': 'DONE',
                        'step_index': 2,
                    }) + '\n'
                )
            working, *_ = tracker.poll()
            self.assertFalse(working)

        # PetWindow can enter sleep mode when idle/not working
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        qt_app = QApplication.instance() or QApplication([])
        window = PetWindow()
        try:
            now = 1000.0
            window.state.set_working(False, now)
            window.state.sleep(now + 1.0)
            self.assertEqual(window.state.mode, 'sleeping')
        finally:
            window.timer.stop()
            window.close()
            qt_app.processEvents()

    def test_pulse_context_cache_and_quota(self):
        import hashlib
        from datetime import datetime, timezone
        from catgirl_pet.dialogue import read_antigravity_quota

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            pulse_data = tmp_path / 'pulse_data'
            scope = hashlib.sha256(b'cat@example.com').hexdigest()
            hist_dir = pulse_data / 'history-v1' / scope
            usage_dir = pulse_data / 'usage-v1' / scope
            brain_dir = tmp_path / 'brain'
            tr_dir = brain_dir / 'conv-abc/.system_generated/logs'
            hist_dir.mkdir(parents=True)
            usage_dir.mkdir(parents=True)
            tr_dir.mkdir(parents=True)

            (tr_dir / 'transcript.jsonl').write_text(
                json.dumps({'type': 'USER_INPUT', 'status': 'DONE', 'step_index': 0}) + '\n',
                encoding='utf-8',
            )
            (hist_dir / 'conv-abc.json').write_text(
                json.dumps({
                    'conversationId': 'conv-abc',
                    'savedAt': '2026-11-21T00:00:00Z',
                    'metrics': {
                        'status': 'CASCADE_RUN_STATUS_RUNNING',
                        'model': 'Gemini 4 Hydrogen (High)',
                        'context': {
                            'usedTokens': 160940,
                            'maxTokens': 512000,
                            'usedFraction': 0.3143,
                            'model': 'Gemini 4 Hydrogen (High)',
                        },
                        'cache': {'hitRate': 0.75, 'cachedTokens': 750, 'inputTokens': 1000},
                        'taskUsage': {
                            'subagents': 2,
                            'cache': {'hitRate': 0.808, 'cachedTokens': 808, 'inputTokens': 1000},
                        },
                    },
                }),
                encoding='utf-8',
            )

            tracker = ActivityTracker(
                hook_roots=[],
                brain_root=brain_dir,
                pulse_history_root=pulse_data / 'history-v1',
            )
            tracker.poll()
            usage, recent = tracker.context_snapshot()
            self.assertFalse(recent)
            self.assertEqual(usage['kind'], 'pulse')
            self.assertAlmostEqual(usage['rate'], 80.8, places=1)
            rendered = format_context_usage(usage, recent=recent)
            self.assertIn('160.9K / 512K (31%)', rendered)
            self.assertIn('缓存命中率 80.8%', rendered)
            self.assertIn('Gemini 4 Hydrogen (High)', rendered)

            now_dt = datetime(2026, 11, 21, 8, 0, 0, tzinfo=timezone.utc)
            now_ts = now_dt.timestamp()
            (usage_dir / 'ledger.json').write_text(
                json.dumps({
                    'records': [
                        {'at': int((now_ts - 3600) * 1000), 'uncached': 1000, 'cacheRead': 4000, 'cacheWrite': 0, 'output': 500},
                    ]
                }),
                encoding='utf-8',
            )
            accounts_file = tmp_path / 'accounts.json'
            accounts_file.write_text(
                json.dumps({
                    'accounts': [{
                        'email': 'cat@example.com',
                        'label': '主账号',
                        'planTier': 'Google AI Pro',
                        'quotaSummary': {
                            'updatedAt': '2026-11-21T07:50:00Z',
                            'groups': [{
                                'displayName': 'Gemini Models',
                                'buckets': [
                                    {'window': '5h', 'remainingPercent': 85, 'resetTime': '2026-11-21T06:00:00Z'},
                                    {'window': 'weekly', 'remainingPercent': 95, 'resetTime': '2026-11-27T10:00:00Z'},
                                ],
                            }],
                        },
                    }]
                }),
                encoding='utf-8',
            )
            quota_text = read_antigravity_quota(pulse_data_root=pulse_data, accounts_path=accounts_file, now=now_ts)
            self.assertIn('主账号 (Google AI Pro)', quota_text)
            self.assertIn('5h 已重置(旧85%待面板刷新)', quota_text)
            self.assertIn('周 剩95%', quota_text)
            self.assertIn('近5h 5.5K', quota_text)

    def test_packaging_and_windows_status(self):
        import importlib.util
        from unittest.mock import patch
        from catgirl_pet.dialogue import _windows_antigravity_counts

        spec = importlib.util.spec_from_file_location(
            'pet_create_packages',
            Path(__file__).resolve().parent.parent / 'packaging' / 'create_packages.py',
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        collect_files = mod.collect_files

        linux_names = {name for name, _ in collect_files('linux')}
        win_names = {name for name, _ in collect_files('windows')}
        self.assertIn('start.sh', linux_names)
        self.assertIn('follow-antigravity.sh', linux_names)
        self.assertIn('catgirl_pet/monitor.py', linux_names)
        self.assertIn('setup.bat', win_names)
        self.assertIn('standalone.bat', win_names)
        self.assertIn('follow-antigravity.bat', win_names)
        self.assertIn('build.bat', win_names)
        self.assertIn('main.py', win_names)
        self.assertNotIn('catgirl_pet/monitor.py', win_names)
        self.assertIn('assets/transparent-v2/running-right/15.png', win_names)
        self.assertIn('assets/transparent-v2/sleep/15.png', linux_names)

        sample = json.dumps([
            {'Name': 'Antigravity.exe', 'CommandLine': '"C:\\App\\Antigravity.exe" --no-sandbox'},
            {'Name': 'Antigravity.exe', 'CommandLine': '"C:\\App\\Antigravity.exe" --type=renderer'},
            {'Name': 'language_server.exe', 'CommandLine': 'language_server.exe --standalone'},
        ]).encode('utf-8')
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.stdout = sample
            self.assertEqual(_windows_antigravity_counts(), (1, 1))

    def test_pet_window_offscreen(self):
        os.environ['QT_QPA_PLATFORM'] = 'offscreen'
        from PyQt5.QtWidgets import QApplication
        from catgirl_pet.app import PetWindow

        app = QApplication.instance() or QApplication([])
        win = PetWindow()
        self.assertTrue(win.testAttribute(0x00000078))  # WA_TranslucentBackground
        self.assertEqual(len(win.sleep_images), 16)
        self.assertIsInstance(read_antigravity_status(), str)
        win.close()
        app.quit()


if __name__ == '__main__':
    unittest.main()
