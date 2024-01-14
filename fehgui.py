#!/usr/bin/python3

import sys
from os.path import basename
from hashlib import md5
import subprocess
import argparse
from PyQt5 import QtCore, QtWidgets, QtGui

class ScreensScene(QtWidgets.QGraphicsScene):
    screenClicked = QtCore.pyqtSignal(object)
    screenDoubleClicked = QtCore.pyqtSignal(object)
    sceneClicked = QtCore.pyqtSignal()

class ScreensView(QtWidgets.QGraphicsView):
    def mousePressEvent(self, ev):
        super().mousePressEvent(ev)
        ev.ignore()

    def mouseReleaseEvent(self, ev):
        super().mouseReleaseEvent(ev)
        self.scene().sceneClicked.emit()
        ev.ignore()
        #self.scene().screenClicked.emit(self)

class ScreenItem(QtWidgets.QGraphicsPixmapItem):
    def __init__(self, number, scale, rect, path=None, parent=None):
        self.scale = scale
        self.orig_rect = rect
        self.scaled_rect = QtCore.QRectF(rect.x() / scale, rect.y() / scale, rect.width() / scale, rect.height() / scale) 
        print(path)
        pixmap = QtGui.QPixmap(path).scaled(int(self.scaled_rect.width()), int(self.scaled_rect.height()))
        super().__init__(pixmap, parent)
        self.setOffset(int(self.scaled_rect.x()), int(self.scaled_rect.y()))
        self.number = number
        #self.setPen(QtGui.QPen(QtGui.QColor("red")))
        self.setFlags(QtWidgets.QGraphicsItem.ItemIsFocusable | QtWidgets.QGraphicsItem.ItemIsSelectable)
        self._path = path

    @property
    def path(self):
        return self._path
    
    @path.setter
    def path(self, path):
        self._path = path
        pixmap = QtGui.QPixmap(path).scaled(int(self.scaled_rect.width()), int(self.scaled_rect.height()))
        self.setPixmap(pixmap)

    def rect(self):
        return self.scaled_rect

    def geometry(self):
        r = self.orig_rect
        return f"{int(r.width())}x{int(r.height())}+{int(r.x())}+{int(r.y())}"
    
    def tostring(self):
        return f"{self.number}: {self.geometry()}"

    def mousePressEvent(self, ev):
        super().mousePressEvent(ev)
        ev.accept()

    def mouseReleaseEvent(self, ev):
        self.scene().screenClicked.emit(self)

    def mouseDoubleClickEvent(self, ev):
        self.scene().screenDoubleClicked.emit(self)

def get_screens():
    screens = QtWidgets.QApplication.screens()
    for screen in screens:
        yield screen.geometry()

def get_screen_items(screens, width, height):
    max_x = max([s.x() + s.width() for s in screens])
    max_y = max([s.y() + s.height() for s in screens])
    screens = [QtCore.QRectF(s) for s in screens]
    scale_x = max_x / width
    scale_y = max_y / height
    scale = min(scale_x, scale_y)
    return [ScreenItem(i, scale, s) for i, s in enumerate(screens)]

def get_scaled_screens(width, height):
    screens = list(get_screens())
    return get_screen_items(screens, width, height)

class Config:
    def __init__(self):
        self.screens = []
        self.name = "Unknown"
        self.id = "___UNKNOWN___"

    @staticmethod
    def screens_hash(screens=None):
        if screens is None:
            screens = get_screens()
        if not screens:
            return "___EMPTY___"
        s = ""
        for i, screen in enumerate(screens):
            s = s + f"screen {i}: {screen.orig_rect}"
        print(f"Pre-hash: <{s}>")
        return md5(s.encode('utf-8')).hexdigest()

    @staticmethod
    def new():
        cfg = Config()
        cfg.screens = get_scaled_screens(320, 200)
        cfg.name = f"New: {len(cfg.screens)} monitors"
        cfg.id = Config.screens_hash(cfg.screens)
        return cfg
    
    @staticmethod
    def current_from_settings(settings):
        empty_config = Config.new()
        section = f"config_{empty_config.id}"
        print("current config id", empty_config.id)
        name = settings.value(f"{section}/name")
        if not name:
            print(f"loading new config, name={empty_config.name}")
            return empty_config
        else:
            return Config.from_settings(settings, empty_config.id)

    @staticmethod
    def from_settings(settings, id):
        cfg = Config()
        cfg.id = id
        section = f"config_{id}"
        cfg.name = settings.value(f"{section}/name")
        if not cfg.name:
            return None
        n_screens = settings.beginReadArray(f"{section}/screens")
        screens = []
        paths = []
        for i in range(n_screens):
            settings.setArrayIndex(i)
            x = settings.value("x", type=int)
            y = settings.value("y", type=int)
            w = settings.value("w", type=int)
            h = settings.value("h", type=int)
            path = settings.value("path")
            paths.append(path)
            screen = QtCore.QRectF(x, y, w, h)
            screens.append(screen)
        settings.endArray()
        cfg.screens = get_screen_items(screens, 320, 200)
        for screen, path in zip(cfg.screens, paths):
            screen.path = path
        return cfg
    
    @staticmethod
    def list_from_settings(settings):
        prefix = "config_"
        prefix_len = len(prefix)
        for key in settings.childGroups():
            if not key.startswith(prefix):
                continue
            id = key[prefix_len:]
            config = Config.from_settings(settings, id)
            yield config
    
    def save(self, settings):
        section = f"config_{self.id}"
        settings.setValue(f"{section}/name", self.name)
        settings.beginWriteArray(f"{section}/screens")
        for screen in self.screens:
            settings.setArrayIndex(screen.number)
            settings.setValue("x", screen.orig_rect.x())
            settings.setValue("y", screen.orig_rect.y())
            settings.setValue("w", screen.orig_rect.width())
            settings.setValue("h", screen.orig_rect.height())
            settings.setValue("path", screen.path)
            print(f"W: {screen.number} => {screen.path}")
        settings.endArray()

    def apply(self):
        screens = sorted(self.screens, key = lambda s: s.number)
        paths = ["\""+s.path+"\"" for s in screens if s.path is not None]
        all_paths = " ".join(paths)
        command = f"feh --bg-scale {all_paths}"
        print(command)
        subprocess.call(command, shell=True)

class GUI(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QtCore.QSettings("fehgui", "fehgui")
        self.scene = ScreensScene()
        self.graphics_view = ScreensView(self.scene, self)
        self.main_widget = QtWidgets.QWidget(self)
        self.selected_screen_id = None
        self.setCentralWidget(self.main_widget)
        layout = QtWidgets.QVBoxLayout()
        self.main_widget.setLayout(layout)
        topbar = QtWidgets.QWidget(self)
        topbar_layout = QtWidgets.QHBoxLayout()
        topbar.setLayout(topbar_layout)
        self.current_config_label = QtWidgets.QLabel(self)
        topbar_layout.addWidget(self.current_config_label)
        layout.addWidget(topbar)
        layout.addWidget(self.graphics_view, True)
        self.bottombar = QtWidgets.QWidget(self)
        bottombar_layout = QtWidgets.QHBoxLayout()
        self.bottombar.setLayout(bottombar_layout)
        self.selected_screen_label = QtWidgets.QLabel(self)
        bottombar_layout.addWidget(self.selected_screen_label, True)
        browse_button = QtWidgets.QPushButton("Browse...", self)
        browse_button.clicked.connect(self._on_browse_selected)
        bottombar_layout.addWidget(browse_button)
        apply_button = QtWidgets.QPushButton("Apply", self)
        bottombar_layout.addWidget(apply_button)
        apply_button.clicked.connect(self._on_apply)
        layout.addWidget(self.bottombar)
        self.load_config(self.get_current_config())
        self.scene.screenClicked.connect(self._on_screen_clicked)
        self.scene.sceneClicked.connect(self._on_scene_clicked)
        self.scene.screenDoubleClicked.connect(self._on_browse_screen)

    def closeEvent(self, ev):
        self.selected_config.save(self.settings)
        self.settings.sync()
        ev.accept()

    def _on_select_image(self, path):
        if not path:
            return
        i = self.selected_screen_id
        print(f"{i} :=> {path}")
        self.screen_items[i].path = path
        self.text_items[i].setPlainText(f"{i}: {basename(path)}")

    def _on_browse_selected(self, button):
        if self.selected_screen_id is None:
            return
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select file", ".", "Image files (*.jpg *.png *.png)")
        self._on_select_image(path)

    def _on_browse_screen(self, screen_item):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select file", ".", "Image files (*.jpg *.png *.png)")
        self.selected_screen_id = screen_item.number
        self._on_select_image(path)

    def _on_apply(self, button):
        self.selected_config.apply()

    def get_current_config(self):
        return Config.current_from_settings(self.settings)
    
    def load_config(self, config):
        self.selected_config = config
        self.current_config_label.setText(f"Config: {config.name}")
        self.screen_items = config.screens[:]
        self.text_items = []
        for screen_item in config.screens:
            self.scene.addItem(screen_item)
            if screen_item.path is None:
                text = f"{screen_item.number}: <Not set>"
            else:
                text = f"{screen_item.number}: {basename(screen_item.path)}"
            text_item = self.scene.addText(text)
            text_item.setPos(screen_item.rect().topLeft())
            self.text_items.append(text_item)

    def _on_screen_clicked(self, screen_item):
        r = screen_item.orig_rect
        self.selected_screen_label.setText(f"Screen #{screen_item.number}, position: {int(r.x())}, {int(r.y())}, size: {int(r.width())} x {int(r.height())}. Path: {screen_item.path}")
        self.selected_screen_id = screen_item.number

    def _on_scene_clicked(self):
        selected = self.scene.selectedItems()
        if not selected:
            self.selected_screen_label.setText("")
            self.selected_screen_id = None

def launch_gui():
    app = QtWidgets.QApplication(sys.argv)
    win = GUI()
    win.show()
    sys.exit(app.exec_())

if __name__ == "__main__":

    parser = argparse.ArgumentParser(prog="fehgui", description="Manipulate wallpapers in multimonitor configurations using feh")
    subparsers = parser.add_subparsers(title="Action to be executed", dest="command")
    parser_apply = subparsers.add_parser("apply", help="Apply wallpapers from saved configuration")
    parser_apply.add_argument('-i', '--id', metavar="ID", help="Apply wallpapers from specified configuration")
    parser_list = subparsers.add_parser("list", help="List existing configurations")
    parser_gui = subparsers.add_parser("gui", help="Launch GUI to configure wallpapers (default)")

    args = parser.parse_args()
    if args.command is None or args.command == "gui":
        launch_gui()
    elif args.command == "apply":
        app = QtWidgets.QApplication(sys.argv)
        settings = QtCore.QSettings("fehgui", "fehgui")
        if args.id is None:
            config = Config.current_from_settings(settings)
        else:
            config = Config.from_settings(settings, args.id)
            if config is None:
                print(f"No configuration with such ID: {args.id}")
                sys.exit(1)
        config.apply()
    elif args.command == "list":
        settings = QtCore.QSettings("fehgui", "fehgui")
        for config in Config.list_from_settings(settings):
            print(f"Configuration: ID = {config.id}, name = {config.name}")
            for screen in config.screens:
                print(f"\tScreen {screen.tostring()}: {screen.path}")

