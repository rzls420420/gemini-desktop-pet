"""Create Linux (.tar.gz) and Windows 11 (.zip) runtime packages without development clutter."""
import sys
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from catgirl_pet.animation import ANIMATIONS

VERSION = 'v1.0.0'


def collect_files(platform):
    if platform not in ('linux', 'windows'):
        raise ValueError(platform)
    template = ROOT / 'packaging' / platform
    for path in sorted(template.iterdir()):
        if path.is_file():
            yield path.name, path
    for extra_name in ('SOUL.md', 'NOTICE.md'):
        extra = ROOT / extra_name
        if extra.is_file():
            yield extra.name, extra
    for path in sorted((ROOT / 'catgirl_pet').glob('*.py')):
        if platform == 'windows' and path.name == 'monitor.py':
            continue
        yield f'catgirl_pet/{path.name}', path
    counts = {name: data[0] for name, data in ANIMATIONS.items()}
    counts['sleep'] = 16
    for state, count in counts.items():
        for i in range(count):
            name = f'assets/transparent-v2/{state}/{i:02d}.png'
            path = ROOT / name
            if not path.is_file():
                raise FileNotFoundError(path)
            yield name, path


def main():
    dest = ROOT / 'dist'
    dest.mkdir(exist_ok=True)
    linux = dest / f'gemini-desktop-pet-{VERSION}-linux.tar.gz'
    windows = dest / f'gemini-desktop-pet-{VERSION}-win11.zip'
    with tarfile.open(linux, 'w:gz') as archive:
        for name, path in collect_files('linux'):
            info = archive.gettarinfo(str(path), arcname=f'gemini-desktop-pet-linux/{name}')
            info.mode = 0o755 if name.endswith('.sh') else 0o644
            with path.open('rb') as data:
                archive.addfile(info, data)
    with zipfile.ZipFile(windows, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, path in collect_files('windows'):
            archive.write(path, arcname=f'gemini-desktop-pet-win11/{name}')
    print(linux)
    print(windows)


if __name__ == '__main__':
    main()
