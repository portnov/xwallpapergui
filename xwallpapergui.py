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
    imageDropped = QtCore.pyqtSignal(object, str)

class ScreensView(QtWidgets.QGraphicsView):
    def mousePressEvent(self, ev):
        super().mousePressEvent(ev)
        ev.ignore()

    def mouseReleaseEvent(self, ev):
        super().mouseReleaseEvent(ev)
        self.scene().sceneClicked.emit()
        ev.ignore()
        #self.scene().screenClicked.emit(self)

class ScreenMock:
    def __init__(self, geometry, name, manufacturer, model, serial_number):
        self._geometry = geometry
        self._name = name
        self._manufacturer = manufacturer
        self._model = model
        self._serial_number = serial_number

    def name(self):
        return self._name
    
    def manufacturer(self):
        return self._manufacturer
    
    def model(self):
        return self._model
    
    def geometry(self):
        return self._geometry

    def serialNumber(self):
        return self._serial_number

class ScreenItem(QtWidgets.QGraphicsPixmapItem):
    def __init__(self, scale, screen, path=None, mode=None, parent=None):
        rect = screen.geometry()
        self.scale = scale
        self.orig_rect = rect
        self._name = screen.name()
        if not self._name:
            self._name = "[unnamed]"
        self._manufacturer = screen.manufacturer()
        if not self._manufacturer:
            self._manufacturer = "[unknown manufacturer]"
        self._model = screen.model()
        if not self._model:
            self._model = "[unknown model]"
        self._serial_number = screen.serialNumber()
        if not self._serial_number:
            self._serial_number = "[unknown number]"
        self.scaled_rect = QtCore.QRectF(rect.x() / scale, rect.y() / scale, rect.width() / scale, rect.height() / scale) 
        if path:
            pixmap = QtGui.QPixmap(path).scaled(int(self.scaled_rect.width()), int(self.scaled_rect.height()))
        else:
            pixmap = QtGui.QPixmap(int(self.scaled_rect.width()), int(self.scaled_rect.height()))
            pixmap.fill(QtGui.QColor("#00ff00"))
        super().__init__(pixmap, parent)
        self.setOffset(int(self.scaled_rect.x()), int(self.scaled_rect.y()))
        self.setFlags(QtWidgets.QGraphicsItem.ItemIsFocusable | QtWidgets.QGraphicsItem.ItemIsSelectable)
        self.setAcceptDrops(True)
        self.mode = mode
        if not self.mode:
            self.mode = "--zoom"
        self._path = path
        self._hashkey = None

    def name(self):
        return self._name
    
    def manufacturer(self):
        return self._manufacturer
    
    def model(self):
        return self._model

    def serialNumber(self):
        return self._serial_number

    @property
    def path(self):
        return self._path
    
    @path.setter
    def path(self, path):
        self._path = path
        if path:
            pixmap = QtGui.QPixmap(path).scaled(int(self.scaled_rect.width()), int(self.scaled_rect.height()))
        else:
            pixmap = QtGui.QPixmap(int(self.scaled_rect.width()), int(self.scaled_rect.height()))
            pixmap.fill(QtGui.QColor("#00ff00"))
        self.setPixmap(pixmap)

    def rect(self):
        return self.scaled_rect

    def geometry(self):
        return self.orig_rect

    def geometry_str(self):
        r = self.orig_rect
        return f"{int(r.width())}x{int(r.height())}+{int(r.x())}+{int(r.y())}"
    
    
    def monitor_name(self):
        return f"{self.manufacturer()} {self.model()} SN.{self.serialNumber()} @ {self.name()}"

    def tostring(self):
        return f"{self.monitor_name()}: {self.geometry_str()}"

    def for_hash(self):
        return f"[{self.name()}, {self.manufacturer()}, {self.model()}, {self.serialNumber()}, {self.geometry()}]"

    def hashkey(self):
        if self._hashkey is None:
            self._hashkey = md5(self.for_hash().encode('utf-8')).hexdigest()
        return self._hashkey
    
    def __repr__(self):
        return self.tostring()

    def mousePressEvent(self, ev):
        super().mousePressEvent(ev)
        ev.accept()

    def mouseReleaseEvent(self, ev):
        self.scene().screenClicked.emit(self)

    def mouseDoubleClickEvent(self, ev):
        self.scene().screenDoubleClicked.emit(self)

    def dropEvent(self, ev):
        data = ev.mimeData()
        if data.hasUrls():
            path = data.urls()[0].toLocalFile()
        elif data.hasText():
            path = data.text()
        if not path:
            return
        prefix = "file://"
        prefix_len = len(prefix)
        if path.startswith(prefix):
            path = path[prefix_len:]
        self.scene().imageDropped.emit(self, path)

def get_screens():
    return QtWidgets.QApplication.screens()

def get_screen_items(screens, width, height):
    rects = [s.geometry() for s in screens]
    max_x = max([s.x() + s.width() for s in rects])
    max_y = max([s.y() + s.height() for s in rects])
    rects = [QtCore.QRectF(s) for s in rects]
    scale_x = max_x / width
    scale_y = max_y / height
    scale = min(scale_x, scale_y)

    def get_mode(s):
        if hasattr(s, 'mode'):
            return s.mode
        else:
            return None

    return [ScreenItem(scale, s, mode=get_mode(s)) for s in screens]

def get_scaled_screens(width, height):
    screens = list(get_screens())
    return get_screen_items(screens, width, height)

class Config:
    def __init__(self):
        self.screens = []
        self.name = "Unknown"
        self.id = "___UNKNOWN___"

    def displayed_name(self, actual_id=None):
        if actual_id is not None and actual_id == self.id:
            selected = "[*] "
        else:
            selected = "[ ] "
        return f"{selected}[{self.id[:8]}]: {self.name}"
    
    def set_mode(self, screen_key, mode):
        for screen in self.screens:
            if screen.hashkey() == screen_key:
                screen.mode = mode
                return

    @staticmethod
    def screens_hash(screens=None):
        if screens is None:
            screens = get_screens()
        if not screens:
            return "___EMPTY___"
        s = ""
        for screen in sorted(screens, key = lambda s: s.name()):
            s = s + screen.for_hash()
        #print(f"Pre-hash: <{s}>")
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
        #print("current config id", empty_config.id)
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
            name = settings.value("name")
            manufacturer = settings.value("manufacturer")
            model = settings.value("model")
            serial_number = settings.value("serial_number")
            path = settings.value("path")
            paths.append(path)
            rect = QtCore.QRectF(x, y, w, h)
            mock = ScreenMock(rect, name, manufacturer, model, serial_number)
            screen = ScreenItem(1.0, mock)
            screen.mode = settings.value("mode")
            #print(f"Load: {screen.name()}, {screen.path}, {screen.mode}")
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
        configs = []
        current_config = Config.new()
        ids = set()
        for key in settings.childGroups():
            if not key.startswith(prefix):
                continue
            id = key[prefix_len:]
            ids.add(id)
            config = Config.from_settings(settings, id)
            configs.append(config)
        if not configs or current_config.id not in ids:
            configs.append(current_config)
        return configs
    
    def save(self, settings):
        section = f"config_{self.id}"
        settings.setValue(f"{section}/name", self.name)
        settings.beginWriteArray(f"{section}/screens")
        for i, screen in enumerate(self.screens):
            settings.setArrayIndex(i)
            settings.setValue("x", screen.orig_rect.x())
            settings.setValue("y", screen.orig_rect.y())
            settings.setValue("w", screen.orig_rect.width())
            settings.setValue("h", screen.orig_rect.height())
            settings.setValue("name", screen.name())
            settings.setValue("manufacturer", screen.manufacturer())
            settings.setValue("model", screen.model())
            settings.setValue("serial_number", screen.serialNumber())
            settings.setValue("path", screen.path)
            settings.setValue("mode", screen.mode)
            #print(f"W: {screen.name()} => {screen.path}, {screen.mode}")
        settings.endArray()

    def apply(self):
        args = []
        for screen in self.screens:
            args.append("--output")
            args.append(screen.name())
            args.append(screen.mode)
            args.append('"'+screen.path+'"')
        all_args = " ".join(args)
        command = f"xwallpaper {all_args}"
        print(command)
        subprocess.call(command, shell=True)

class GUI(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QtCore.QSettings("xwallpapergui", "xwallpapergui")
        self.scene = ScreensScene()
        self.graphics_view = ScreensView(self.scene, self)
        self.main_widget = QtWidgets.QWidget(self)
        self.selected_screen_key = None
        self.setCentralWidget(self.main_widget)
        layout = QtWidgets.QVBoxLayout()
        self.main_widget.setLayout(layout)
        topbar = QtWidgets.QWidget(self)
        topbar_layout = QtWidgets.QHBoxLayout()
        topbar.setLayout(topbar_layout)

        label = QtWidgets.QLabel("Configuration:", self)
        topbar_layout.addWidget(label)
        self.current_config_combo = QtWidgets.QComboBox(self)
        actual_id = self.get_current_config().id
        for cfg in Config.list_from_settings(self.settings):
            self.current_config_combo.addItem(cfg.displayed_name(actual_id), cfg.id)
        topbar_layout.addWidget(self.current_config_combo, True)

        rename_button = QtWidgets.QPushButton("Rename", self)
        rename_button.clicked.connect(self._on_rename_config)
        topbar_layout.addWidget(rename_button)

        layout.addWidget(topbar)
        layout.addWidget(self.graphics_view, True)

        self.bottombar = QtWidgets.QWidget(self)
        bottombar_layout = QtWidgets.QVBoxLayout()
        self.bottombar.setLayout(bottombar_layout)
        self.selected_screen_label = QtWidgets.QLabel(self)
        bottombar_layout.addWidget(self.selected_screen_label)

        path_layout = QtWidgets.QHBoxLayout()
        self.path_label = QtWidgets.QLabel(self)
        path_layout.addWidget(self.path_label, False, QtCore.Qt.AlignLeft)

        self.browse_button = QtWidgets.QPushButton("Browse...", self)
        self.browse_button.clicked.connect(self._on_browse_selected)
        self.browse_button.setEnabled(False)
        path_layout.addWidget(self.browse_button, False, QtCore.Qt.AlignLeft)
        path_layout.addStretch()

        bottombar_layout.addLayout(path_layout)

        mode_layout = QtWidgets.QHBoxLayout()
        mode_label = QtWidgets.QLabel("<b>Mode</b>:", self)
        mode_layout.addWidget(mode_label, False, QtCore.Qt.AlignLeft)

        self.mode_combo = QtWidgets.QComboBox(self)
        self.mode_combo.addItem("Maximize", "--maximize")
        self.mode_combo.addItem("Stretch", "--stretch")
        self.mode_combo.addItem("Zoom", "--zoom")
        self.mode_combo.addItem("Tile", "--tile")
        self.mode_combo.addItem("Center", "--center")
        self.mode_combo.setCurrentIndex(0)
        self.mode_combo.currentIndexChanged.connect(self._on_select_mode)
        self.mode_combo.setEnabled(False)
        mode_layout.addWidget(self.mode_combo, False, QtCore.Qt.AlignLeft)
        mode_layout.addStretch()

        bottombar_layout.addLayout(mode_layout)

        apply_button = QtWidgets.QPushButton("Apply", self)
        bottombar_layout.addWidget(apply_button, False, QtCore.Qt.AlignRight)
        apply_button.clicked.connect(self._on_apply)
        layout.addWidget(self.bottombar)

        self.load_config(self.get_current_config())
        self._set_selected_config(self.selected_config)

        self._mask_select_mode = False

        self.current_config_combo.currentIndexChanged.connect(self._on_select_config)
        self.scene.screenClicked.connect(self._on_screen_clicked)
        self.scene.sceneClicked.connect(self._on_scene_clicked)
        self.scene.screenDoubleClicked.connect(self._on_browse_screen)
        self.scene.imageDropped.connect(self._on_image_dropped)

    def _save_settings(self):
        self.selected_config.save(self.settings)
        self.settings.sync()

    def closeEvent(self, ev):
        self._save_settings()
        ev.accept()

    def _on_select_image(self, path):
        if not path:
            return
        key = self.selected_screen_key
        print(f"{key} :=> {path}")
        self.screen_items[key].path = path
        self.text_items[key].setPlainText(f"{self.screen_items[key].name()}: {basename(path)}")

    def _on_browse_selected(self, button):
        if self.selected_screen_key is None:
            return
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select file", ".", "Image files (*.jpg *.png *.png)")
        self._on_select_image(path)

    def _on_browse_screen(self, screen_item):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select file", ".", "Image files (*.jpg *.png *.png)")
        self.selected_screen_key = screen_item.hashkey()
        self._on_select_image(path)

    def _on_image_dropped(self, screen_item, path):
        self.selected_screen_key = screen_item.hashkey()
        self._on_select_image(path)
        self._display_selected_screen(screen_item)

    def _on_apply(self, button):
        self.selected_config.apply()

    def _on_select_mode(self):
        if self._mask_select_mode:
            return
        mode = self.mode_combo.currentData()
        self.selected_config.set_mode(self.selected_screen_key, mode)
        print("Selected", mode)
        self._save_settings()

    def _on_rename_config(self):
        new_name, ok = QtWidgets.QInputDialog.getText(self, "New configuration name", "New name:", QtWidgets.QLineEdit.Normal, self.selected_config.name)
        if ok and new_name:
            self.selected_config.name = new_name
            cfg_idx = self.current_config_combo.findData(self.selected_config.id)
            actual_id = self.get_current_config().id
            self.current_config_combo.setItemText(cfg_idx, self.selected_config.displayed_name(actual_id))
        self._save_settings()

    def _set_selected_config(self, cfg):
        cfg_idx = self.current_config_combo.findData(cfg.id)
        self.current_config_combo.setCurrentIndex(cfg_idx)

    def _set_selected_mode(self, mode):
        self._mask_select_mode = True
        mode_idx = self.mode_combo.findData(mode)
        self.mode_combo.setCurrentIndex(mode_idx)
        self._mask_select_mode = False

    def _on_select_config(self, src):
        self._save_settings()
        cfg_id = self.current_config_combo.currentData()
        config = Config.from_settings(self.settings, cfg_id)
        self.load_config(config)

    def get_current_config(self):
        return Config.current_from_settings(self.settings)
    
    def load_config(self, config):
        self.selected_config = config
        self.screen_items = dict([(s.hashkey(), s) for s in config.screens])
        self.text_items = dict()
        self.scene.clear()
        for screen_item in config.screens:
            self.scene.addItem(screen_item)
            if screen_item.path is None:
                text = f"{screen_item.name()}: <Not set>"
            else:
                text = f"{screen_item.name()}: {basename(screen_item.path)}"
            text_item = self.scene.addText(text)
            text_item.setPos(screen_item.rect().topLeft())
            self.text_items[screen_item.hashkey()] = text_item
        self.mode_combo.setEnabled(False)
        self.browse_button.setEnabled(False)

    def _display_selected_screen(self, screen_item):
        text = f"""<b>Selected screen</b>: geometry: {screen_item.geometry_str()}.<br>
        <b>Monitor</b>: {screen_item.monitor_name()}"""
        self.selected_screen_label.setText(text)
        self.path_label.setText(f"<b>Wallpaper</b>: {screen_item.path}")

    def _on_screen_clicked(self, screen_item):
        self._display_selected_screen(screen_item)
        self.selected_screen_key = screen_item.hashkey()
        #print(f"Screen clicked: {screen_item.name()}, {screen_item.path}, {screen_item.mode}")
        self._set_selected_mode(screen_item.mode)
        self.mode_combo.setEnabled(True)
        self.browse_button.setEnabled(True)

    def _on_scene_clicked(self):
        selected = self.scene.selectedItems()
        if not selected:
            self.selected_screen_label.setText("")
            self.mode_combo.setEnabled(False)
            self.browse_button.setEnabled(False)
            self.selected_screen_key = None

def launch_gui():
    app = QtWidgets.QApplication(sys.argv)
    win = GUI()
    win.show()
    sys.exit(app.exec_())

if __name__ == "__main__":

    parser = argparse.ArgumentParser(prog="xwallpapergui", description="Manipulate wallpapers in multimonitor configurations using xwallpaper")
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
        settings = QtCore.QSettings("xwallpapergui", "xwallpapergui")
        if args.id is None:
            config = Config.current_from_settings(settings)
        else:
            config = Config.from_settings(settings, args.id)
            if config is None:
                print(f"No configuration with such ID: {args.id}")
                sys.exit(1)
        config.apply()
    elif args.command == "list":
        app = QtWidgets.QApplication(sys.argv)
        settings = QtCore.QSettings("xwallpapergui", "xwallpapergui")
        current_config = Config.current_from_settings(settings)
        for config in Config.list_from_settings(settings):
            if config.id == current_config.id:
                selected = "[*] "
            else:
                selected = "[ ] "
            print(f"{selected}Configuration: ID = {config.id}, name = {config.name}")
            for screen in config.screens:
                print(f"\t{screen.tostring()}: wallpaper {screen.path}, mode {screen.mode}")

