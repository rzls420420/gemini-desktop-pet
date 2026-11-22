"""Download full CrossPet Gemini library and build v2 transparent animations."""
import io
import json
import urllib.request
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter, ImageOps

ROOT = Path(__file__).resolve().parent
SOURCE_DIR = ROOT / 'assets/source'
V2_SOURCE_DIR = ROOT / 'assets/transparent-v2/source'
V2_OUT_DIR = ROOT / 'assets/transparent-v2'
BASE_URL = 'https://raw.githubusercontent.com/lokicorvus/crosspet/main/characters/gemini/'
TREE_URL = 'https://api.github.com/repos/lokicorvus/crosspet/git/trees/main?recursive=1'

ARTIFACT_DIR = Path('/home/ls/.gemini/antigravity/brain/ae039632-7c7b-47be-9297-f673360759a4')
IDLE_WAVING_JPG = ARTIFACT_DIR / 'idle_waving_1795184224337.jpg'
RUNNING_JPG = ARTIFACT_DIR / 'crosspet_gemini_running_sheet_final_1795220887558.jpg'
SLEEP_JPG = ARTIFACT_DIR / 'sleep_1795184260410.jpg'

SIZE = (768, 832)
GROUND = 782
TARGET_HEIGHT = 650

CORE_SPRITES = [
    'annoyed', 'asking', 'avatar', 'busy_left', 'busy_right', 'bye',
    'coaxed', 'compact', 'delegating', 'dizzy', 'drawing', 'drink',
    'edge_left', 'edge_left_peek', 'edge_right', 'edge_right_peek',
    'fest_christmas', 'fest_dragonboat', 'fest_halloween', 'fest_lantern',
    'fest_midautumn', 'fest_national', 'fest_newyear', 'fest_spring',
    'float', 'forgiven', 'greet_afternoon', 'greet_dawn', 'greet_evening',
    'greet_morning', 'greet_night', 'greet_noon', 'happy', 'hum',
    'idle', 'idle-2', 'idle-3', 'listening', 'oops', 'pat',
    'proud', 'puffed', 'reading', 'redhot', 'roll_call', 'running',
    'searching', 'sleeping', 'stretch', 'sulk', 'surprised',
    'swamped_left', 'swamped_right', 'thinking', 'tired', 'update',
    'writing', 'yawn',
]


def _fetch_bytes(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read()


def download_all_sources():
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    names = list(CORE_SPRITES)
    try:
        tree = json.loads(_fetch_bytes(TREE_URL).decode('utf-8'))
        remote = sorted(
            Path(item['path']).stem
            for item in tree.get('tree', [])
            if item.get('path', '').startswith('characters/gemini/')
            and item.get('path', '').endswith('.webp')
            and Path(item['path']).stem not in ('portrait', 'portrait-card')
        )
        if remote:
            names = remote
    except Exception:
        pass

    for name in names:
        dst = SOURCE_DIR / f'{name}.webp'
        if dst.exists():
            continue
        data = _fetch_bytes(f'{BASE_URL}{name}.webp')
        im = Image.open(io.BytesIO(data)).convert('RGBA')
        alpha = np.array(im)[:, :, 3]
        if (alpha == 0).sum() == 0:
            continue
        dst.write_bytes(data)
    return names


def remove_white_bg_floodfill(im, white_thresh=240, max_sat=24):
    """Remove exterior connected white background while keeping interior whites."""
    rgba = np.array(im.convert('RGBA'))
    rgb = rgba[:, :, :3].astype(np.int16)
    h, w = rgb.shape[:2]

    cmin = rgb.min(axis=2)
    cmax = rgb.max(axis=2)
    is_bg_candidate = (cmin >= white_thresh) & ((cmax - cmin) <= max_sat)

    visited = np.zeros((h, w), dtype=bool)
    q = deque()
    for x in range(w):
        for y in (0, h - 1):
            if is_bg_candidate[y, x] and not visited[y, x]:
                visited[y, x] = True
                q.append((y, x))
    for y in range(h):
        for x in (0, w - 1):
            if is_bg_candidate[y, x] and not visited[y, x]:
                visited[y, x] = True
                q.append((y, x))

    while q:
        cy, cx = q.popleft()
        for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
            if 0 <= ny < h and 0 <= nx < w and not visited[ny, nx] and is_bg_candidate[ny, nx]:
                visited[ny, nx] = True
                q.append((ny, nx))

    rgba[visited, 3] = 0
    # Soften 1px fringe bordering the removed background to avoid white halos.
    alpha_img = Image.fromarray(rgba[:, :, 3], 'L')
    eroded = np.array(alpha_img.filter(ImageFilter.MinFilter(3)))
    fringe = (rgba[:, :, 3] > 0) & (eroded == 0) & (cmin > 205) & ((cmax - cmin) <= 35)
    rgba[fringe, 3] = np.clip((245 - cmin[fringe]) * 4, 0, 220).astype(np.uint8)
    return Image.fromarray(rgba, 'RGBA')


def _find_valley(counts, target, radius=60):
    lo = max(1, target - radius)
    hi = min(len(counts) - 1, target + radius)
    win = counts[lo:hi]
    min_val = int(win.min())
    indices = np.where(win == min_val)[0] + lo
    return int((indices[0] + indices[-1]) // 2)


def split_grid_cells(sheet_path):
    sheet = Image.open(sheet_path).convert('RGBA')
    w, h = sheet.size
    rgb = np.array(sheet.convert('RGB'))
    non_white = ((rgb[:, :, 0] < 245) | (rgb[:, :, 1] < 245) | (rgb[:, :, 2] < 245)).astype(np.int32)

    mid_y = _find_valley(non_white.sum(axis=1), h // 2, radius=45)
    row_bounds = [(0, mid_y), (mid_y, h)]

    cells = []
    for top, bottom in row_bounds:
        col_sum = non_white[top:bottom].sum(axis=0)
        col_edges = [0] + [_find_valley(col_sum, round(w * i / 4), radius=60) for i in (1, 2, 3)] + [w]
        row = []
        for i in range(4):
            cell = sheet.crop((col_edges[i], top, col_edges[i + 1], bottom))
            row.append(remove_white_bg_floodfill(cell))
        cells.append(row)
    return cells


def _draw_sleep_bubble(size_px=56):
    """Render an anti-aliased anime translucent cyan sleep bubble tilted down-right."""
    from PIL import ImageDraw

    ss = 4
    w = size_px * ss
    h = round(size_px * 1.15) * ss
    canvas = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    # Outer teardrop/pear-like snot bubble anchored near top-left
    cx, cy = round(w * 0.56), round(h * 0.56)
    rx, ry = round(w * 0.36), round(h * 0.34)
    draw.polygon(
        [(round(w * 0.14), round(h * 0.14)), (cx - rx // 2, cy), (cx, cy - ry // 2)],
        fill=(165, 226, 255, 200),
        outline=(86, 148, 210, 235),
    )
    draw.ellipse(
        (cx - rx, cy - ry, cx + rx, cy + ry),
        fill=(170, 230, 255, 210),
        outline=(86, 148, 210, 240),
        width=max(2, ss),
    )
    # Soft inner specular shine
    hx0, hy0 = cx - round(rx * 0.52), cy - round(ry * 0.52)
    draw.ellipse(
        (hx0, hy0, hx0 + round(rx * 0.55), hy0 + round(ry * 0.42)),
        fill=(255, 255, 255, 215),
    )
    return canvas.resize((size_px, round(size_px * 1.15)), Image.Resampling.LANCZOS)


def _largest_component(rgba_arr):
    """Return RGBA array keeping only the largest 4-connected opaque component."""
    mask = rgba_arr[:, :, 3] > 24
    h, w = mask.shape
    visited = np.zeros((h, w), dtype=bool)
    best_pixels = []
    for y0 in range(h):
        for x0 in range(w):
            if not mask[y0, x0] or visited[y0, x0]:
                continue
            comp = []
            q = deque([(y0, x0)])
            visited[y0, x0] = True
            while q:
                cy, cx = q.popleft()
                comp.append((cy, cx))
                for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    ny, nx = cy + dy, cx + dx
                    if 0 <= ny < h and 0 <= nx < w and not visited[ny, nx] and mask[ny, nx]:
                        visited[ny, nx] = True
                        q.append((ny, nx))
            if len(comp) > len(best_pixels):
                best_pixels = comp
    out = np.zeros_like(rgba_arr)
    if best_pixels:
        ys, xs = zip(*best_pixels)
        out[ys, xs] = rgba_arr[ys, xs]
    return out


def _blend_rgba(frame_a, frame_b, t):
    """Premultiplied-alpha RGBA blend between two identically sized frames without dark halos."""
    a = np.array(frame_a.convert('RGBA'), dtype=np.float32)
    b = np.array(frame_b.convert('RGBA'), dtype=np.float32)
    aa = a[:, :, 3:4] / 255.0
    ab = b[:, :, 3:4] / 255.0
    out_a = aa * (1.0 - t) + ab * t
    out_premul = a[:, :, :3] * aa * (1.0 - t) + b[:, :, :3] * ab * t
    safe_a = np.maximum(out_a, 1e-6)
    out_rgb = np.where(out_a > 1e-4, out_premul / safe_a, 0.0)
    merged = np.concatenate(
        [np.clip(out_rgb, 0, 255), np.clip(out_a * 255.0, 0, 255)],
        axis=2,
    ).astype(np.uint8)
    return Image.fromarray(merged, 'RGBA')


def _sleep_bubble_cell(f4_cell, scale):
    """Place a scaled translucent cyan sleep bubble at Frame 4's mouth."""
    if scale <= 0:
        return f4_cell.copy()
    out = f4_cell.copy()
    arr = np.array(out)
    ys4, xs4 = np.where(arr[:, :, 3] > 32)
    b_left, b_top = int(xs4.min()), int(ys4.min())
    b_right, b_bottom = int(xs4.max()), int(ys4.max())
    bw = b_right - b_left
    bh = b_bottom - b_top
    bubble = _draw_sleep_bubble(size_px=max(16, round(bh * 0.165 * scale)))
    mouth_x = b_left + round(bw * 0.525)
    mouth_y = b_top + round(bh * 0.452)
    out.alpha_composite(bubble, (mouth_x, mouth_y))
    return out


def fix_sleep_cells(cells, stretch_im):
    """Build clean Sleep Bubble (Frame 5) and Wake Stretch in Bed (Frame 6)."""
    # Frame 5 (row 1, col 0): place crisp translucent cyan sleep bubble at Frame 4's mouth
    f4 = cells[0][3].copy()
    f4_arr = np.array(f4)
    ys4, xs4 = np.where(f4_arr[:, :, 3] > 32)
    b_left, b_top = int(xs4.min()), int(ys4.min())
    b_right, b_bottom = int(xs4.max()), int(ys4.max())
    bw = b_right - b_left
    bh = b_bottom - b_top

    cells[1][0] = _sleep_bubble_cell(f4, 1.0)

    # Frame 6 (row 1, col 1): use Frame 4's frontal bed geometry cleanly behind + in front of stretch.webp
    cw, ch = f4.size
    bed_back = f4_arr.copy()
    center_x = (b_left + b_right) // 2
    rim_y_center = b_top + round(bh * 0.566)

    xs_grid = np.arange(cw)
    dx_norm = np.abs(xs_grid - center_x) / max(1.0, bw * 0.42)
    rim_curve = (rim_y_center + np.round(bh * 0.026 * np.clip(dx_norm, 0, 1.2) ** 2)).astype(np.int32)
    ys_grid = np.arange(ch)[:, None]

    # Carve out sleeping head/ears/hair above the curved blanket rim:
    # Left wooden finial starts cleanly at cx - 0.285*bw; right wooden crest starts cleanly at cx + 0.362*bw.
    carve_l = center_x - round(bw * 0.285)
    carve_r = center_x + round(bw * 0.362)
    carve_mask = (ys_grid < (rim_curve + round(bh * 0.03))[None, :]) & (xs_grid[None, :] >= carve_l) & (xs_grid[None, :] <= carve_r)
    bed_back[carve_mask] = 0
    # Drop any tiny isolated dust from Frame 4's hair halo on bed_back
    bed_back = _largest_component(bed_back)

    # Keep Frame 4's natural curved front blanket starting at rim_y(x) and patch out sleeping paws/chin pixels
    blanket_arr = f4_arr.copy()
    blanket_arr[ys_grid < rim_curve[None, :], 3] = 0

    # Smoothly patch out the two sleeping paws + chin sliver sitting at the top edge of the blanket
    patch_y0 = rim_y_center - 2
    patch_y1 = rim_y_center + max(18, round(bh * 0.095))
    for px_offset in (-0.095, 0.0, 0.095):
        px_c = center_x + round(bw * px_offset)
        px_half = max(12, round(bw * 0.08))
        src_y = min(ch - 1, patch_y1 + 6)
        sample_strip = f4_arr[src_y:src_y + 1, px_c - px_half:px_c + px_half].copy()
        for py in range(patch_y0, patch_y1):
            dst_slice = blanket_arr[py:py + 1, px_c - px_half:px_c + px_half]
            warm_or_dark = (
                (dst_slice[:, :, 3] > 32)
                & (
                    (dst_slice[:, :, 0].astype(np.int16) > dst_slice[:, :, 2].astype(np.int16) - 10)
                    | (dst_slice[:, :, :3].mean(axis=2) < 175)
                )
            )
            dst_slice[warm_or_dark] = sample_strip[warm_or_dark]

    # Prepare stretch sprite cropped cleanly below hips so legs never poke under bed/blanket
    st_rgba = stretch_im.convert('RGBA')
    st_arr = np.array(st_rgba)
    sys_, sxs = np.where(st_arr[:, :, 3] > 32)
    st_crop = st_rgba.crop((int(sxs.min()), int(sys_.min()), int(sxs.max()) + 1, int(sys_.max()) + 1))
    st_upper = st_crop.crop((0, 0, st_crop.width, round(st_crop.height * 0.76)))

    target_st_h = round(bh * 0.86)
    target_st_w = round(st_upper.width * (target_st_h / st_upper.height))
    st_resized = st_upper.resize((target_st_w, target_st_h), Image.Resampling.LANCZOS)

    f6_canvas = Image.fromarray(bed_back, 'RGBA')
    st_x = center_x - target_st_w // 2 + round(bw * 0.015)
    st_y = rim_y_center - target_st_h + round(bh * 0.175)
    f6_canvas.alpha_composite(st_resized, (st_x, max(4, st_y)))
    f6_canvas.alpha_composite(Image.fromarray(blanket_arr, 'RGBA'), (0, 0))

    cells[1][1] = f6_canvas
    return cells


def prepare_frame(image, flip=False, dy=0, scale_x=1.0, scale_y=1.0, rotate_deg=0.0, target_h=TARGET_HEIGHT):
    im = image.convert('RGBA')
    if flip:
        im = ImageOps.mirror(im)
    if rotate_deg:
        im = im.rotate(rotate_deg, resample=Image.Resampling.BICUBIC, expand=True)
    pixels = np.array(im)
    alpha = pixels[:, :, 3]
    pixels[alpha < 16] = 0
    ys, xs = np.where(pixels[:, :, 3] > 32)
    if not len(xs):
        raise ValueError('Empty sprite frame')
    left = max(0, int(xs.min()) - 4)
    top = max(0, int(ys.min()) - 4)
    right = min(im.width, int(xs.max()) + 5)
    bottom = min(im.height, int(ys.max()) + 5)
    crop = Image.fromarray(pixels, 'RGBA').crop((left, top, right, bottom))
    scale = target_h / crop.height
    new_w = max(1, round(crop.width * scale * scale_x))
    new_h = max(1, round(crop.height * scale * scale_y))
    if new_w > SIZE[0] - 16:
        fit = (SIZE[0] - 16) / new_w
        new_w = round(new_w * fit)
        new_h = round(new_h * fit)
    crop = crop.resize((new_w, new_h), Image.Resampling.LANCZOS)
    x = (SIZE[0] - crop.width) // 2
    y = max(4, min(SIZE[1] - crop.height, GROUND - crop.height + dy))
    canvas = Image.new('RGBA', SIZE, (0, 0, 0, 0))
    canvas.alpha_composite(crop, (x, y))
    return canvas


def build_all():
    names = download_all_sources()
    loaded = {}
    for name in names:
        src = SOURCE_DIR / f'{name}.webp'
        if src.exists():
            loaded[name] = Image.open(src).convert('RGBA')

    V2_SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    idle_waving_cells = split_grid_cells(IDLE_WAVING_JPG)
    running_raw = split_grid_cells(RUNNING_JPG)
    run_right_cells = running_raw[0]
    run_left_cells = [ImageOps.mirror(cell) for cell in run_right_cells]
    running_cells = [run_right_cells, run_left_cells]
    sleep_cells = fix_sleep_cells(split_grid_cells(SLEEP_JPG), loaded['stretch'])

    # Save 1774x887 transparent master sheets like white-dragon-pet
    for out_name, grid in (
        ('idle-waving.png', idle_waving_cells),
        ('running.png', running_cells),
        ('sleep.png', sleep_cells),
    ):
        master = Image.new('RGBA', (1774, 887), (0, 0, 0, 0))
        for r_idx, row in enumerate(grid):
            for c_idx, cell in enumerate(row):
                fitted = cell.copy()
                fitted.thumbnail((420, 420), Image.Resampling.LANCZOS)
                cx = round(1774 * c_idx / 4) + (443 - fitted.width) // 2
                cy = r_idx * 443 + (443 - fitted.height) // 2
                master.alpha_composite(fitted, (cx, cy))
        master.save(V2_SOURCE_DIR / out_name)

    # 1. idle (12 frames: smooth progressive blink cycle + gentle breathing)
    i0 = prepare_frame(idle_waving_cells[0][0], dy=0)
    i0_breath = prepare_frame(idle_waving_cells[0][0], dy=0, scale_y=1.008)
    i1 = prepare_frame(idle_waving_cells[0][1], dy=0)
    i2 = prepare_frame(idle_waving_cells[0][2], dy=1)
    i3 = prepare_frame(idle_waving_cells[0][3], dy=-1)
    idle_frames = [
        i0,
        i0_breath,
        _blend_rgba(i0, i1, 0.5),
        i1,
        _blend_rgba(i1, i2, 0.5),
        i2,
        prepare_frame(idle_waving_cells[0][2], dy=1, scale_y=0.994),
        _blend_rgba(i2, i1, 0.5),
        i1,
        _blend_rgba(i1, i3, 0.5),
        i3,
        i0,
    ]

    # 2. waving (8 frames: smooth arm raise -> cheerful double wave -> return)
    w0 = prepare_frame(idle_waving_cells[1][0], dy=0)
    w1 = prepare_frame(idle_waving_cells[1][1], dy=-4)
    w_roll = prepare_frame(loaded['roll_call'], dy=-8)
    w2 = prepare_frame(idle_waving_cells[1][2], dy=-5)
    w3 = prepare_frame(idle_waving_cells[1][3], dy=0)
    waving_frames = [
        w0,
        _blend_rgba(w0, w1, 0.55),
        w1,
        w_roll,
        w2,
        w1,
        _blend_rgba(w1, w3, 0.55),
        w3,
    ]

    # 3 & 4. running-right & running-left (16 frames: 8-step parabolic stride micro-cycle x2)
    stride_phases = [
        (0, 0, 1.02, 0.98, 0.0),
        (0, -3, 1.00, 1.00, 1.5),
        (1, -5, 0.99, 1.01, 0.5),
        (1, -10, 0.98, 1.02, -1.5),
        (2, -19, 1.00, 1.01, -2.5),
        (2, -14, 1.01, 0.99, -0.5),
        (3, -4, 1.01, 0.99, 1.2),
        (3, 0, 1.02, 0.98, 0.0),
    ]
    running_right_frames = [
        prepare_frame(run_right_cells[idx], dy=dy, scale_x=sx, scale_y=sy, rotate_deg=rot)
        for _cycle in range(2)
        for idx, dy, sx, sy, rot in stride_phases
    ]
    running_left_frames = [
        prepare_frame(run_left_cells[idx], dy=dy, scale_x=sx, scale_y=sy, rotate_deg=-rot)
        for _cycle in range(2)
        for idx, dy, sx, sy, rot in stride_phases
    ]

    # 5. jumping (10 frames: crouch -> push-off -> ascent -> apex float -> descent -> cushion -> recover)
    jump_frames = [
        prepare_frame(loaded['idle'], dy=4, scale_x=1.04, scale_y=0.95),
        prepare_frame(loaded['happy'], dy=-6, scale_x=0.98, scale_y=1.02),
        prepare_frame(loaded['happy'], dy=-18, scale_x=0.99, scale_y=1.01),
        prepare_frame(loaded['float'], dy=-30, scale_x=1.0, scale_y=1.0, rotate_deg=-1.0),
        prepare_frame(loaded['float'], dy=-42, scale_x=1.0, scale_y=1.0, rotate_deg=-2.0),
        prepare_frame(loaded['float'], dy=-40, scale_x=1.0, scale_y=1.0, rotate_deg=1.5),
        prepare_frame(loaded['proud'], dy=-26, scale_x=1.0, scale_y=1.0),
        prepare_frame(loaded['proud'], dy=-12, scale_x=1.01, scale_y=0.99),
        prepare_frame(loaded['idle'], dy=4, scale_x=1.04, scale_y=0.95),
        prepare_frame(loaded['idle'], dy=0, scale_x=1.01, scale_y=0.99),
    ]

    # 6. failed (16 frames: oops -> surprised -> tired -> puffed -> annoyed -> sulk -> recover)
    failed_frames = [
        prepare_frame(loaded['oops'], dy=0),
        prepare_frame(loaded['oops'], dy=-3, scale_y=1.01),
        prepare_frame(loaded['surprised'], dy=-2),
        prepare_frame(loaded['surprised'], dy=0, scale_x=1.01, scale_y=0.99),
        prepare_frame(loaded['tired'], dy=0),
        prepare_frame(loaded['tired'], dy=2, scale_y=0.99),
        prepare_frame(loaded['puffed'], dy=0),
        prepare_frame(loaded['puffed'], dy=-2, scale_x=1.02, scale_y=0.98),
        prepare_frame(loaded['annoyed'], dy=0),
        prepare_frame(loaded['annoyed'], dy=-1, rotate_deg=-1.5),
        prepare_frame(loaded['annoyed'], dy=0, rotate_deg=1.5),
        prepare_frame(loaded['sulk'], dy=0, target_h=570),
        prepare_frame(loaded['sulk'], dy=2, target_h=560),
        prepare_frame(loaded['sulk'], dy=3, target_h=555, scale_x=1.02, scale_y=0.98),
        prepare_frame(loaded['sulk'], dy=1, target_h=565),
        prepare_frame(loaded['tired'], dy=0),
    ]

    # 7. waiting (12 frames: listening -> idle-2 -> asking -> hum -> idle-3 -> listening)
    waiting_frames = [
        prepare_frame(loaded['listening'], dy=0),
        prepare_frame(loaded['listening'], dy=-2, scale_y=1.01),
        prepare_frame(loaded['idle-2'], dy=0),
        prepare_frame(loaded['idle-2'], dy=-2, scale_y=1.01),
        prepare_frame(loaded['asking'], dy=0),
        prepare_frame(loaded['asking'], dy=-2, rotate_deg=1.0),
        prepare_frame(loaded['hum'], dy=0),
        prepare_frame(loaded['hum'], dy=-2, rotate_deg=-1.0),
        prepare_frame(loaded['idle-3'], dy=0),
        prepare_frame(loaded['idle-3'], dy=-2),
        prepare_frame(loaded['listening'], dy=-1),
        prepare_frame(loaded['listening'], dy=0),
    ]

    # 8. running / working (12 frames: writing -> drawing -> reading -> searching -> delegating -> reading)
    working_frames = [
        prepare_frame(loaded['writing'], dy=0),
        prepare_frame(loaded['writing'], dy=-2, rotate_deg=-1.0),
        prepare_frame(loaded['drawing'], dy=0),
        prepare_frame(loaded['drawing'], dy=-2, rotate_deg=1.0),
        prepare_frame(loaded['reading'], dy=0),
        prepare_frame(loaded['reading'], dy=-2, scale_y=1.01),
        prepare_frame(loaded['searching'], dy=0),
        prepare_frame(loaded['searching'], dy=-2, rotate_deg=-1.0),
        prepare_frame(loaded['delegating'], dy=0),
        prepare_frame(loaded['delegating'], dy=-2, rotate_deg=1.0),
        prepare_frame(loaded['writing'], dy=0),
        prepare_frame(loaded['reading'], dy=0),
    ]

    # 9. review / thinking (12 frames: thinking -> reading -> searching -> asking -> thinking)
    review_frames = [
        prepare_frame(loaded['thinking'], dy=0),
        prepare_frame(loaded['thinking'], dy=-2, rotate_deg=-1.0),
        prepare_frame(loaded['thinking'], dy=0, scale_y=1.01),
        prepare_frame(loaded['reading'], dy=0),
        prepare_frame(loaded['reading'], dy=-2, rotate_deg=1.0),
        prepare_frame(loaded['reading'], dy=0),
        prepare_frame(loaded['searching'], dy=0),
        prepare_frame(loaded['searching'], dy=-2),
        prepare_frame(loaded['asking'], dy=0),
        prepare_frame(loaded['asking'], dy=-1, rotate_deg=1.0),
        prepare_frame(loaded['thinking'], dy=-2),
        prepare_frame(loaded['thinking'], dy=0),
    ]

    # 10. sleep (16 frames: 0..5 entry -> 6..9 breathing/bubble loop -> 10..15 wake stretch & stand)
    f4_clean = sleep_cells[0][3]
    sleep_frames = [
        prepare_frame(sleep_cells[0][0], dy=0, target_h=650),
        prepare_frame(loaded['yawn'], dy=-2, target_h=640),
        prepare_frame(loaded['tired'], dy=0, target_h=640),
        prepare_frame(sleep_cells[0][1], dy=0, target_h=610),
        prepare_frame(sleep_cells[0][2], dy=4, target_h=545),
        prepare_frame(sleep_cells[0][2], dy=0, target_h=540),
        prepare_frame(f4_clean, dy=0, target_h=540),
        prepare_frame(_sleep_bubble_cell(f4_clean, 0.58), dy=1, scale_y=0.992, target_h=540),
        prepare_frame(_sleep_bubble_cell(f4_clean, 1.00), dy=0, target_h=540),
        prepare_frame(_sleep_bubble_cell(f4_clean, 1.16), dy=1, scale_y=0.992, target_h=540),
        prepare_frame(f4_clean, dy=-1, target_h=540),
        prepare_frame(sleep_cells[1][1], dy=2, target_h=540),
        prepare_frame(sleep_cells[1][1], dy=-2, scale_y=1.01, target_h=544),
        prepare_frame(sleep_cells[1][2], dy=0, target_h=610),
        prepare_frame(loaded['happy'], dy=-5, target_h=650),
        prepare_frame(sleep_cells[1][3], dy=0, target_h=650),
    ]

    all_states = {
        'idle': idle_frames,
        'waving': waving_frames,
        'running-right': running_right_frames,
        'running-left': running_left_frames,
        'jumping': jump_frames,
        'failed': failed_frames,
        'waiting': waiting_frames,
        'running': working_frames,
        'review': review_frames,
        'sleep': sleep_frames,
    }

    for out_root in (V2_OUT_DIR, ROOT / 'assets/transparent'):
        for state, frames in all_states.items():
            dest = out_root / state
            dest.mkdir(parents=True, exist_ok=True)
            for old in dest.glob('*.png'):
                old.unlink()
            for idx, frame in enumerate(frames):
                frame.save(dest / f'{idx:02d}.png')
    for state, frames in all_states.items():
        print(f'{state}: {len(frames)} frames')
    print(f'Total source sprites in assets/source: {len(loaded)}')


if __name__ == '__main__':
    build_all()
