"""State machine for idle, sleeping, waking, and working modes."""


class PetState:
    def __init__(self, idle_seconds=300):
        self.idle_seconds = idle_seconds
        self.mode = 'idle'
        self.last_interaction = 0
        self.started = 0
        self.working = False

    def tick(self, now):
        if self.mode == 'idle' and not self.working and now - self.last_interaction >= self.idle_seconds:
            self.sleep(now)
        elif self.mode == 'waking' and now - self.started >= 3:
            self.mode = 'idle'
            self.last_interaction = now

    def sleep(self, now):
        if self.working:
            return
        self.mode = 'sleeping'
        self.started = now

    def set_working(self, working, now):
        if self.working and not working:
            self.last_interaction = now
        self.working = working
        if working and self.mode == 'sleeping':
            self.wake(now)

    def wake(self, now):
        if self.mode == 'sleeping':
            self.mode = 'waking'
            self.started = now
        elif self.mode == 'idle':
            self.last_interaction = now

    def frame(self, now):
        elapsed = max(0, now - self.started)
        if self.mode == 'waking':
            return min(15, 10 + int(elapsed * 2))
        if elapsed < 3:
            return min(5, int(elapsed * 2))
        return 6 + int((elapsed - 3) / 0.65) % 4
