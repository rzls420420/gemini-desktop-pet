"""PyQt5 transparent desktop pet window for Antigravity Gemini Catgirl."""
import sys
import time
from pathlib import Path

from PyQt5.QtCore import QRect, Qt, QThread, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QFontMetrics, QPainter, QPixmap
from PyQt5.QtWidgets import QApplication, QMenu, QMessageBox, QWidget

from catgirl_pet import autostart
from catgirl_pet.animation import ANIMATIONS, AnimationSchedule, roam_x
from catgirl_pet.dialogue import (
    format_context_usage,
    pick_line,
    read_antigravity_quota,
    read_antigravity_status,
)
from catgirl_pet.speech import SpeechQueue
from catgirl_pet.state import PetState
from catgirl_pet.task_activity import ActivityTracker


def resource_root():
    return Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent.parent))


class StatusWorker(QThread):
    result = pyqtSignal(str)

    def run(self):
        try:
            self.result.emit(read_antigravity_status())
        except OSError:
            self.result.emit('Antigravity 状态暂时查不到喵，主人稍后再试。')


class QuotaWorker(QThread):
    result = pyqtSignal(str)

    def run(self):
        try:
            self.result.emit(read_antigravity_quota())
        except OSError:
            self.result.emit('额度信息暂时读取不到喵，主人稍后再试。')


def load_transparent_frames(state, count):
    v2_root = resource_root() / 'assets/transparent-v2' / state
    v1_root = resource_root() / 'assets/transparent' / state
    root = v2_root if v2_root.is_dir() else v1_root
    frames = [QPixmap(str(root / f'{index:02d}.png')) for index in range(count)]
    if any(frame.isNull() for frame in frames):
        raise RuntimeError(f'找不到 Gemini 猫娘透明动作素材：{state}')
    return frames


class PetWindow(QWidget):
    def __init__(self):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setWindowTitle('哈基米喵桌面宠物')
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(300, 380)
        self.origin = time.monotonic()
        self.state = PetState()
        self.animations = AnimationSchedule()
        self.activity = ActivityTracker()
        self.sleep_images = load_transparent_frames('sleep', 16)
        self.images = {}
        for name, (count, _) in ANIMATIONS.items():
            self.images[name] = load_transparent_frames(name, count)
        self.animations.play('waving', 0, duration=4)
        self.current_animation = None
        self.next_auto_speech = 45
        self.next_context_speech = 20
        self.speech = SpeechQueue()
        self.talk(pick_line('startup'))
        self.drag = None
        self.status_worker = None
        self.quota_worker = None
        geometry = QApplication.primaryScreen().availableGeometry()
        self.move(geometry.right() - self.width() - 30, geometry.bottom() - self.height() - 30)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(60)
        self.activity_timer = QTimer(self)
        self.activity_timer.timeout.connect(self.check_activity)
        self.check_activity()
        self.activity_timer.start(2000)

    def now(self):
        return time.monotonic() - self.origin

    def refresh(self):
        previous = self.state.mode
        self.state.tick(self.now())
        if previous == 'idle' and self.state.mode == 'sleeping':
            self.talk(pick_line('sleep'))
        if self.state.mode == 'idle':
            name = self.animations.current(self.now(), self.state.working)
            if (not self.state.working and name != self.current_animation and name != 'idle'
                    and self.now() >= self.next_auto_speech):
                category = f'ambient-{name}' if name in ('running', 'waiting', 'review') else name
                self.talk(pick_line(category), priority=0)
                self.next_auto_speech = self.now() + 60
            self.current_animation = name
            if not self.state.working and self.drag is None and name in ('running-left', 'running-right'):
                screen = QApplication.screenAt(self.frameGeometry().center()) or QApplication.primaryScreen()
                area = screen.availableGeometry()
                direction = 1 if name == 'running-right' else -1
                x = roam_x(self.x(), self.width(), area.left(), area.right() + 1, direction, step=1)
                self.move(x, self.y())
        else:
            self.current_animation = None
        speech = self.speech.current(self.now())
        bubble, _ = self.speech_rectangles(speech)
        height = 380 + max(0, bubble.height() - 66)
        if height != self.height():
            bottom = self.y() + self.height()
            self.resize(self.width(), height)
            self.move(self.x(), bottom - height)
        self.update()

    def speech_text_height(self, text):
        if not text:
            return 0
        metrics = QFontMetrics(QFont('Sans Serif', 11))
        return metrics.boundingRect(
            QRect(0, 0, 256, 100000),
            Qt.TextWordWrap | Qt.TextWrapAnywhere,
            text,
        ).height()

    def speech_rectangles(self, text):
        text_height = self.speech_text_height(text)
        height = 66 if text_height <= 54 else text_height + 28
        if text and any(key in text for key in ('缓存命中', '配额快照', '实时消耗', '最新节点', '主进程')):
            height = max(height, text_height + 28, 82)
        return QRect(12, 8, 276, height), QRect(22, 14, 256, height - 12)

    def play_animation(self, name, duration=4):
        now = self.now()
        delay = max(0, self.state.started + 3 - now) if self.state.mode == 'waking' else 0
        self.animations.play(name, now, delay=delay, duration=duration)

    def talk(self, text, priority=1, delay=0):
        self.speech.add(text, self.now(), priority=priority, delay=delay)

    def check_activity(self):
        working, completed, aborted, missing = self.activity.poll()
        was_working = self.state.working
        self.state.set_working(working, self.now())
        if working and not was_working:
            self.play_animation('running-right')
            self.talk(pick_line('task-start'), priority=2)
        if completed:
            self.play_animation('jumping')
            self.talk(pick_line('task-complete'), priority=2)
        if aborted:
            self.play_animation('failed')
            self.talk(pick_line('task-aborted'), priority=2)
        if missing:
            self.talk(pick_line('task-unknown'), priority=2)
        if working and self.now() >= self.next_context_speech:
            usage = self.activity.context_usage()
            if usage is not None:
                self.talk(format_context_usage(usage), priority=0)
            self.next_context_speech = self.now() + 60

    def paintEvent(self, event):
        now = self.now()
        p = QPainter(self)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        speech = self.speech.current(now)
        if speech:
            bubble, text_rect = self.speech_rectangles(speech)
            p.setBrush(QColor(255, 255, 255, 240))
            p.setPen(QColor('#7b5cd6'))
            p.drawRoundedRect(bubble, 9, 9)
            p.setFont(QFont('Sans Serif', 11))
            p.setPen(QColor('#2b2140'))
            p.drawText(text_rect, Qt.AlignCenter | Qt.TextWordWrap | Qt.TextWrapAnywhere, speech)
        if self.state.mode == 'idle':
            name = self.animations.current(now, self.state.working)
            images = self.images[name]
            fps_map = {
                'running-left': 8,
                'running-right': 8,
                'jumping': 7,
                'waving': 6,
                'idle': 4,
                'failed': 3.5,
            }
            fps = fps_map.get(name, 2.5)
            image = images[int(now * fps) % len(images)]
        else:
            image = self.sleep_images[self.state.frame(now)]
        target = image.size().scaled(286, 296, Qt.KeepAspectRatio)
        p.drawPixmap(
            (self.width() - target.width()) // 2,
            self.height() - target.height(),
            target.width(),
            target.height(),
            image,
        )

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag = event.globalPos() - self.frameGeometry().topLeft()
            was_sleeping = self.state.mode == 'sleeping'
            self.state.wake(self.now())
            self.play_animation('waving')
            self.talk(pick_line('wake' if was_sleeping else 'interaction'), delay=3 if was_sleeping else 0)

    def mouseMoveEvent(self, event):
        if self.drag is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPos() - self.drag)

    def mouseReleaseEvent(self, event):
        self.drag = None

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        sleep = menu.addAction('立即睡觉')
        wake = menu.addAction('叫醒')
        quota_action = menu.addAction('查询额度')
        context = menu.addAction('查看上下文状态')
        status_action = menu.addAction('查看 Antigravity 状态')
        startup = menu.addAction('开机启动')
        startup.setCheckable(True)
        try:
            startup.setChecked(autostart.is_enabled())
        except OSError as error:
            startup.setEnabled(False)
            startup.setToolTip(str(error))
        preview = menu.addMenu('预览动作')
        previews = {preview.addAction(label): name for name, (_, label) in ANIMATIONS.items()}
        menu.addSeparator()
        quit_action = menu.addAction('退出')
        chosen = menu.exec_(event.globalPos())
        if chosen == sleep:
            if self.state.working:
                self.talk('本喵喵正在处理任务，暂时不能睡喵。')
            else:
                self.state.sleep(self.now())
                self.talk(pick_line('sleep'))
        elif chosen == wake:
            was_sleeping = self.state.mode == 'sleeping'
            self.state.wake(self.now())
            self.talk(pick_line('wake'), delay=3 if was_sleeping else 0)
        elif chosen == quota_action:
            if self.quota_worker is None or not self.quota_worker.isRunning():
                self.talk('本喵喵正在查看额度与近期用量……')
                self.quota_worker = QuotaWorker(self)
                self.quota_worker.result.connect(lambda text: self.talk(text, priority=2))
                self.quota_worker.start()
        elif chosen == status_action:
            if self.status_worker is None or not self.status_worker.isRunning():
                self.talk('本喵喵正在检查 Antigravity 状态……')
                self.status_worker = StatusWorker(self)
                self.status_worker.result.connect(lambda text: self.talk(text, priority=2))
                self.status_worker.start()
        elif chosen == context:
            usage, recent = self.activity.context_snapshot()
            self.talk(format_context_usage(usage, recent=recent), priority=2)
        elif chosen == startup:
            try:
                autostart.set_enabled(startup.isChecked())
                self.talk('本喵喵已设置开机启动✦' if startup.isChecked() else '本喵喵已关闭开机启动。')
            except OSError as error:
                QMessageBox.warning(self, '开机启动设置失败', str(error))
        elif chosen in previews:
            self.state.wake(self.now())
            name = previews[chosen]
            self.play_animation(name)
            self.talk(pick_line(name))
        elif chosen == quit_action:
            QApplication.quit()


def main():
    app = QApplication(sys.argv)
    window = PetWindow()
    window.show()
    return app.exec_()


if __name__ == '__main__':
    sys.exit(main())
