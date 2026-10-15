import json
from pathlib import Path
from PySide6.QtCore import QObject, QThread, Signal, QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QApplication
from online_content import APP_VERSION, load_policy
from build_channel import BUILD_CHANNEL


class Task(QThread):
    done = Signal(object)
    failed = Signal(str)

    def __init__(self, operation, parent=None):
        super().__init__(parent)
        self.operation = operation
        # Let an in-flight bounded network request finish before Qt tears down threads.
        app = QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self.wait)

    def run(self):
        try:
            self.done.emit(self.operation())
        except Exception as error:
            self.failed.emit(str(error))


class UpdateMonitor(QObject):
    permitted = Signal()
    blocked = Signal()

    def __init__(self, app, config_path):
        super().__init__(app)
        self.allowed = False
        self.policy = None
        self.worker = None
        try:
            self.config = json.loads(Path(config_path).read_text(encoding="utf-8"))
        except Exception:
            self.config = {}
        self.dialog = QDialog()
        self.dialog.setWindowTitle(f"DesktopCat {APP_VERSION} — 更新確認")
        self.dialog.resize(470, 240)
        layout = QVBoxLayout(self.dialog)
        self.title = QLabel("更新を確認しています…")
        self.title.setStyleSheet("font-size:20px;font-weight:600;")
        layout.addWidget(self.title)
        self.message = QLabel("最新版の確認が完了するまでお待ちください。")
        self.message.setWordWrap(True)
        layout.addWidget(self.message)
        self.download = QPushButton("更新ページを開く")
        self.download.setEnabled(False)
        self.download.clicked.connect(self.open_download)
        layout.addWidget(self.download)
        self.retry = QPushButton("再確認する")
        self.retry.clicked.connect(self.check)
        layout.addWidget(self.retry)
        close = QPushButton("アプリを終了")
        close.clicked.connect(app.quit)
        layout.addWidget(close)
        self.dialog.rejected.connect(app.quit)
        self.periodic = QTimer(self)
        self.periodic.timeout.connect(self.check)
        if BUILD_CHANNEL == "release":
            self.periodic.start(15*60*1000)

    def open_download(self):
        if self.policy:
            QDesktopServices.openUrl(QUrl(self.policy["download_url"]))

    def check(self):
        if BUILD_CHANNEL == "development":
            self.allowed = True
            self.dialog.hide()
            self.permitted.emit()
            return
        if self.worker is not None and self.worker.isRunning():
            return
        self.retry.setEnabled(False)
        if not self.allowed:
            self.dialog.show()
            self.dialog.raise_()
        self.worker = Task(lambda: load_policy(self.config), self)
        self.worker.done.connect(self.accept_policy)
        self.worker.failed.connect(self.fail)
        self.worker.start()

    def accept_policy(self, result):
        policy, allowed = result
        self.policy = policy
        self.allowed = allowed
        self.retry.setEnabled(True)
        self.download.setEnabled(True)
        if allowed:
            self.dialog.hide()
            self.permitted.emit()
        else:
            self.title.setText("更新が必要です")
            self.message.setText(
                f"現在：{APP_VERSION} / 最低対応版：{policy['minimum_version']}\n"
                + str(policy.get("message", "更新後に再起動してください。"))[:300])
            self.blocked.emit()
            self.dialog.show()
            self.dialog.raise_()
            self.dialog.activateWindow()

    def fail(self, error):
        self.allowed = False
        self.title.setText("更新を確認できません")
        self.message.setText("安全にバージョンを確認できるまで利用を停止します。\n" + error[:300])
        self.retry.setEnabled(True)
        self.download.setEnabled(self.policy is not None)
        self.blocked.emit()
        self.dialog.show()
        self.dialog.raise_()
