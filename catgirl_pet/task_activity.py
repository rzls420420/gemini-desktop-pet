"""Track Antigravity task activity via hook logs and brain transcripts."""
import json
import time
from pathlib import Path


class ActivityTracker:
    STALE_INITIAL_SECONDS = 120
    STALE_ACTIVE_SECONDS = 300

    def __init__(self, hook_roots=None, brain_root=None, pulse_history_root=None):
        if hook_roots is None:
            self.hook_roots = [
                Path.home() / '.cache/gemini-catgirl-pet/antigravity',
            ]
        else:
            self.hook_roots = [Path(root) for root in hook_roots]
        self.brain_root = Path(brain_root) if brain_root is not None else Path.home() / '.gemini/antigravity/brain'
        self.pulse_history_root = (
            Path(pulse_history_root)
            if pulse_history_root is not None
            else Path.home() / '.gemini/antigravity/sidecar_data/antigravity-pulse/panel/data/history-v1'
        )
        self.files = {}
        self.transcripts = {}
        self.initialized = False

    def _collect_hook_files(self):
        candidates = []
        for root in self.hook_roots:
            try:
                if root.is_dir():
                    candidates.extend(root.glob('*.jsonl'))
            except OSError:
                continue
        return candidates

    def _collect_transcripts(self):
        try:
            if self.brain_root.is_dir():
                return list(self.brain_root.glob('*/.system_generated/logs/transcript.jsonl'))
        except OSError:
            pass
        return []

    def _poll_hooks(self, cutoff):
        completed = 0
        aborted = 0
        missing = 0
        candidates = self._collect_hook_files()
        for path, item in list(self.files.items()):
            try:
                path.stat()
            except FileNotFoundError:
                if item['active']:
                    missing += 1
                del self.files[path]
            except OSError:
                pass

        for path in candidates:
            try:
                stat = path.stat()
                if stat.st_mtime < cutoff and path not in self.files:
                    continue
                item = self.files.get(path)
                if item is None:
                    item = {'offset': 0, 'active': False, 'partial': b'', 'usage': None, 'completed_usage': None}
                    self.files[path] = item
                if stat.st_size < item['offset']:
                    item.update(offset=0, active=False, partial=b'', usage=None, completed_usage=None)
                item['modified'] = stat.st_mtime_ns
                with path.open('rb') as stream:
                    stream.seek(item['offset'])
                    lines = []
                    while True:
                        line = stream.readline()
                        if not line:
                            break
                        line = item['partial'] + line
                        item['partial'] = b''
                        if not line.endswith(b'\n'):
                            item['partial'] = line
                            break
                        if b'event_msg' in line:
                            lines.append(line)
                    item['offset'] = stream.tell()

                for line in lines:
                    try:
                        record = json.loads(line)
                        if record.get('type') != 'event_msg':
                            continue
                        kind = record.get('payload', {}).get('type')
                    except (ValueError, AttributeError):
                        continue
                    if kind == 'task_started':
                        item['active'] = True
                        item['usage'] = None
                    elif kind == 'token_count' and item['active']:
                        info = record['payload'].get('info')
                        if isinstance(info, dict):
                            item['usage'] = info
                    elif kind in ('task_complete', 'turn_aborted'):
                        if kind == 'task_complete' and item['active']:
                            item['completed_usage'] = item['usage']
                            if self.initialized:
                                completed += 1
                        elif kind == 'turn_aborted' and item['active'] and self.initialized:
                            aborted += 1
                        item['active'] = False
                stale_limit = self.STALE_ACTIVE_SECONDS if self.initialized else self.STALE_INITIAL_SECONDS
                if item['active'] and (time.time() - stat.st_mtime) > stale_limit:
                    item['active'] = False
            except OSError:
                continue
        return any(item['active'] for item in self.files.values()), completed, aborted, missing

    def _poll_transcripts(self, cutoff):
        completed = 0
        aborted = 0
        for path, item in list(self.transcripts.items()):
            if not path.exists():
                del self.transcripts[path]

        for path in self._collect_transcripts():
            try:
                stat = path.stat()
                if stat.st_mtime < cutoff and path not in self.transcripts:
                    continue
                item = self.transcripts.get(path)
                if item is None:
                    item = {
                        'offset': 0,
                        'partial': b'',
                        'active': False,
                        'steps': 0,
                        'last_type': None,
                        'last_status': None,
                    }
                    self.transcripts[path] = item
                if stat.st_size < item['offset']:
                    item.update(offset=0, partial=b'', active=False, steps=0)
                item['modified'] = stat.st_mtime_ns
                with path.open('rb') as stream:
                    stream.seek(item['offset'])
                    lines = []
                    while True:
                        line = stream.readline()
                        if not line:
                            break
                        line = item['partial'] + line
                        item['partial'] = b''
                        if not line.endswith(b'\n'):
                            item['partial'] = line
                            break
                        lines.append(line)
                    item['offset'] = stream.tell()

                for line in lines:
                    try:
                        record = json.loads(line)
                    except ValueError:
                        continue
                    step_type = record.get('type')
                    status = record.get('status')
                    item['steps'] += 1
                    item['last_type'] = step_type
                    item['last_status'] = status
                    if step_type == 'USER_INPUT':
                        item['active'] = True
                    elif step_type == 'PLANNER_RESPONSE' and status == 'DONE' and not record.get('tool_calls'):
                        if item['active'] and self.initialized and not self.files:
                            completed += 1
                        item['active'] = False
                    elif status == 'ERROR':
                        if item['active'] and self.initialized and not self.files:
                            aborted += 1
                        item['active'] = False
                stale_limit = self.STALE_ACTIVE_SECONDS if self.initialized else self.STALE_INITIAL_SECONDS
                if item['active'] and (time.time() - stat.st_mtime) > stale_limit:
                    item['active'] = False
            except OSError:
                continue
        return any(item['active'] for item in self.transcripts.values()), completed, aborted

    def poll(self):
        now = time.time()
        cutoff = now - 86400
        hook_working, completed, aborted, missing = self._poll_hooks(cutoff)
        tr_working, tr_completed, tr_aborted = self._poll_transcripts(cutoff)
        self.initialized = True
        return (
            hook_working or tr_working,
            completed + tr_completed,
            aborted + tr_aborted,
            missing,
        )

    def _conversation_id_from_transcript(self, path):
        try:
            return path.parent.parent.parent.name
        except IndexError:
            return ''

    def _read_pulse_context(self, conversation_ids=None):
        """Read live context window and cache hit metrics persisted by antigravity-pulse."""
        root = self.pulse_history_root
        try:
            if not root.is_dir():
                return None
            candidates = list(root.glob('*/*.json'))
        except OSError:
            return None
        if not candidates:
            return None

        preferred = [p for p in candidates if p.stem in (conversation_ids or ())]
        pool = preferred or (candidates if not conversation_ids else [])
        if not pool:
            return None

        best_path = max(pool, key=lambda p: self._safe_mtime(p))
        try:
            payload = json.loads(best_path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            return None
        metrics = payload.get('metrics')
        if not isinstance(metrics, dict):
            return None
        parsed = self._parse_pulse_metrics(metrics, saved_at=payload.get('savedAt'))
        if parsed is not None:
            parsed['conversation_id'] = payload.get('conversationId') or best_path.stem
            parsed['scope'] = best_path.parent.name
        return parsed

    @staticmethod
    def _safe_mtime(path):
        try:
            return path.stat().st_mtime_ns
        except OSError:
            return 0

    def context_usage(self):
        active_hooks = [item for item in self.files.values() if item['active'] and item.get('usage')]
        if active_hooks:
            info = max(active_hooks, key=lambda item: item.get('modified', 0))['usage']
            parsed = self._parse_context_usage(info)
            if parsed:
                return parsed
        active_tr = [
            (path, item) for path, item in self.transcripts.items() if item['active']
        ]
        if active_tr:
            latest_path, latest = max(active_tr, key=lambda pair: pair[1].get('modified', 0))
            conv_id = self._conversation_id_from_transcript(latest_path)
            pulse = self._read_pulse_context(conversation_ids={conv_id} if conv_id else None)
            if pulse is not None:
                return pulse
            return {
                'kind': 'transcript',
                'steps': latest['steps'],
                'last_type': latest['last_type'],
                'last_status': latest['last_status'],
            }
        return None

    def context_snapshot(self):
        active = self.context_usage()
        if active is not None and active.get('kind') != 'transcript':
            return active, False
        completed_hooks = [
            item for item in self.files.values()
            if item.get('completed_usage') is not None
            and item.get('modified', 0) >= (time.time() - 86400) * 1_000_000_000
        ]
        if completed_hooks:
            info = max(completed_hooks, key=lambda item: item['modified'])['completed_usage']
            parsed = self._parse_context_usage(info)
            if parsed:
                return parsed, True

        conv_ids = set()
        if self.transcripts:
            latest_path, _ = max(self.transcripts.items(), key=lambda pair: pair[1].get('modified', 0))
            cid = self._conversation_id_from_transcript(latest_path)
            if cid:
                conv_ids.add(cid)
        pulse = self._read_pulse_context(conversation_ids=conv_ids or None)
        if pulse is None and conv_ids:
            pulse = self._read_pulse_context()
        if pulse is not None:
            is_running = 'RUNNING' in str(pulse.get('status') or '').upper()
            return pulse, not is_running

        if active is not None:
            return active, False
        if self.transcripts:
            latest = max(self.transcripts.values(), key=lambda item: item.get('modified', 0))
            return {
                'kind': 'transcript',
                'steps': latest['steps'],
                'last_type': latest['last_type'],
                'last_status': latest['last_status'],
            }, True
        return None, False

    @staticmethod
    def _parse_pulse_metrics(metrics, saved_at=None):
        """Parse antigravity-pulse metrics into unified context window & cache hit stats."""
        ctx = metrics.get('context') if isinstance(metrics.get('context'), dict) else {}
        used = ctx.get('usedTokens')
        window = ctx.get('maxTokens')

        def valid_int(value):
            return isinstance(value, int) and not isinstance(value, bool) and value >= 0

        # Match inline-widget.cjs: prefer taskUsage (with subagents) cache when present
        task_usage = metrics.get('taskUsage') if isinstance(metrics.get('taskUsage'), dict) else None
        if task_usage and (task_usage.get('subagents') or 0) > 0 and isinstance(task_usage.get('cache'), dict):
            cache_obj = task_usage['cache']
        elif isinstance(metrics.get('cache'), dict):
            cache_obj = metrics['cache']
        else:
            cache_obj = {}

        hit_rate = cache_obj.get('hitRate')
        if isinstance(hit_rate, (int, float)) and not isinstance(hit_rate, bool) and 0 <= hit_rate <= 1:
            rate = float(hit_rate) * 100.0
        else:
            cached = cache_obj.get('cachedTokens')
            inp = cache_obj.get('inputTokens')
            rate = (100.0 * cached / inp) if (valid_int(cached) and valid_int(inp) and inp > 0) else None

        if not valid_int(used) and rate is None:
            return None

        used_pct = None
        frac = ctx.get('usedFraction')
        if isinstance(frac, (int, float)) and not isinstance(frac, bool) and 0 <= frac <= 1:
            used_pct = float(frac) * 100.0
        elif valid_int(used) and valid_int(window) and window > 0:
            used_pct = 100.0 * used / window

        return {
            'kind': 'pulse',
            'used': used if valid_int(used) else None,
            'window': window if (valid_int(window) and window > 0) else None,
            'used_pct': used_pct,
            'rate': rate,
            'cached_tokens': cache_obj.get('cachedTokens') if valid_int(cache_obj.get('cachedTokens')) else None,
            'input_tokens': cache_obj.get('inputTokens') if valid_int(cache_obj.get('inputTokens')) else None,
            'model': ctx.get('model') or metrics.get('model'),
            'status': metrics.get('status'),
            'tps': metrics.get('latestTps') if isinstance(metrics.get('latestTps'), (int, float)) else metrics.get('tps'),
            'saved_at': saved_at or metrics.get('lastActiveAt'),
        }

    @staticmethod
    def _parse_context_usage(info):
        if not isinstance(info, dict):
            return None
        usage = info.get('last_token_usage')
        window = info.get('model_context_window')
        if not isinstance(usage, dict):
            return None
        incoming = usage.get('input_tokens')
        outgoing = usage.get('output_tokens')
        cached = usage.get('cached_input_tokens')

        def valid(value):
            return isinstance(value, int) and not isinstance(value, bool) and value >= 0

        if not all(valid(value) for value in (incoming, outgoing, window)) or window == 0:
            return None
        rate = 100 * cached / incoming if valid(cached) and incoming > 0 and cached <= incoming else None
        return {'used': incoming + outgoing, 'window': window, 'rate': rate}
