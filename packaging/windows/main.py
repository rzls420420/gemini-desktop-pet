import ctypes
import subprocess
import sys
import time
from pathlib import Path

from catgirl_pet.autostart import is_enabled


def antigravity_running():
    query = (
        "Get-CimInstance Win32_Process -Filter \"Name='Antigravity.exe'\" | "
        "Where-Object { $_.CommandLine -notmatch '--type=' "
        "-and $_.CommandLine -notmatch 'language_server|sidecar_sdk' } | "
        "Select-Object -First 1 -ExpandProperty ProcessId"
    )
    result = subprocess.run(
        ['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', query],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        timeout=10,
        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
    )
    return bool(result.stdout.strip())


def monitor():
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, 'Local\\GeminiCatgirlAntigravityMonitor')
    if not mutex or ctypes.windll.kernel32.GetLastError() == 183:
        return
    pet = None
    previous = False
    while True:
        try:
            running = antigravity_running()
        except (OSError, subprocess.TimeoutExpired):
            time.sleep(5)
            continue
        try:
            enabled = is_enabled()
        except OSError:
            enabled = False
        if running and not previous and not enabled and (pet is None or pet.poll() is not None):
            command = (
                [sys.executable, '--pet']
                if getattr(sys, 'frozen', False)
                else [sys.executable, str(Path(__file__).resolve()), '--pet']
            )
            pet = subprocess.Popen(command, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        elif previous and not running and pet and pet.poll() is None and not enabled:
            pet.terminate()
            try:
                pet.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pet.kill()
                pet.wait()
            pet = None
        previous = running
        time.sleep(3)


if __name__ == '__main__':
    if '--pet' in sys.argv:
        from catgirl_pet.app import main

        sys.argv = sys.argv[:1]
        sys.exit(main())
    monitor()
