"""Animation schedule and screen-edge roaming logic."""

ANIMATIONS = {
    'idle': (12, '待机'),
    'running-right': (16, '向右跑'),
    'running-left': (16, '向左跑'),
    'waving': (8, '打招呼'),
    'jumping': (10, '跳跃'),
    'failed': (16, '委屈表情'),
    'waiting': (12, '等待'),
    'running': (12, '工作'),
    'review': (12, '思考'),
}


def roam_x(x, width, left, right, direction, step=2):
    limit = max(left, right - width)
    if (x < left and direction < 0) or (x > limit and direction > 0):
        return x
    target = x + direction * step
    return max(left, min(limit, target)) if left <= x <= limit else target


class AnimationSchedule:
    def __init__(self):
        self.override = None

    def play(self, name, now, delay=0, duration=4):
        if name not in ANIMATIONS:
            raise ValueError(f'Unknown animation: {name}')
        self.override = (name, now + delay, now + delay + duration)

    def current(self, now, working):
        if self.override:
            name, start, end = self.override
            if start <= now < end:
                return name
            if now >= end:
                self.override = None
        choices = ('running', 'waiting', 'review') if working else tuple(ANIMATIONS)
        return choices[int(now // 16) % len(choices)]
