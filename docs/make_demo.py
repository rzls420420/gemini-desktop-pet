from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONT = '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'
font = ImageFont.truetype(FONT, 22)
small = ImageFont.truetype(FONT, 15)

scenes = [
    ('waving', 8, ['哼，本喵喵来陪你写代码啦✦']),
    ('running-right', 16, ['收到新任务！侧身冲刺开工喵～']),
    ('jumping', 10, ['✦ 搞定喵！反重力跳起来庆祝！']),
    ('idle', 12, ['上下文与缓存查询（模拟）', '上下文 160.9K / 512K (31%)  ·  缓存命中率 84.3%']),
    ('running', 12, ['额度与用量查询（模拟）', '5h 剩余 85%  ·  每周剩余 95%  ·  今日已用 6.4M']),
    ('sleep', 16, ['暂时没有任务，本喵喵先眯一会儿 Zzz…']),
]

frames = []
for state, count, lines in scenes:
    for index in range(count):
        sprite = Image.open(ROOT / 'assets/transparent-v2' / state / f'{index:02}.png').convert('RGBA')
        sprite.thumbnail((300, 280), Image.Resampling.LANCZOS)
        frame = Image.new('RGBA', (760, 340), '#f5f7fb')
        frame.alpha_composite(sprite, (20 + (300 - sprite.width) // 2, 330 - sprite.height))
        draw = ImageDraw.Draw(frame)
        draw.rounded_rectangle((320, 68, 735, 224), radius=16, fill='white', outline='#7b5cd6', width=2)
        for line_no, line in enumerate(lines):
            draw.text((340, 98 + line_no * 42), line, font=font if line_no == 0 else small, fill='#2b2140')
        draw.text((342, 240), '哈基米小姐桌面宠物演示  ·  额度与上下文为模拟数据', font=small, fill='#696779')
        frames.append(frame.convert('RGB'))

out = ROOT / 'docs/demo.gif'
out.parent.mkdir(parents=True, exist_ok=True)
frames[0].save(out, save_all=True, append_images=frames[1:], duration=130, loop=0, optimize=True)
print(f'Saved {out} ({out.stat().st_size} bytes, {len(frames)} frames)')
