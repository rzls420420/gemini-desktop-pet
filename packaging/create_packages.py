"""Create Linux (.tar.gz) and Windows 11 (.zip) runtime packages without development clutter."""
import io
import sys
import tarfile
import zipfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from catgirl_pet.animation import ANIMATIONS

VERSION = 'v1.0.0'
RELEASE_FRAME_SIZE = (576, 624)


def _package_bytes(name, path):
    if name.endswith('.png'):
        with Image.open(path) as im:
            im = im.convert('RGBA')
            if im.size != RELEASE_FRAME_SIZE:
                im = im.resize(RELEASE_FRAME_SIZE, Image.Resampling.LANCZOS)
            buf = io.BytesIO()
            im.save(buf, format='PNG', optimize=True)
            return buf.getvalue()
    return path.read_bytes()


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
    with tarfile.open(linux, 'w:gz', compresslevel=9) as archive:
        for name, path in collect_files('linux'):
            payload = _package_bytes(name, path)
            info = archive.gettarinfo(str(path), arcname=f'gemini-desktop-pet-linux/{name}')
            info.size = len(payload)
            info.mode = 0o755 if name.endswith('.sh') else 0o644
            archive.addfile(info, io.BytesIO(payload))
    with zipfile.ZipFile(windows, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, path in collect_files('windows'):
            archive.writestr(f'gemini-desktop-pet-win11/{name}', _package_bytes(name, path))
    print(linux)
    print(windows)


if __name__ == '__main__':
    main()
