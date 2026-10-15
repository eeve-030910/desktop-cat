"""Windows 11 desktop sparrow. Coordinates use Qt logical screen units."""
import ctypes
from ctypes import wintypes as W
import math
from pathlib import Path
import random
import sys
import time
import json

from PySide6.QtCore import Qt, QTimer, QPoint, QSettings, QStandardPaths, QUrl
from PySide6.QtGui import QPixmap, QPainter, QIcon, QTransform, QDesktopServices, QPainterPath, QColor
from PySide6.QtWidgets import QApplication, QWidget, QSystemTrayIcon, QMenu, QMainWindow, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QCheckBox, QMessageBox, QComboBox, QScrollArea

from online_content import APP_VERSION, fetch, catalog_entries, install_character
from update_ui import Task, UpdateMonitor
from build_channel import BUILD_CHANNEL
ROOT = Path(__file__).resolve().parent
BUILTINS = [
    {"id":"tabby_cat", "name":"茶トラねこ", "path":str(ROOT / "assets"), "kind":"cat"},
    {"id":"shiba_dog", "name":"柴犬", "path":str(ROOT / "assets" / "dog"), "kind":"dog"},
    {"id":"sparrow", "name":"スズメ", "path":str(ROOT / "assets" / "sparrow"), "kind":"sparrow"},
]


class DesktopCat(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.policy_allowed = True
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint |
                            Qt.Tool | Qt.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.resize(128, 144)
        self.frames = {"walk": []}
        for i in range(4):
            pix = QPixmap(str(ROOT / "assets" / f"cat_{i}.png"))
            if pix.isNull():
                raise RuntimeError(f"Missing sprite: cat_{i}.png")
            self.frames["walk"].append(pix)
        self.sleep_pix = QPixmap(str(ROOT / "assets" / "cat_sleep.png"))
        if self.sleep_pix.isNull():
            raise RuntimeError("Missing sprite: cat_sleep.png")
        self.sparrow_hop = None
        self.sparrow_hops_left = 3
        self.hop_offset = 0.0
        self.flap_until = 0.0
        self.next_flap = time.monotonic()+random.uniform(20, 45)
        self.flap_frames = []
        self.character_kind = "cat"
        self.sleeping = False
        self.sleep_until = 0.0
        self.next_sleep = time.monotonic() + random.uniform(90, 180)
        self.heart_start = 0.0
        self.heart_until = 0.0
        self.direction = 1
        self.paused = False
        self.walking = True
        self.phase = 0.0
        self.rest_until = 0.0
        self.px = self.ground()[0] + 60
        self.last = time.monotonic()
        self.place_on_bottom()
        self.tray = QSystemTrayIcon(QIcon(self.frames["walk"][0]), self)
        self.menu = QMenu()
        self.menu.addAction("キャラクターを選ぶ", self.open_selector)
        self.pause_action = self.menu.addAction("一時停止")
        self.pause_action.setCheckable(True)
        self.pause_action.toggled.connect(self.set_paused)
        self.menu.addAction("ごはんをあげる", self.feed)
        self.menu.addAction("眠る / 起きる", self.toggle_sleep)
        self.menu.addAction("向きを変える", self.turn)
        self.menu.addSeparator()
        self.menu.addAction("終了", app.quit)
        self.tray.setContextMenu(self.menu)
        self.tray.setToolTip("デスクトップねこ")
        self.tray.activated.connect(self.tray_clicked)
        self.tray.show()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(33)
        self.show()

    def ground(self):
        g = QApplication.primaryScreen().availableGeometry()
        return g.left(), max(g.left(), g.right()+1-self.width()), g.bottom()+1-self.height()

    def place_on_bottom(self):
        left, right, y = self.ground()
        self.px = min(max(self.px, left), right)
        self.move(round(self.px), y-round(self.hop_offset))

    def set_paused(self, value):
        self.paused = value
        self.last = time.monotonic()
        self.update()

    def turn(self):
        self.direction *= -1
        self.update()

    def open_selector(self):
        self.app.selector.present()

    def contextMenuEvent(self, event):
        self.menu.exec(event.globalPos())

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.open_selector()

    def tray_clicked(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.open_selector()

    def fall_asleep(self, now=None):
        if not self.policy_allowed:
            return
        now = time.monotonic() if now is None else now
        self.sleeping = True
        self.sparrow_hop = None
        self.sparrow_hops_left = 3
        self.hop_offset = 0.0
        self.flap_until = 0.0
        self.heart_until = now
        self.place_on_bottom()
        self.walking = False
        self.sleep_until = now + random.uniform(120, 240)
        self.update()

    def wake_up(self, now=None):
        now = time.monotonic() if now is None else now
        self.sleeping = False
        self.next_sleep = now + random.uniform(90, 180)
        self.rest_until = now + .5
        self.update()

    def toggle_sleep(self):
        if self.sleeping:
            self.wake_up()
        else:
            self.fall_asleep()

    def feed(self):
        if not self.policy_allowed:
            return
        now = time.monotonic()
        self.show()
        self.pause_action.setChecked(False)
        self.set_paused(False)
        if self.sleeping:
            self.wake_up(now)
        self.sparrow_hop = None
        self.hop_offset = 0.0
        self.sparrow_hops_left = 3
        self.flap_until = 0.0
        self.heart_start = now
        self.heart_until = now + 3.0
        self.rest_until = now + 3.0
        self.walking = False
        self.next_sleep = now + random.uniform(90, 180)
        self.place_on_bottom()
        self.update()

    def tick(self):
        now = time.monotonic()
        elapsed = max(0.0, now-self.last)
        dt = min(elapsed, .08)
        self.last = now
        if self.paused or not self.policy_allowed:
            self.rest_until += elapsed
            self.next_sleep += elapsed
            self.sleep_until += elapsed
            self.next_flap += elapsed
            self.flap_until += elapsed
            if self.sparrow_hop:
                start, x, end = self.sparrow_hop
                self.sparrow_hop = (start+elapsed, x, end)
            if self.heart_until > self.heart_start:
                self.heart_start += elapsed
                self.heart_until += elapsed
            return
        if self.sleeping:
            if now >= self.sleep_until:
                self.wake_up(now)
        elif now >= self.next_sleep:
            self.fall_asleep(now)
        self.walking = not self.sleeping and now >= self.rest_until
        if self.character_kind == "sparrow" and not self.sleeping:
            self.tick_sparrow(now)
        elif self.walking:
            left, right, y = self.ground()
            self.px += self.direction*52*dt
            if self.px >= right:
                self.px = right
                self.direction = -1
            elif self.px <= left:
                self.px = left
                self.direction = 1
            self.phase += dt
            if random.random() < dt*.12:
                self.rest_until = now+random.uniform(1, 3)
                self.walking = False
        self.place_on_bottom()
        self.update()

    def tick_sparrow(self, now):
        self.hop_offset = 0.0
        if now >= self.next_flap and now >= self.heart_until:
            self.flap_until = now+.8
            self.next_flap = now+random.uniform(20,45)
            self.sparrow_hop = None
            self.sparrow_hops_left = 3
            self.rest_until = max(self.rest_until, self.flap_until)
        if now < self.flap_until or now < self.heart_until:
            self.walking = False
            return
        if self.sparrow_hop:
            start, x, end = self.sparrow_hop
            t = min(1.0, max(0.0, (now-start)/.18))
            self.px = x+(end-x)*t
            self.hop_offset = 6*math.sin(math.pi*t)
            self.walking = True
            if t >= 1:
                self.sparrow_hop = None
                self.hop_offset = 0.0
                self.sparrow_hops_left -= 1
                if self.sparrow_hops_left == 0:
                    self.sparrow_hops_left = 3
                    self.rest_until = now+2.0
                else:
                    self.rest_until = now+.04
                self.walking = False
        elif now >= self.rest_until:
            left, right, y = self.ground()
            if self.px+self.direction*14 > right:
                self.direction = -1
            elif self.px+self.direction*14 < left:
                self.direction = 1
            end = min(max(self.px+self.direction*14,left),right)
            self.sparrow_hop = (now,self.px,end)
            self.walking = True
        else:
            self.walking = False

    def load_character(self, directory, kind="cat"):
        directory = Path(directory)
        walking = [QPixmap(str(directory / f"cat_{i}.png")) for i in range(4)]
        sleeping = QPixmap(str(directory / "cat_sleep.png"))
        if any(p.isNull() or p.width()!=128 or p.height()!=96 for p in walking+[sleeping]):
            raise ValueError("キャラ素材が不正です")
        self.character_kind = kind if kind in ("cat", "dog", "sparrow") else "cat"
        flaps = []
        if kind == "sparrow":
            flaps = [QPixmap(str(directory / f"flap_{i}.png")) for i in range(3)]
            if any(p.isNull() for p in flaps):
                flaps = []
        self.flap_frames = flaps
        self.sparrow_hop = None
        self.sparrow_hops_left = 3
        self.hop_offset = 0.0
        self.flap_until = 0.0
        self.next_flap = time.monotonic()+random.uniform(20,45)
        self.frames["walk"] = walking
        self.sleep_pix = sleeping
        self.update()

    def paintEvent(self, event):
        now = time.monotonic()
        frame = int(self.phase*8)%4 if self.walking and not self.paused else 0
        pix = self.sleep_pix if self.sleeping else self.frames["walk"][frame]
        if self.character_kind == "sparrow" and not self.sleeping:
            if now < self.flap_until and self.flap_frames:
                pix = self.flap_frames[int(now*12)%len(self.flap_frames)]
            else:
                pix = self.frames["walk"][0]
        if self.direction < 0:
            pix = pix.transformed(QTransform().scale(-1, 1))
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, False)
        if self.character_kind == "sparrow":
            # Keep the same upright feet in every pose, including wing flaps.
            feet = self.frames["walk"][0]
            if self.direction < 0:
                feet = feet.transformed(QTransform().scale(-1, 1))
            painter.drawPixmap(0, 48, 128, 78, pix, 0, 0, 128, 78)
            painter.drawPixmap(0, 126, 128, 18, feet, 0, 78, 128, 18)
        else:
            painter.drawPixmap(0, 48, 128, 96, pix)
        if self.sleeping and self.character_kind == "sparrow":
            painter.setPen(QColor("#83a5cf"))
            font = painter.font()
            font.setPixelSize(19)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(73, 38, "zzz")
        if self.heart_start <= now < self.heart_until:
            age = now-self.heart_start
            for i in range(3):
                progress = (age-i*.32)/2.2
                if not 0 <= progress <= 1:
                    continue
                painter.save()
                painter.setRenderHint(QPainter.Antialiasing, True)
                painter.setOpacity(min(1, (1-progress)*2))
                painter.translate(30+i*27, 62-40*progress)
                painter.scale(.65+i*.08, .65+i*.08)
                heart = QPainterPath()
                heart.moveTo(0, 5)
                heart.cubicTo(-18, -7, -13, -22, 0, -12)
                heart.cubicTo(13, -22, 18, -7, 0, 5)
                painter.setPen(Qt.NoPen)
                painter.setBrush(QColor("#f2769c"))
                painter.drawPath(heart)
                painter.restore()


class CharacterWindow(QMainWindow):
    """Character choices are persisted; paid entitlements are not simulated."""
    def __init__(self, pet, settings):
        super().__init__()
        self.pet = pet
        self.settings = settings
        self.setWindowTitle(f"デスクトップねこ v{APP_VERSION} — " + ("開発版・更新確認なし" if BUILD_CHANNEL == "development" else "一般配布版"))
        self.setWindowFlags(Qt.Window | Qt.WindowMinimizeButtonHint | Qt.WindowCloseButtonHint)
        self.setWindowIcon(QIcon(pet.frames["walk"][0]))
        self.resize(760, 640)
        self.setMinimumSize(620, 520)
        self.setStyleSheet("""
          QMainWindow, QWidget#page {background:#f8f5ed;color:#30392d;}
          QLabel {color:#30392d; background:transparent;}
          QLabel#subtitle {color:#697061;}
          QFrame#card {background:#fffdf8;border:2px solid #526c48;border-radius:12px;}
          QFrame#locked {background:#efeee6;border:1px solid #dadccc;border-radius:9px;}
          QPushButton {background:#41573b;color:white;border:0;border-radius:6px;padding:12px 20px;}
          QPushButton:hover {background:#2e4428;}
          QPushButton#secondary {background:#e5e8dd;color:#41573b;}
          QPushButton:disabled {background:#dadfd2;color:#78816d;}
          QCheckBox {color:#56614e;spacing:8px;}
        """)
        page = QWidget(); page.setObjectName("page")
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(page)
        self.setCentralWidget(scroll)
        layout = QVBoxLayout(page); layout.setContentsMargins(30,24,30,24); layout.setSpacing(14)
        title = QLabel("今日の相棒を、えらぼう。")
        title.setStyleSheet("font-size:25px;font-weight:600;")
        layout.addWidget(title)
        sub = QLabel("選んだキャラクターが、デスクトップ下部を左右に歩きます。")
        sub.setObjectName("subtitle"); sub.setWordWrap(True); layout.addWidget(sub)
        card = QFrame(); card.setObjectName("card")
        row = QHBoxLayout(card); row.setContentsMargins(18,14,18,14)
        image = QLabel(); self.character_image = image; image.setPixmap(pet.frames["walk"][0].scaled(128,96,Qt.KeepAspectRatio,Qt.FastTransformation))
        row.addWidget(image)
        words = QVBoxLayout(); self.character_title = QLabel("茶トラねこ  ·  無料"); words.addWidget(self.character_title)
        text = QLabel("足を動かして、とことこ。\n画面下部を歩き、眠り、ごはんで喜ぶ相棒。")
        text.setObjectName("subtitle"); words.addWidget(text); row.addLayout(words,1)
        self.choose = QPushButton("標準ネコを選ぶ"); self.choose.clicked.connect(self.select_sparrow); row.addWidget(self.choose)
        layout.addWidget(card)
        self.character_root = Path(QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation)) / "characters"
        online_row = QHBoxLayout()
        self.character_picker = QComboBox()
        online_row.addWidget(self.character_picker, 1)
        self.apply_button = QPushButton("このキャラを表示")
        self.apply_button.clicked.connect(self.apply_character)
        online_row.addWidget(self.apply_button)
        layout.addLayout(online_row)
        network_row = QHBoxLayout()
        self.catalog_button = QPushButton("追加キャラを確認")
        self.catalog_button.clicked.connect(self.refresh_catalog)
        network_row.addWidget(self.catalog_button)
        self.install_button = QPushButton("選択したキャラをダウンロード")
        self.install_button.clicked.connect(self.download_character)
        network_row.addWidget(self.install_button)
        update = QPushButton("更新を確認")
        update.clicked.connect(lambda: self.pet.app.updates.check())
        network_row.addWidget(update)
        layout.addLayout(network_row)
        self.content_status = QLabel("追加キャラはオンラインで確認できます。")
        self.content_status.setWordWrap(True)
        layout.addWidget(self.content_status)
        support = QHBoxLayout()
        support_label = QLabel("開発を応援する（任意）")
        support.addWidget(support_label)
        self.donate_button = QPushButton("Donate / 寄付する")
        try:
            config = json.loads((ROOT / "update_config.json").read_text(encoding="utf-8"))
            self.donate_url = config.get("donate_url", "")
            from urllib.parse import urlsplit
            parsed = urlsplit(self.donate_url)
            if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
                self.donate_url = ""
        except Exception:
            self.donate_url = ""
        self.donate_button.setEnabled(bool(self.donate_url))
        if not self.donate_url:
            self.donate_button.setText("Donate / 寄付先は準備中")
        self.donate_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(self.donate_url)))
        support.addWidget(self.donate_button)
        layout.addLayout(support)
        self.content_task = None
        self.remote_characters = []
        self.status = QLabel(); self.status.setObjectName("subtitle"); layout.addWidget(self.status)
        care = QHBoxLayout()
        self.feed_button = QPushButton("ごはんをあげる")
        self.feed_button.clicked.connect(pet.feed)
        care.addWidget(self.feed_button)
        self.sleep_button = QPushButton("眠る / 起きる")
        self.sleep_button.setObjectName("secondary")
        self.sleep_button.clicked.connect(pet.toggle_sleep)
        care.addWidget(self.sleep_button)
        layout.addLayout(care)
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(500)
        self.remember = QCheckBox("次回起動時も、選んだキャラをデスクトップに表示する")
        self.remember.setChecked(settings.value("show_pet_on_launch", False, type=bool))
        self.remember.toggled.connect(lambda value: settings.setValue("show_pet_on_launch", value))
        layout.addWidget(self.remember)
        buttons = QHBoxLayout()
        self.toggle = QPushButton("デスクトップに表示する"); self.toggle.clicked.connect(self.toggle_pet)
        buttons.addWidget(self.toggle)
        quit_button = QPushButton("アプリを終了"); quit_button.setObjectName("secondary"); quit_button.clicked.connect(self.close); buttons.addWidget(quit_button)
        layout.addLayout(buttons)
        help_text = QLabel("「×」や「アプリを終了」でキャラも終了します。最小化するとネコはそのまま表示されます。")
        help_text.setObjectName("subtitle"); help_text.setWordWrap(True); layout.addWidget(help_text)
        self.populate_characters()
        self.update_status()

    def present(self):
        # Recover minimized/off-screen windows and request foreground after launch.
        self.showNormal()
        screen = QApplication.primaryScreen().availableGeometry()
        width = min(760, screen.width()-24)
        height = min(640, screen.height()-24)
        self.setMinimumSize(min(620, width), min(520, height))
        self.resize(width, height)
        self.move(screen.center().x()-self.width()//2,
                  screen.center().y()-self.height()//2)
        self.update_status()
        self.raise_()
        self.activateWindow()
        if sys.platform == "win32":
            user32 = ctypes.WinDLL("user32", use_last_error=True)
            user32.ShowWindow.argtypes = [W.HWND, ctypes.c_int]
            user32.SetForegroundWindow.argtypes = [W.HWND]
            handle = int(self.winId())
            user32.ShowWindow(handle, 9)
            user32.SetForegroundWindow(handle)

    def populate_characters(self):
        selected = self.settings.value("character", "tabby_cat")
        self.character_picker.clear()
        for info in BUILTINS:
            self.character_picker.addItem(info["name"]+"（無料）", dict(info))
        if self.character_root.exists():
            for directory in sorted(self.character_root.iterdir()):
                try:
                    if directory.is_symlink() or not directory.is_dir():
                        continue
                    info = json.loads((directory / "character.json").read_text(encoding="utf-8"))
                    self.character_picker.addItem(info["name"]+"（保存済み）", {"path": str(directory), **info})
                except Exception:
                    continue
        for item in self.remote_characters:
            self.character_picker.addItem(item["name"]+"（ダウンロード）", {"remote": item})
        for index in range(self.character_picker.count()):
            data = self.character_picker.itemData(index)
            if data.get("id") == selected:
                self.character_picker.setCurrentIndex(index)
                try:
                    self.pet.load_character(data["path"], data.get("kind", "cat"))
                except Exception:
                    self.character_picker.setCurrentIndex(0)
                    self.pet.load_character(ROOT / "assets")
                self.settings.setValue("character_name", data["name"])
                self.update_character_preview(data["name"])
                break

    def update_character_preview(self, name):
        self.character_image.setPixmap(self.pet.frames["walk"][0].scaled(128,96,Qt.KeepAspectRatio,Qt.FastTransformation))
        self.character_title.setText(name + "  ·  無料")
        self.setWindowIcon(QIcon(self.pet.frames["walk"][0]))
        self.pet.tray.setIcon(QIcon(self.pet.frames["walk"][0]))

    def apply_character(self):
        if not self.pet.policy_allowed:
            return
        data = self.character_picker.currentData() or {}
        if "remote" in data:
            self.content_status.setText("先にダウンロードしてください。")
            return
        try:
            self.pet.load_character(data["path"], data.get("kind", "cat"))
            self.settings.setValue("character", data["id"])
            self.settings.setValue("character_name", data["name"])
            self.update_character_preview(data["name"])
            self.settings.sync()
            if not self.pet.isVisible():
                self.toggle_pet()
        except Exception as error:
            self.content_status.setText(str(error))

    def refresh_catalog(self):
        monitor = getattr(self.pet.app, "updates", None)
        if not monitor or not monitor.allowed or not monitor.policy:
            self.content_status.setText("開発版では内蔵キャラを利用できます。追加ダウンロードは公開更新URLの接続後に利用できます。" if BUILD_CHANNEL == "development" else "先に更新確認を完了してください。")
            return
        hosts = monitor.config["allowed_hosts"]
        self.run_content_task(lambda: catalog_entries(json.loads(fetch(monitor.policy["catalog_url"], hosts)), hosts), self.catalog_received)

    def catalog_received(self, entries):
        self.remote_characters = entries
        self.populate_characters()
        self.content_status.setText(f"追加できる無料キャラ：{len(entries)}件。公開されたキャラはすべて無料です。")

    def run_content_task(self, operation, completed):
        if self.content_task is not None and self.content_task.isRunning():
            return
        self.catalog_button.setEnabled(False)
        self.install_button.setEnabled(False)
        self.content_status.setText("通信中…")
        self.content_task = Task(operation, self)
        self.content_task.done.connect(completed)
        self.content_task.failed.connect(self.content_status.setText)
        self.content_task.finished.connect(lambda: self.catalog_button.setEnabled(self.pet.policy_allowed))
        self.content_task.finished.connect(lambda: self.install_button.setEnabled(self.pet.policy_allowed))
        self.content_task.start()

    def download_character(self):
        if not self.pet.policy_allowed:
            return
        item = (self.character_picker.currentData() or {}).get("remote")
        if not item:
            self.content_status.setText("追加キャラを確認し、一覧からダウンロード対象を選んでください。")
            return
        hosts = self.pet.app.updates.config["allowed_hosts"]
        self.run_content_task(lambda: install_character(item, fetch(item["url"], hosts, 10*1024*1024), self.character_root), self.character_installed)

    def character_installed(self, directory):
        if not self.pet.policy_allowed:
            self.content_status.setText("保存しました。更新確認後に利用できます。")
            return
        info = json.loads((Path(directory) / "character.json").read_text(encoding="utf-8"))
        self.settings.setValue("character", info["id"])
        self.populate_characters()
        self.apply_character()
        self.content_status.setText("キャラを追加しました。")

    def select_sparrow(self):
        # The standard cat and future character additions are all free.
        self.pet.load_character(ROOT / "assets")
        self.character_picker.setCurrentIndex(0)
        self.settings.setValue("character", "tabby_cat")
        self.settings.setValue("character_name", "茶トラねこ")
        self.settings.sync()
        self.update_character_preview("茶トラねこ")
        self.choose.setText("標準ネコを選ぶ")

    def update_status(self):
        shown = self.pet.isVisible()
        state = "おやすみ中" if self.pet.sleeping else ("ごはん、ありがとう ♥" if time.monotonic() < self.pet.heart_until else "おさんぽ中")
        name = self.settings.value("character_name", "茶トラねこ")
        self.status.setText(f"{name}：{state}" if shown else f"選択中：{name}（現在は非表示）")
        self.toggle.setText("デスクトップから隠す" if shown else "デスクトップに表示する")

    def toggle_pet(self):
        if not self.pet.policy_allowed:
            return
        if self.pet.isVisible():
            self.pet.hide()
            self.pet.set_paused(True)
        else:
            self.pet.pause_action.setChecked(False)
            self.pet.set_paused(False)
            self.pet.show()
        self.update_status()

    def closeEvent(self, event):
        self.pet.timer.stop()
        self.status_timer.stop()
        self.pet.tray.hide()
        self.pet.close()
        event.accept()
        QApplication.quit()


def main():
    if sys.platform != "win32" and "--preview" not in sys.argv:
        raise SystemExit("Windows 11向けです。")
    if sys.platform == "win32":
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("DesktopCat.App")
    app = QApplication(sys.argv)
    app.setOrganizationName("DesktopCat")
    app.setApplicationName("DesktopCatDev" if BUILD_CHANNEL == "development" else "DesktopCat")
    app.setQuitOnLastWindowClosed(False)
    settings = QSettings()
    app.updates = UpdateMonitor(app, ROOT / "update_config.json")
    app.pet = None

    def launch_or_resume():
        if app.pet is not None:
            app.pet.policy_allowed = True
            app.selector.setEnabled(True)
            return
        pet = DesktopCat(app)
        app.pet = pet
        if not settings.value("show_pet_on_launch", False, type=bool):
            pet.hide()
            pet.set_paused(True)
        app.aboutToQuit.connect(pet.close)
        app.aboutToQuit.connect(pet.tray.hide)
        app.selector = CharacterWindow(pet, settings)
        app.selector.present()
        QTimer.singleShot(250, app.selector.present)

    def block():
        if app.pet is not None:
            app.pet.policy_allowed = False
            app.pet.hide()
            app.selector.setEnabled(False)

    app.updates.permitted.connect(launch_or_resume)
    app.updates.blocked.connect(block)
    QTimer.singleShot(0, app.updates.check)
    if "--smoke" in sys.argv:
        QTimer.singleShot(1200, app.quit)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
