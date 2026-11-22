"""Priority speech bubble queue."""


class SpeechQueue:
    def __init__(self):
        self.active = None
        self.until = 0
        self.pending = []
        self.serial = 0

    def add(self, text, now, priority=1, delay=0, duration=5):
        self.current(now)
        if priority == 0 and (self.active or self.pending):
            return
        if self.active and priority > self.active[1]:
            self.active = None
        if priority > 0:
            self.pending = [entry for entry in self.pending if entry[1] > 0]
        self.serial += 1
        self.pending.append((text, priority, now + delay, duration, self.serial))
        self.current(now)

    def current(self, now):
        if self.active and now >= self.until:
            self.active = None
        if not self.active:
            ready = [entry for entry in self.pending if entry[2] <= now]
            if ready:
                chosen = min(ready, key=lambda entry: (-entry[1], entry[4]))
                self.pending.remove(chosen)
                self.active = chosen
                self.until = now + chosen[3]
        return self.active[0] if self.active else None
