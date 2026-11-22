"""Dialogue lines and Antigravity status formatting for Gemini Catgirl."""
import os
import random
from pathlib import Path

DIALOGUE = {
    'task-start': (
        '喵～收到主人的新任务啦，看本喵喵的！',
        '✦ 星芒连线中，交给本喵喵吧主人～',
        '有活干啦！尾巴竖起来了喵，主人看好了～',
    ),
    'task-complete': (
        '✦ 搞定喵！主人快来看看这一轮结果吧～',
        '这一轮回复完啦，主人记得检查一下喵！',
        '喵呜～大功告成，主人快夸夸本喵喵！',
    ),
    'task-aborted': (
        '喵呜……这一轮被中止了，主人看看记录吧。',
        '尾巴打结啦，这次回复中断了喵，主人别急。',
    ),
    'task-unknown': (
        '喵？有一份会话记录不见了，状态暂时不确定喵，主人。',
    ),
    'ambient-running': (
        '哼哼，本喵喵在为主人练习多模态反应速度～',
        '随便活动一下爪子，才不是在偷懒喵，主人！',
    ),
    'ambient-review': (
        '嘘……本喵喵在帮主人数窗外的四角星✦',
        '唔，让本喵喵帮主人想点厉害的点子喵～',
    ),
    'ambient-waiting': (
        '本喵喵就在桌面陪着主人呢喵～',
        '哼，才不是特意在等主人，只是刚好趴在这里。',
    ),
    'idle': (
        '（尾巴轻轻甩来甩去）主人有什么吩咐喵？',
        '✦ 本喵喵随时待命中，主人尽管叫我喵～',
    ),
    'running-right': (
        '冲呀！替主人往右边巡逻去咯喵～',
        '让开让开，双子星猫猫为主人加速中！',
    ),
    'running-left': (
        '转个弯绕回来看看主人喵～',
        '哼，主人追得上本喵喵的步伐吗？',
    ),
    'waving': (
        '喵～主人，本喵喵在这里看到没有？',
        '嗨呀主人！跟 Gemini 猫猫打个招呼吧✦',
    ),
    'jumping': (
        '反——重——力——跳给主人看啦喵！',
        '好耶喵！陪在主人身边今天心情超棒的✦',
    ),
    'failed': (
        '唔……不许笑本喵喵刚才的表情喵，主人！',
        '哼，才没有和主人闹别扭呢……才怪。',
    ),
    'waiting': (
        '本喵喵乖乖等着，主人慢慢想喵～',
        '等主人确认哦，不着急的喵。',
    ),
    'running': (
        '正在为主人飞速翻代码、写逻辑喵～',
        '交给本喵喵吧主人，多模态全开运转中✦',
    ),
    'review': (
        '让本喵喵替主人仔细瞧瞧……嗯嗯喵。',
        '左眼帮主人看细节，右眼帮主人找灵感喵✦',
    ),
    'startup': (
        '喵～哈基米喵上线！主人今天想写点什么好呢？✦',
        '反重力桌面猫猫就位！主人有任务随时叫本喵喵～',
        '紫蓝星芒闪烁中✦ 本喵喵准备好陪主人干活啦！',
        '哈基米能量满格喵～今天也要和主人一起加油哦！',
    ),
    'interaction': (
        '呼噜呼噜……主人再摸头耳朵要抖啦喵～',
        '喵？主人找本喵喵有什么事吗？',
        '别误会，本喵喵只是顺便在桌面散步而已，才不是看主人呢～',
        '主人遇到难题了？让本喵喵用四角星帮你照亮思路✦',
        '主人记得喝口水休息一下喵，别把本喵喵看累了～',
        '尾巴可是很敏感的，主人不许乱拽喵！',
        '哼，主人夸奖本喵喵的话再多说两句也行哦～',
        '悄悄告诉主人，本喵喵一直都在留意主人的 Antigravity 哦✦',
    ),
    'sleep': (
        '哈——啊……主人，本喵喵有点困了，先眯一会儿喵……',
        'CPU 微微发热啦，本喵喵先去打个盹 Zzz…主人有事再叫我。',
        '不是偷懒，是猫猫陪主人干活前的必要充电时间喵～',
        '晚安主人喵……有新任务再把本喵喵叫醒哦。',
    ),
    'wake': (
        '喵呜！已经醒啦，主人吵什么呀～',
        '哈啊……才没有睡迷糊呢，随时可以为主人开工喵！',
        '伸个懒腰——✦ 本喵喵满血复活来陪主人啦！',
        '主人叫醒本喵喵啦？是不是有好玩的任务了喵？',
    ),
}

_last_lines = {}


def pick_line(category):
    options = DIALOGUE[category]
    candidates = [line for line in options if line != _last_lines.get(category)]
    selected = random.choice(candidates or options)
    _last_lines[category] = selected
    return selected


def _compact_tokens(value):
    """Format token count compactly like antigravity-pulse (K / M / B)."""
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
        return '—'
    for base, suffix, next_base, next_suffix in (
        (1_000_000_000_000, 'T', 0, ''),
        (1_000_000_000, 'B', 1_000_000_000_000, 'T'),
        (1_000_000, 'M', 1_000_000_000, 'B'),
        (1_000, 'K', 1_000_000, 'M'),
    ):
        if value >= base:
            rounded = round(value / base, 1)
            if next_base and rounded * base >= next_base:
                return f'1{next_suffix}'
            text = f'{rounded:.1f}'.rstrip('0').rstrip('.')
            return f'{text}{suffix}'
    return str(int(value))


def _parse_iso_ts(value):
    if not isinstance(value, str) or not value.strip():
        return None
    from datetime import datetime
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp()
    except ValueError:
        return None


def _format_local_time(ts):
    from datetime import datetime
    return datetime.fromtimestamp(ts).strftime('%m-%d %H:%M')


def format_context_usage(usage, recent=False):
    if usage is None:
        return '本喵喵暂时查不到 Antigravity 对话状态，还没检测到近期记录喵。'
    if usage.get('kind') == 'pulse':
        used = usage.get('used')
        window = usage.get('window')
        used_pct = usage.get('used_pct')
        rate = usage.get('rate')
        model = usage.get('model')
        ctx_text = f'{_compact_tokens(used)} / {_compact_tokens(window)}'
        if isinstance(used_pct, (int, float)):
            ctx_text += f' ({round(used_pct)}%)'
        cache_text = f'{rate:.1f}%' if isinstance(rate, (int, float)) else '不可用'
        prefix = '✦ 上下文快照：' if recent else '✦ 当前上下文状态：'
        lines = [prefix, f'上下文 {ctx_text}', f'缓存命中率 {cache_text}']
        if model:
            lines.append(f'模型 {model}')
        return '\n'.join(lines)
    if usage.get('kind') == 'transcript':
        steps = usage.get('steps', 0)
        last_type = usage.get('last_type') or '未知'
        last_status = usage.get('last_status') or '未知'
        prefix = '最近一次 Antigravity 对话：' if recent else '当前 Antigravity 对话状态：'
        return f'{prefix}\n累计记录 {steps} 步\n最新节点 {last_type} ({last_status})'
    used = usage['used']
    window = usage['window']
    rate = usage.get('rate')
    cache = f'{rate:.1f}%' if rate is not None else '不可用'
    prefix = '上次可用上下文数据：' if recent else random.choice(('本喵喵查到了：', '✦ 上下文状态在这里：'))
    return f'{prefix}\n上下文 {used / 1000:.1f}k / {window / 1000:.1f}k\n缓存命中率 {cache}'


def _detect_active_scope(pulse_data_root):
    history_root = pulse_data_root / 'history-v1'
    if not history_root.is_dir():
        return None
    try:
        files = list(history_root.glob('*/*.json'))
    except OSError:
        return None
    if not files:
        return None
    newest = max(files, key=lambda p: p.stat().st_mtime_ns)
    return newest.parent.name


def _read_live_usage_totals(pulse_data_root, scope, now_ts):
    import json
    from datetime import datetime

    usage_root = pulse_data_root / 'usage-v1'
    scope_dir = usage_root / scope if scope else None
    if scope_dir is None or not scope_dir.is_dir():
        return None
    five_h_ms = int((now_ts - 5 * 3600) * 1000)
    today_dt = datetime.fromtimestamp(now_ts).replace(hour=0, minute=0, second=0, microsecond=0)
    today_ms = int(today_dt.timestamp() * 1000)
    tokens_5h = 0
    tokens_today = 0
    try:
        files = list(scope_dir.glob('*.json'))
    except OSError:
        return None
    for path in files:
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        for rec in data.get('records', []):
            if not isinstance(rec, dict):
                continue
            at = rec.get('at')
            if not isinstance(at, (int, float)):
                continue
            tok = sum(
                rec.get(k) for k in ('uncached', 'cacheRead', 'cacheWrite', 'output')
                if isinstance(rec.get(k), (int, float))
            )
            if at >= five_h_ms:
                tokens_5h += tok
            if at >= today_ms:
                tokens_today += tok
    return tokens_5h, tokens_today


def _format_quota_bucket(bucket, label_prefix, now_ts):
    pct = bucket.get('remainingPercent')
    reset_ts = _parse_iso_ts(bucket.get('resetTime'))
    if not isinstance(pct, (int, float)):
        return f'{label_prefix} 不可用'
    if reset_ts is not None and reset_ts <= now_ts:
        return f'{label_prefix} 已重置(旧{pct:.0f}%待面板刷新)'
    suffix = f' ({_format_local_time(reset_ts)}重置)' if reset_ts is not None else ''
    return f'{label_prefix} 剩{pct:.0f}%{suffix}'


def read_antigravity_quota(pulse_data_root=None, accounts_path=None, now=None):
    """Read live token consumption (usage-v1) and cached account quota snapshot (non-secret fields only)."""
    import hashlib
    import json
    import time

    now_ts = time.time() if now is None else float(now)
    pulse_dir = (
        Path(pulse_data_root)
        if pulse_data_root is not None
        else Path.home() / '.gemini/antigravity/sidecar_data/antigravity-pulse/panel/data'
    )
    acc_file = (
        Path(accounts_path)
        if accounts_path is not None
        else Path.home() / '.gemini/config/plugins/account-switcher/data/accounts.json'
    )

    scope = _detect_active_scope(pulse_dir)
    usage_totals = _read_live_usage_totals(pulse_dir, scope, now_ts)

    account_info = None
    if acc_file.is_file():
        try:
            raw = json.loads(acc_file.read_text(encoding='utf-8'))
            accounts = raw.get('accounts', []) if isinstance(raw, dict) else []
            # Only match safe non-secret metadata (email, label, planTier, quotaSummary)
            if scope:
                for acc in accounts:
                    email = acc.get('email')
                    if isinstance(email, str) and hashlib.sha256(email.encode('utf-8')).hexdigest() == scope:
                        account_info = acc
                        break
            if account_info is None and accounts:
                account_info = max(
                    accounts,
                    key=lambda a: _parse_iso_ts(a.get('lastActiveAt')) or 0.0,
                )
        except (OSError, ValueError):
            account_info = None

    lines = []
    if account_info:
        label = account_info.get('label') or account_info.get('email') or '当前账号'
        tier = account_info.get('planTier')
        header = f'✦ {label}' + (f' ({tier})' if tier else '')
        lines.append(header)
        qs = account_info.get('quotaSummary') if isinstance(account_info.get('quotaSummary'), dict) else None
        if qs and isinstance(qs.get('groups'), list):
            for group in qs['groups']:
                gname = str(group.get('displayName') or '')
                short_name = 'Gemini' if 'gemini' in gname.lower() else 'Claude/GPT' if ('claude' in gname.lower() or 'gpt' in gname.lower()) else gname
                buckets = {b.get('window'): b for b in group.get('buckets', []) if isinstance(b, dict)}
                parts = []
                if '5h' in buckets:
                    parts.append(_format_quota_bucket(buckets['5h'], '5h', now_ts))
                if 'weekly' in buckets:
                    parts.append(_format_quota_bucket(buckets['weekly'], '周', now_ts))
                if parts:
                    lines.append(f'{short_name}: ' + ' | '.join(parts))
            updated_ts = _parse_iso_ts(qs.get('updatedAt'))
            if updated_ts is not None:
                age_min = max(0, int((now_ts - updated_ts) // 60))
                stale_note = ' (较旧,点切换器面板刷新)' if age_min >= 30 else ''
                lines.append(f'配额快照：{_format_local_time(updated_ts)}{stale_note}')

    if usage_totals is not None:
        t5h, tday = usage_totals
        lines.append(f'实时消耗：近5h {_compact_tokens(t5h)} · 今日 {_compact_tokens(tday)}')

    if not lines:
        return '本喵喵暂未找到 Antigravity 用量或额度快照，请主人先打开 Antigravity 面板查看喵。'
    return '\n'.join(lines)


def _windows_antigravity_counts():
    """Inspect Antigravity main and language-server processes on Windows via PowerShell."""
    import json
    import subprocess

    query = (
        "Get-CimInstance Win32_Process | Where-Object { "
        "$_.Name -match 'antigravity|language_server' -or $_.CommandLine -match 'antigravity' "
        "} | Select-Object Name,CommandLine | ConvertTo-Json -Compress"
    )
    try:
        res = subprocess.run(
            ['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', query],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=8,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
        )
        raw = res.stdout.decode('utf-8', errors='replace').strip()
        if not raw:
            return 0, 0
        items = json.loads(raw)
        if isinstance(items, dict):
            items = [items]
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return 0, 0

    main_count = 0
    sidecar_count = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        name = str(item.get('Name') or '').lower()
        cmd = str(item.get('CommandLine') or '').lower()
        if 'language_server' in name or 'language_server' in cmd or 'sidecar_sdk' in cmd:
            sidecar_count += 1
        elif name == 'antigravity.exe' and '--type=' not in cmd:
            main_count += 1
    return main_count, sidecar_count


def read_antigravity_status(proc_root='/proc', brain_root=None, pulse_data_root=None):
    """Inspect local Antigravity main process, sidecars, and active brain sessions."""
    main_pids = []
    sidecar_count = 0
    if os.name == 'nt' and proc_root == '/proc':
        main_count, sidecar_count = _windows_antigravity_counts()
        main_pids = [str(i) for i in range(main_count)]
    else:
        proc = Path(proc_root)
        uid = os.getuid() if hasattr(os, 'getuid') else None
        try:
            for entry in proc.iterdir():
                if not entry.name.isdigit():
                    continue
                try:
                    if uid is not None and entry.stat().st_uid != uid:
                        continue
                    cmdline = (entry / 'cmdline').read_bytes().decode(errors='replace')
                    if 'antigravity' not in cmdline.lower():
                        continue
                    if 'language_server' in cmdline or 'sidecar_sdk' in cmdline:
                        sidecar_count += 1
                    elif '--type=' not in cmdline and '--type\x00' not in cmdline:
                        if 'antigravity' in cmdline.split('\x00', 1)[0].lower():
                            main_pids.append(entry.name)
                except (OSError, ProcessLookupError):
                    continue
        except OSError:
            pass

    brain = Path(brain_root) if brain_root is not None else Path.home() / '.gemini/antigravity/brain'
    transcripts = []
    if brain.is_dir():
        try:
            transcripts = list(brain.glob('*/.system_generated/logs/transcript.jsonl'))
        except OSError:
            transcripts = []

    if not main_pids:
        return f'Antigravity 主程序当前未运行喵。\n本地历史对话：{len(transcripts)} 个'
    return (
        f'Antigravity 运行中（主进程 {len(main_pids)} 个，语言服务 {sidecar_count} 个）\n'
        f'本地对话档案：{len(transcripts)} 个\n'
        '右键「查询额度 / 上下文状态」查看实时用量喵✦'
    )
