"""Cross-platform autostart configuration for Gemini Catgirl Desktop Pet."""
import os
import subprocess
import sys
from pathlib import Path

NAME = 'GeminiCatgirlDesktopPet'
ROOT = Path(__file__).resolve().parent.parent


def desktop_quote(value):
    value = str(value).replace('%', '%%')
    for char in ('\\', '"', '`', '$'):
        value = value.replace(char, '\\' + char)
    return '"' + value + '"'


def linux_entry():
    config = Path(os.environ.get('XDG_CONFIG_HOME') or Path.home() / '.config')
    return config / 'autostart' / 'gemini-catgirl-pet.desktop'


def windows_command():
    if getattr(sys, 'frozen', False):
        return subprocess.list2cmdline([sys.executable, '--pet'])
    python = Path(sys.executable)
    pythonw = python.with_name('pythonw.exe')
    if pythonw.exists():
        python = pythonw
    return subprocess.list2cmdline([str(python), str(ROOT / 'main.py'), '--pet'])


def is_enabled(platform=None):
    platform = platform or sys.platform
    if platform.startswith('linux'):
        return linux_entry().is_file()
    if platform == 'win32':
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Run') as key:
                winreg.QueryValueEx(key, NAME)
            return True
        except FileNotFoundError:
            return False
    return False


def set_enabled(enabled, platform=None):
    platform = platform or sys.platform
    if platform.startswith('linux'):
        entry = linux_entry()
        if enabled:
            entry.parent.mkdir(parents=True, exist_ok=True)
            command = ' '.join(desktop_quote(arg) for arg in (sys.executable, '-m', 'catgirl_pet.app'))
            entry.write_text(
                '[Desktop Entry]\nType=Application\nName=Gemini Catgirl Desktop Pet\n'
                f'Exec={command}\nPath={ROOT}\nTerminal=false\n',
                encoding='utf-8',
            )
        else:
            entry.unlink(missing_ok=True)
        return
    if platform == 'win32':
        import winreg
        with winreg.CreateKeyEx(
            winreg.HKEY_CURRENT_USER,
            r'Software\Microsoft\Windows\CurrentVersion\Run',
            0,
            winreg.KEY_SET_VALUE,
        ) as key:
            if enabled:
                winreg.SetValueEx(key, NAME, 0, winreg.REG_SZ, windows_command())
            else:
                try:
                    winreg.DeleteValue(key, NAME)
                except FileNotFoundError:
                    pass
        return
    raise OSError('当前系统不支持开机启动')
