"""Background process monitor that launches/stops the pet alongside Antigravity."""
try:
    import fcntl
except ImportError:
    fcntl = None
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from catgirl_pet.autostart import is_enabled


def is_antigravity_main(args, executable=None):
    if not args:
        return False
    try:
        first = shlex.split(args[0])
    except ValueError:
        return False
    if not first:
        return False
    target = executable or first[0]
    if Path(target).name.lower() != 'antigravity':
        return False
    options = first[1:] + args[1:]
    if any(arg == '--type' or arg.startswith('--type=') for arg in options):
        return False
    if any('sidecar_sdk' in arg or arg == 'main.mjs' for arg in options):
        return False
    return True


def antigravity_running():
    for process in Path('/proc').iterdir():
        if not process.name.isdigit():
            continue
        try:
            if process.stat().st_uid != os.getuid():
                continue
            args = (process / 'cmdline').read_bytes().split(b'\0')
            executable = os.readlink(process / 'exe')
            if is_antigravity_main([arg.decode(errors='replace') for arg in args if arg], executable):
                return True
        except (OSError, ProcessLookupError):
            continue
    return False


def next_action(was_running, running, pet_running, autostart_enabled=False):
    if autostart_enabled:
        return None
    if running and not was_running and not pet_running:
        return 'start'
    if was_running and not running and pet_running:
        return 'stop'
    return None


def main():
    if fcntl is None:
        raise RuntimeError('Linux monitor requires fcntl; on Windows use main.py')
    runtime = Path(os.environ.get('XDG_RUNTIME_DIR', '/tmp'))
    lock = open(runtime / f'gemini-catgirl-monitor-{os.getuid()}.lock', 'w')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return 0
    previous = False
    pet = None
    while True:
        running = antigravity_running()
        active = pet is not None and pet.poll() is None
        try:
            enabled = is_enabled()
        except OSError:
            enabled = False
        action = next_action(previous, running, active, enabled)
        if action == 'start':
            pet = subprocess.Popen([sys.executable, '-m', 'catgirl_pet.app'], cwd=ROOT)
        elif action == 'stop':
            pet.terminate()
            try:
                pet.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pet.kill()
                pet.wait()
            pet = None
        previous = running
        time.sleep(2)


if __name__ == '__main__':
    sys.exit(main())
