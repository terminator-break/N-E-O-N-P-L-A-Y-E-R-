"""
╔══════════════════════════════════════════════════════════════════════════════╗
║            NEON PLAYER — YouTube Audio Overlay                             ║
║  Always-on-top, полупрозрачный мини-плеер с киберпанк-стилем               ║
║  Зависимости: PyQt5, yt-dlp, python-vlc, keyboard, requests, Pillow        ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import sys
import os
import io
import json
import time
import threading
import queue
import ctypes
import platform
import urllib.request
from pathlib import Path
from typing import Optional, List, Dict

# ── Qt ────────────────────────────────────────────────────────────────────────
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QSlider, QHBoxLayout,
    QVBoxLayout, QLineEdit, QSystemTrayIcon, QMenu, QAction, QDialog,
    QComboBox, QSpinBox, QDoubleSpinBox, QFormLayout, QGroupBox,
    QMessageBox, QFrame, QSizeGrip, QGraphicsDropShadowEffect
)
from PyQt5.QtCore import (
    Qt, QTimer, QThread, pyqtSignal, QPoint, QSize, QRect,
    QPropertyAnimation, QEasingCurve
)
from PyQt5.QtGui import (
    QPainter, QColor, QLinearGradient, QRadialGradient, QFont,
    QFontDatabase, QPixmap, QIcon, QPen, QBrush, QPainterPath,
    QImage, QPalette
)

# ── Сторонние ────────────────────────────────────────────────────────────────
try:
    import vlc
except ImportError:
    vlc = None
    print("[WARN] python-vlc не установлен. Воспроизведение недоступно.")

try:
    import yt_dlp
except ImportError:
    yt_dlp = None
    print("[WARN] yt-dlp не установлен. Загрузка треков недоступна.")

try:
    import keyboard as kb
except ImportError:
    kb = None
    print("[WARN] keyboard не установлен. Глобальные горячие клавиши недоступны.")

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("[WARN] Pillow не установлен. Обложки могут не работать.")

# ── Константы ─────────────────────────────────────────────────────────────────
APP_NAME   = "NeonPlayer"
VERSION    = "1.0.0"
CONFIG_DIR = Path.home() / ".neonplayer"
CONFIG_FILE = CONFIG_DIR / "config.json"
LIKES_FILE  = CONFIG_DIR / "likes.json"

# Цветовая палитра «Киберпанк»
C_BG        = QColor(12, 10, 20, 200)       # тёмный фон с прозрачностью
C_BG_PANEL  = QColor(20, 15, 35, 220)
C_VIOLET    = QColor(180, 0, 255)            # неоновый фиолетовый
C_CYAN      = QColor(0, 255, 220)            # неоновый бирюзовый
C_PINK      = QColor(255, 0, 128)            # акцент розовый
C_TEXT      = QColor(220, 210, 255)          # светлый текст
C_TEXT_DIM  = QColor(120, 100, 180)          # приглушённый текст
C_GLASS     = QColor(255, 255, 255, 18)      # стекло

DEFAULT_CONFIG = {
    "volume": 70,
    "opacity": 0.88,
    "width": 340,
    "height": 480,
    "audio_device": "",
    "hotkey_play": "media play pause",
    "hotkey_next": "media next track",
    "hotkey_prev": "media previous track",
    "hotkey_vol_up": "ctrl+alt+up",
    "hotkey_vol_down": "ctrl+alt+down",
    "pos_x": 100,
    "pos_y": 100,
}

# ══════════════════════════════════════════════════════════════════════════════
#  Утилиты конфигурации
# ══════════════════════════════════════════════════════════════════════════════
def load_config() -> dict:
    """Загружает конфиг из JSON, создаёт дефолтный если не существует."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            # Добавляем новые ключи если конфиг устарел
            for k, v in DEFAULT_CONFIG.items():
                cfg.setdefault(k, v)
            return cfg
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()

def save_config(cfg: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)

def load_likes() -> List[str]:
    if LIKES_FILE.exists():
        try:
            with open(LIKES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []

def save_likes(likes: List[str]) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(LIKES_FILE, "w", encoding="utf-8") as f:
        json.dump(likes, f, indent=2, ensure_ascii=False)


# ══════════════════════════════════════════════════════════════════════════════
#  Win32 вспомогательные функции (Windows-only)
# ══════════════════════════════════════════════════════════════════════════════
def set_windows_always_on_top_click_through(hwnd: int, enable: bool) -> None:
    """
    Устанавливает флаги WS_EX_LAYERED и WS_EX_TRANSPARENT на окно,
    чтобы оно оставалось поверх DirectX/OpenGL и не перехватывало
    клики мыши в прозрачных областях.
    """
    if platform.system() != "Windows":
        return
    try:
        GWL_EXSTYLE     = -20
        WS_EX_LAYERED   = 0x00080000
        WS_EX_TRANSPARENT = 0x00000020
        WS_EX_TOPMOST   = 0x00000008
        HWND_TOPMOST    = -1
        SWP_NOMOVE      = 0x0002
        SWP_NOSIZE      = 0x0001

        user32 = ctypes.windll.user32
        style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        if enable:
            # Добавляем флаги прозрачности для кликов в пустых зонах
            style |= WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOPMOST
        else:
            style &= ~WS_EX_TRANSPARENT
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
        # Принудительно ставим поверх всех окон, включая fullscreen
        user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                            SWP_NOMOVE | SWP_NOSIZE)
    except Exception as e:
        print(f"[Win32] SetWindowPos ошибка: {e}")


# ══════════════════════════════════════════════════════════════════════════════
#  Поток загрузки информации о треке через yt-dlp
# ══════════════════════════════════════════════════════════════════════════════
class TrackInfo:
    """Данные об одном треке."""
    def __init__(self):
        self.title: str  = "Неизвестный трек"
        self.artist: str = "Неизвестный исполнитель"
        self.url: str    = ""           # прямая ссылка на аудиопоток
        self.thumbnail_url: str = ""
        self.thumbnail: Optional[QPixmap] = None
        self.duration: int = 0          # секунды
        self.webpage_url: str = ""      # оригинальный URL YouTube
        self.video_id: str = ""


class YtDlpThread(QThread):
    """
    Фоновый поток: извлекает метаданные и прямые URL аудиопотоков
    через yt-dlp без скачивания файлов.
    """
    tracks_ready   = pyqtSignal(list)   # list[TrackInfo]
    error_occurred = pyqtSignal(str)
    progress       = pyqtSignal(str)    # текстовый статус

    def __init__(self, url: str, parent=None):
        super().__init__(parent)
        self.url = url

    def run(self):
        if yt_dlp is None:
            self.error_occurred.emit("yt-dlp не установлен")
            return

        self.progress.emit("Получение информации...")

        ydl_opts = {
            # Только аудио, лучшее качество
            "format": "bestaudio/best",
            # Не скачивать, только получить URL
            "nodownload": True,
            "quiet": True,
            "no_warnings": True,
            # Разворачиваем плейлист
            "extract_flat": False,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.url, download=False)

            tracks = []
            # Плейлист возвращает entries, одиночное видео — нет
            entries = info.get("entries", None)
            if entries is None:
                entries = [info]

            for entry in entries:
                if entry is None:
                    continue
                t = TrackInfo()
                t.title       = entry.get("title", "Без названия")
                t.artist      = (entry.get("uploader") or
                                 entry.get("channel") or "Неизвестно")
                t.duration    = int(entry.get("duration") or 0)
                t.webpage_url = entry.get("webpage_url", self.url)
                t.video_id    = entry.get("id", "")
                t.thumbnail_url = entry.get("thumbnail", "")

                # Находим прямой URL аудиопотока
                t.url = self._pick_audio_url(entry)
                tracks.append(t)

            self.tracks_ready.emit(tracks)

        except Exception as e:
            self.error_occurred.emit(str(e))

    @staticmethod
    def _pick_audio_url(entry: dict) -> str:
        """Выбирает лучший аудио-URL из форматов."""
        formats = entry.get("formats", [])
        # Приоритет: только аудио форматы
        audio_fmts = [f for f in formats
                      if f.get("vcodec") == "none" and f.get("url")]
        if audio_fmts:
            # Сортируем по битрейту
            audio_fmts.sort(key=lambda x: x.get("abr") or 0, reverse=True)
            return audio_fmts[0]["url"]
        # Если отдельного аудио нет — берём первый доступный
        if formats and formats[0].get("url"):
            return formats[0]["url"]
        # Fallback
        return entry.get("url", "")


class ThumbnailLoader(QThread):
    """Загружает обложку трека в фоне."""
    loaded = pyqtSignal(QPixmap, str)  # pixmap, video_id

    def __init__(self, url: str, video_id: str, parent=None):
        super().__init__(parent)
        self.url = url
        self.video_id = video_id

    def run(self):
        if not self.url:
            return
        try:
            req = urllib.request.Request(
                self.url,
                headers={"User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = resp.read()

            img = QImage()
            img.loadFromData(data)
            if not img.isNull():
                px = QPixmap.fromImage(img)
                self.loaded.emit(px, self.video_id)
        except Exception as e:
            print(f"[Thumbnail] Ошибка загрузки: {e}")


# ══════════════════════════════════════════════════════════════════════════════
#  VLC-плеер обёртка
# ══════════════════════════════════════════════════════════════════════════════
class VLCPlayer:
    """
    Тонкая обёртка вокруг python-vlc для воспроизведения аудио.
    Видеовыход полностью отключён.
    """
    def __init__(self, audio_device: str = ""):
        if vlc is None:
            self.instance = None
            self.player   = None
            return

        # Создаём инстанс VLC с параметрами только-аудио
        args = ["--no-video", "--no-xlib", "--quiet"]
        self.instance = vlc.Instance(*args)
        self.player   = self.instance.media_player_new()

        # Указываем аудиовыход если задан
        if audio_device:
            self.player.audio_output_device_set(None, audio_device)

    def play_url(self, url: str) -> None:
        if not self.player:
            return
        media = self.instance.media_new(url)
        self.player.set_media(media)
        self.player.play()

    def pause(self) -> None:
        if self.player:
            self.player.pause()

    def stop(self) -> None:
        if self.player:
            self.player.stop()

    def is_playing(self) -> bool:
        if not self.player:
            return False
        return self.player.is_playing() == 1

    def set_volume(self, vol: int) -> None:
        """vol: 0–100"""
        if self.player:
            self.player.audio_set_volume(vol)

    def get_position(self) -> float:
        """Возвращает 0.0–1.0"""
        if not self.player:
            return 0.0
        return self.player.get_position()

    def set_position(self, pos: float) -> None:
        if self.player:
            self.player.set_position(pos)

    def get_time(self) -> int:
        """Текущая позиция в миллисекундах."""
        if not self.player:
            return 0
        return max(0, self.player.get_time())

    def get_length(self) -> int:
        """Длина в миллисекундах."""
        if not self.player:
            return 0
        return max(0, self.player.get_length())

    def get_audio_devices(self) -> List[str]:
        """Список аудиоустройств VLC."""
        if not self.player:
            return []
        devices = []
        try:
            mods = self.player.audio_output_enumerate_devices()
            if mods:
                for m in mods:
                    name = m.get("description", b"").decode("utf-8", errors="replace")
                    devices.append(name)
        except Exception:
            pass
        return devices

    def ended(self) -> bool:
        """Проверяет, закончился ли трек."""
        if not self.player:
            return False
        state = self.player.get_state()
        return state in (vlc.State.Ended, vlc.State.Error)


# ══════════════════════════════════════════════════════════════════════════════
#  Кастомные виджеты — стиль «Киберпанк / Стекломорфизм»
# ══════════════════════════════════════════════════════════════════════════════
class NeonButton(QPushButton):
    """Кнопка с неоновым свечением при наведении."""

    def __init__(self, text: str, color: QColor = None, parent=None):
        super().__init__(text, parent)
        self._color    = color or C_VIOLET
        self._hovered  = False
        self._pressed  = False
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(32)
        self._setup_glow()

    def _setup_glow(self):
        glow = QGraphicsDropShadowEffect(self)
        glow.setBlurRadius(14)
        glow.setColor(self._color)
        glow.setOffset(0, 0)
        self.setGraphicsEffect(glow)

    def enterEvent(self, e):
        self._hovered = True
        eff = self.graphicsEffect()
        if eff:
            eff.setBlurRadius(28)
        self.update()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hovered = False
        eff = self.graphicsEffect()
        if eff:
            eff.setBlurRadius(14)
        self.update()
        super().leaveEvent(e)

    def mousePressEvent(self, e):
        self._pressed = True
        self.update()
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        self._pressed = False
        self.update()
        super().mouseReleaseEvent(e)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = self.rect().adjusted(2, 2, -2, -2)

        # Фон
        alpha = 180 if self._hovered else 100
        bg = QColor(self._color.red(), self._color.green(),
                    self._color.blue(), alpha if self._pressed else alpha // 2)
        p.setBrush(bg)
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(r, 6, 6)

        # Обводка
        border_col = QColor(self._color)
        border_col.setAlpha(200 if self._hovered else 120)
        p.setPen(QPen(border_col, 1.5))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(r, 6, 6)

        # Текст
        p.setPen(C_TEXT if self._hovered else QColor(self._color))
        p.setFont(QFont("Segoe UI", 9, QFont.Bold))
        p.drawText(self.rect(), Qt.AlignCenter, self.text())


class IconButton(QPushButton):
    """Маленькая иконочная кнопка (символ Unicode) с неоновым свечением."""

    def __init__(self, symbol: str, color: QColor = None,
                 size: int = 36, parent=None):
        super().__init__(symbol, parent)
        self._color   = color or C_CYAN
        self._hovered = False
        self.setFixedSize(size, size)
        self.setCursor(Qt.PointingHandCursor)
        glow = QGraphicsDropShadowEffect(self)
        glow.setBlurRadius(10)
        glow.setColor(self._color)
        glow.setOffset(0, 0)
        self.setGraphicsEffect(glow)
        self.setStyleSheet("background: transparent; border: none;")

    def enterEvent(self, e):
        self._hovered = True
        eff = self.graphicsEffect()
        if eff:
            eff.setBlurRadius(22)
        self.update()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hovered = False
        eff = self.graphicsEffect()
        if eff:
            eff.setBlurRadius(10)
        self.update()
        super().leaveEvent(e)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        col = C_TEXT if self._hovered else self._color
        p.setPen(col)
        font = QFont("Segoe UI Symbol", 14)
        p.setFont(font)
        p.drawText(self.rect(), Qt.AlignCenter, self.text())


class GlassSlider(QSlider):
    """Ползунок в стиле стекломорфизма с градиентом."""

    def __init__(self, orientation=Qt.Horizontal, parent=None):
        super().__init__(orientation, parent)
        self.setFixedHeight(18)
        self.setStyleSheet("""
            QSlider::groove:horizontal {
                background: rgba(255,255,255,25);
                height: 4px;
                border-radius: 2px;
            }
            QSlider::sub-page:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #b400ff, stop:1 #00ffdc);
                height: 4px;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #ffffff;
                border: 2px solid #b400ff;
                width: 12px;
                height: 12px;
                margin: -4px 0;
                border-radius: 6px;
            }
            QSlider::handle:horizontal:hover {
                background: #b400ff;
                border: 2px solid #00ffdc;
            }
        """)


class Visualizer(QWidget):
    """
    Простой аудиовизуализатор: анимированные столбики.
    Поскольку VLC не предоставляет PCM-данные напрямую,
    используем псевдо-анимацию на основе таймера + случайных значений,
    синхронизированных с воспроизведением.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(40)
        self._bars     = [0.1] * 16          # высоты столбиков 0.0–1.0
        self._targets  = [0.1] * 16
        self._playing  = False
        self._timer    = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(50)                # 20 fps достаточно

    def set_playing(self, playing: bool):
        self._playing = playing

    def _tick(self):
        import random
        if self._playing:
            # Генерируем псевдо-случайные цели (имитация спектра)
            for i in range(len(self._targets)):
                if random.random() < 0.3:
                    # Центральные полосы выше — похоже на реальный звук
                    center_boost = 1.0 - abs(i - 7) / 8.0
                    self._targets[i] = random.uniform(0.1, 0.5 + center_boost * 0.5)
        else:
            self._targets = [0.05] * len(self._targets)

        # Плавное приближение к целям (lerp)
        for i in range(len(self._bars)):
            diff = self._targets[i] - self._bars[i]
            self._bars[i] += diff * 0.35
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w = self.width()
        h = self.height()
        n = len(self._bars)
        gap = 2
        bar_w = max(1, (w - gap * (n - 1)) // n)

        for i, val in enumerate(self._bars):
            bar_h = max(2, int(val * (h - 4)))
            x = i * (bar_w + gap)
            y = h - bar_h

            # Градиент от фиолетового к бирюзовому по высоте
            grad = QLinearGradient(x, y, x, h)
            t = i / (n - 1)
            r = int(180 * (1 - t))
            g = int(255 * t)
            b = int(255 * (1 - t) + 220 * t)
            grad.setColorAt(0.0, QColor(r, g, b, 220))
            grad.setColorAt(1.0, QColor(r // 2, g // 2, b // 2, 80))

            p.setBrush(QBrush(grad))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(x, y, bar_w, bar_h, 2, 2)


class TrackArtwork(QLabel):
    """Виджет обложки трека с закруглёнными углами и рамкой-свечением."""

    def __init__(self, size: int = 80, parent=None):
        super().__init__(parent)
        self._size = size
        self.setFixedSize(size, size)
        self._pixmap: Optional[QPixmap] = None
        glow = QGraphicsDropShadowEffect(self)
        glow.setBlurRadius(20)
        glow.setColor(C_VIOLET)
        glow.setOffset(0, 0)
        self.setGraphicsEffect(glow)

    def set_pixmap(self, px: QPixmap):
        self._pixmap = px.scaled(
            self._size, self._size,
            Qt.KeepAspectRatioByExpanding,
            Qt.SmoothTransformation
        )
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = self.rect()
        path = QPainterPath()
        path.addRoundedRect(r.x(), r.y(), r.width(), r.height(), 10, 10)
        p.setClipPath(path)

        if self._pixmap:
            p.drawPixmap(r, self._pixmap)
        else:
            # Плейсхолдер — градиентный квадрат с нотой
            grad = QLinearGradient(0, 0, self._size, self._size)
            grad.setColorAt(0.0, QColor(60, 0, 100))
            grad.setColorAt(1.0, QColor(0, 60, 80))
            p.fillRect(r, grad)
            p.setPen(C_VIOLET)
            p.setFont(QFont("Segoe UI Symbol", 28))
            p.drawText(r, Qt.AlignCenter, "♪")

        # Неоновая рамка
        p.setClipping(False)
        pen = QPen(QColor(180, 0, 255, 160), 2)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(r.adjusted(1, 1, -1, -1), 10, 10)


# ══════════════════════════════════════════════════════════════════════════════
#  Диалог настроек
# ══════════════════════════════════════════════════════════════════════════════
class SettingsDialog(QDialog):
    """Диалог настроек с поддержкой выбора аудиоустройства."""

    settings_changed = pyqtSignal(dict)

    def __init__(self, config: dict, audio_devices: List[str], parent=None):
        super().__init__(parent)
        self.config = config.copy()
        self.setWindowTitle("⚙ Настройки NeonPlayer")
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumWidth(360)
        self._build_ui(audio_devices)

    def _build_ui(self, devices: List[str]):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Заголовок
        title = QLabel("⚙ НАСТРОЙКИ")
        title.setStyleSheet("color: #b400ff; font: bold 13px 'Segoe UI';"
                            " letter-spacing: 3px;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.setSpacing(8)

        def label(txt):
            l = QLabel(txt)
            l.setStyleSheet("color: #dcd2ff; font: 10px 'Segoe UI';")
            return l

        # Громкость
        self.vol_spin = QSpinBox()
        self.vol_spin.setRange(0, 100)
        self.vol_spin.setValue(self.config["volume"])
        self._style_spinbox(self.vol_spin)
        form.addRow(label("Громкость:"), self.vol_spin)

        # Прозрачность
        self.opacity_spin = QDoubleSpinBox()
        self.opacity_spin.setRange(0.3, 1.0)
        self.opacity_spin.setSingleStep(0.05)
        self.opacity_spin.setValue(self.config["opacity"])
        self._style_spinbox(self.opacity_spin)
        form.addRow(label("Прозрачность:"), self.opacity_spin)

        # Ширина
        self.w_spin = QSpinBox()
        self.w_spin.setRange(260, 600)
        self.w_spin.setValue(self.config["width"])
        self._style_spinbox(self.w_spin)
        form.addRow(label("Ширина (px):"), self.w_spin)

        # Высота
        self.h_spin = QSpinBox()
        self.h_spin.setRange(360, 800)
        self.h_spin.setValue(self.config["height"])
        self._style_spinbox(self.h_spin)
        form.addRow(label("Высота (px):"), self.h_spin)

        # Аудиоустройство
        self.dev_combo = QComboBox()
        self.dev_combo.addItem("По умолчанию", "")
        for d in devices:
            self.dev_combo.addItem(d, d)
        self._style_combo(self.dev_combo)
        form.addRow(label("Аудиоустройство:"), self.dev_combo)

        layout.addLayout(form)

        # Кнопки
        btn_row = QHBoxLayout()
        ok_btn = NeonButton("Сохранить", C_VIOLET)
        ok_btn.clicked.connect(self._save)
        cancel_btn = NeonButton("Отмена", C_PINK)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(ok_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

    def _style_spinbox(self, w):
        w.setStyleSheet("""
            QAbstractSpinBox {
                background: rgba(20,15,35,200);
                color: #dcd2ff;
                border: 1px solid #b400ff;
                border-radius: 4px;
                padding: 2px 6px;
                font: 10px 'Segoe UI';
            }
            QAbstractSpinBox::up-button, QAbstractSpinBox::down-button {
                width: 16px;
                background: rgba(180,0,255,80);
            }
        """)

    def _style_combo(self, w):
        w.setStyleSheet("""
            QComboBox {
                background: rgba(20,15,35,200);
                color: #dcd2ff;
                border: 1px solid #b400ff;
                border-radius: 4px;
                padding: 2px 8px;
                font: 10px 'Segoe UI';
            }
            QComboBox QAbstractItemView {
                background: rgba(20,15,35,240);
                color: #dcd2ff;
                selection-background-color: rgba(180,0,255,120);
            }
        """)

    def _save(self):
        self.config["volume"]   = self.vol_spin.value()
        self.config["opacity"]  = self.opacity_spin.value()
        self.config["width"]    = self.w_spin.value()
        self.config["height"]   = self.h_spin.value()
        self.config["audio_device"] = self.dev_combo.currentData()
        self.settings_changed.emit(self.config)
        self.accept()

    def paintEvent(self, e):
        """Полупрозрачный фон диалога."""
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(self.rect().x(), self.rect().y(),
                            self.rect().width(), self.rect().height(), 12, 12)
        p.fillPath(path, QColor(12, 10, 20, 230))
        p.setPen(QPen(C_VIOLET, 1.5))
        p.setBrush(Qt.NoBrush)
        p.drawPath(path)


# ══════════════════════════════════════════════════════════════════════════════
#  Главное окно — NeonPlayerWindow
# ══════════════════════════════════════════════════════════════════════════════
class NeonPlayerWindow(QWidget):
    """
    Основной виджет плеера:
    - Без рамки, полупрозрачный, всегда поверх
    - Перетаскивается за любую пустую зону
    - Имеет все элементы управления
    """

    def __init__(self):
        super().__init__()
        self.config  = load_config()
        self.likes   = load_likes()
        self.tracks: List[TrackInfo] = []
        self.current_index = 0
        self._drag_pos: Optional[QPoint] = None
        self._loading  = False

        # Создаём VLC-плеер
        self.player = VLCPlayer(self.config.get("audio_device", ""))

        # Таймер обновления прогресс-бара
        self._update_timer = QTimer(self)
        self._update_timer.timeout.connect(self._update_progress)
        self._update_timer.start(500)

        # Таймер проверки конца трека
        self._end_timer = QTimer(self)
        self._end_timer.timeout.connect(self._check_ended)
        self._end_timer.start(1000)

        self._setup_window()
        self._build_ui()
        self._setup_tray()
        self._setup_hotkeys()
        self._restore_position()
        self.show()

        # Применяем Win32-флаги для прохождения кликов
        QTimer.singleShot(200, self._apply_win32_flags)

    # ── Настройка окна ──────────────────────────────────────────────────────
    def _setup_window(self):
        self.setWindowTitle(APP_NAME)
        self.setWindowFlags(
            Qt.FramelessWindowHint      |   # без рамки
            Qt.WindowStaysOnTopHint     |   # всегда поверх
            Qt.Tool                         # не в таскбаре (Linux/Win)
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.resize(self.config["width"], self.config["height"])
        self.setWindowOpacity(self.config["opacity"])

    def _apply_win32_flags(self):
        """Вызывается после show() чтобы hwnd был доступен."""
        if platform.system() == "Windows":
            hwnd = int(self.winId())
            set_windows_always_on_top_click_through(hwnd, True)

    def _restore_position(self):
        self.move(self.config.get("pos_x", 100),
                  self.config.get("pos_y", 100))

    # ── Построение UI ────────────────────────────────────────────────────────
    def _build_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(12, 12, 12, 12)
        main.setSpacing(8)

        # ── Заголовок (логотип + кнопки управления окном) ──
        header = QHBoxLayout()
        logo = QLabel("⬡ NEON PLAYER")
        logo.setStyleSheet(
            "color: #b400ff; font: bold 11px 'Segoe UI'; letter-spacing: 2px;"
        )
        header.addWidget(logo)
        header.addStretch()

        btn_settings = IconButton("⚙", C_CYAN, 24)
        btn_settings.clicked.connect(self._open_settings)
        btn_settings.setToolTip("Настройки")
        btn_minimize = IconButton("—", C_TEXT_DIM, 24)
        btn_minimize.clicked.connect(self._minimize_to_tray)
        btn_minimize.setToolTip("Свернуть в трей")
        btn_close = IconButton("✕", C_PINK, 24)
        btn_close.clicked.connect(self._quit)
        btn_close.setToolTip("Выйти")

        header.addWidget(btn_settings)
        header.addWidget(btn_minimize)
        header.addWidget(btn_close)
        main.addLayout(header)

        # ── Обложка + метаданные ──
        meta_row = QHBoxLayout()
        meta_row.setSpacing(10)

        self.artwork = TrackArtwork(80)
        meta_row.addWidget(self.artwork)

        meta_col = QVBoxLayout()
        meta_col.setSpacing(3)
        self.lbl_title = QLabel("NeonPlayer")
        self.lbl_title.setStyleSheet(
            "color: #dcd2ff; font: bold 11px 'Segoe UI'; "
        )
        self.lbl_title.setWordWrap(True)
        self.lbl_title.setMaximumWidth(200)

        self.lbl_artist = QLabel("Введите ссылку ниже")
        self.lbl_artist.setStyleSheet(
            "color: #7864b4; font: 10px 'Segoe UI';"
        )

        self.lbl_time = QLabel("0:00 / 0:00")
        self.lbl_time.setStyleSheet(
            "color: #7864b4; font: 9px 'Segoe UI';"
        )

        meta_col.addWidget(self.lbl_title)
        meta_col.addWidget(self.lbl_artist)
        meta_col.addStretch()
        meta_col.addWidget(self.lbl_time)
        meta_row.addLayout(meta_col)
        meta_row.addStretch()

        # Кнопка лайк
        self.btn_like = IconButton("♡", C_PINK, 30)
        self.btn_like.clicked.connect(self._toggle_like)
        self.btn_like.setToolTip("Лайк (сохранить)")
        meta_row.addWidget(self.btn_like, alignment=Qt.AlignTop)

        main.addLayout(meta_row)

        # ── Визуализатор ──
        self.visualizer = Visualizer()
        main.addWidget(self.visualizer)

        # ── Прогресс-бар ──
        self.progress_bar = GlassSlider(Qt.Horizontal)
        self.progress_bar.setRange(0, 1000)
        self.progress_bar.setValue(0)
        self.progress_bar.sliderMoved.connect(self._seek)
        self.progress_bar.setToolTip("Позиция трека")
        main.addWidget(self.progress_bar)

        # ── Кнопки управления ──
        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(6)
        ctrl_row.setAlignment(Qt.AlignCenter)

        self.btn_prev = IconButton("⏮", C_CYAN, 36)
        self.btn_prev.clicked.connect(self.prev_track)
        self.btn_prev.setToolTip("Предыдущий трек")

        self.btn_play = IconButton("▶", C_VIOLET, 42)
        self.btn_play.clicked.connect(self.toggle_play)
        self.btn_play.setToolTip("Play / Pause")

        self.btn_next = IconButton("⏭", C_CYAN, 36)
        self.btn_next.clicked.connect(self.next_track)
        self.btn_next.setToolTip("Следующий трек")

        ctrl_row.addWidget(self.btn_prev)
        ctrl_row.addWidget(self.btn_play)
        ctrl_row.addWidget(self.btn_next)
        main.addLayout(ctrl_row)

        # ── Громкость ──
        vol_row = QHBoxLayout()
        lbl_vol = QLabel("🔊")
        lbl_vol.setStyleSheet("color: #7864b4; font: 12px;")
        lbl_vol.setFixedWidth(22)
        self.vol_slider = GlassSlider(Qt.Horizontal)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(self.config["volume"])
        self.vol_slider.valueChanged.connect(self._on_volume_changed)
        self.vol_slider.setToolTip("Громкость")
        self.lbl_vol_val = QLabel(f"{self.config['volume']}%")
        self.lbl_vol_val.setFixedWidth(32)
        self.lbl_vol_val.setStyleSheet("color: #7864b4; font: 9px 'Segoe UI';")
        vol_row.addWidget(lbl_vol)
        vol_row.addWidget(self.vol_slider)
        vol_row.addWidget(self.lbl_vol_val)
        main.addLayout(vol_row)

        # ── Разделитель ──
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: rgba(180,0,255,80);")
        main.addWidget(sep)

        # ── Поле ввода URL ──
        url_lbl = QLabel("YouTube URL или плейлист:")
        url_lbl.setStyleSheet("color: #7864b4; font: 9px 'Segoe UI';")
        main.addWidget(url_lbl)

        url_row = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://youtu.be/...")
        self.url_input.returnPressed.connect(self._load_url)
        self.url_input.setStyleSheet("""
            QLineEdit {
                background: rgba(20,15,35,180);
                color: #dcd2ff;
                border: 1px solid rgba(180,0,255,150);
                border-radius: 6px;
                padding: 4px 10px;
                font: 10px 'Segoe UI';
            }
            QLineEdit:focus {
                border: 1px solid #b400ff;
            }
        """)
        btn_load = NeonButton("▶ Загрузить", C_VIOLET)
        btn_load.setFixedWidth(90)
        btn_load.clicked.connect(self._load_url)
        url_row.addWidget(self.url_input)
        url_row.addWidget(btn_load)
        main.addLayout(url_row)

        # ── Статусная строка ──
        self.lbl_status = QLabel("Готов к работе")
        self.lbl_status.setStyleSheet(
            "color: #00ffdc; font: italic 9px 'Segoe UI';"
        )
        self.lbl_status.setAlignment(Qt.AlignCenter)
        main.addWidget(self.lbl_status)

        # ── Трек-лист (метка с номером) ──
        self.lbl_tracklist = QLabel("")
        self.lbl_tracklist.setStyleSheet(
            "color: #7864b4; font: 9px 'Segoe UI';"
        )
        self.lbl_tracklist.setAlignment(Qt.AlignCenter)
        main.addWidget(self.lbl_tracklist)

        main.addStretch()

        # Применяем начальную громкость
        self.player.set_volume(self.config["volume"])

    # ── Системный трей ─────────────────────────────────────────────────────
    def _setup_tray(self):
        self.tray_icon = QSystemTrayIcon(self)

        # Иконка: создаём программно (фиолетовый кружок с нотой)
        pm = QPixmap(32, 32)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(QColor(180, 0, 255))
        p.setPen(Qt.NoPen)
        p.drawEllipse(2, 2, 28, 28)
        p.setPen(QColor(255, 255, 255))
        p.setFont(QFont("Segoe UI Symbol", 14, QFont.Bold))
        p.drawText(pm.rect(), Qt.AlignCenter, "♪")
        p.end()

        self.tray_icon.setIcon(QIcon(pm))
        self.tray_icon.setToolTip("NeonPlayer")
        self.tray_icon.activated.connect(self._on_tray_activated)

        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background: rgba(12,10,20,230);
                color: #dcd2ff;
                border: 1px solid #b400ff;
                font: 10px 'Segoe UI';
            }
            QMenu::item:selected {
                background: rgba(180,0,255,100);
            }
        """)
        act_show  = QAction("Показать", self)
        act_show.triggered.connect(self._show_from_tray)
        act_play  = QAction("▶ Play/Pause", self)
        act_play.triggered.connect(self.toggle_play)
        act_next  = QAction("⏭ Следующий", self)
        act_next.triggered.connect(self.next_track)
        act_quit  = QAction("✕ Выйти", self)
        act_quit.triggered.connect(self._quit)

        menu.addAction(act_show)
        menu.addSeparator()
        menu.addAction(act_play)
        menu.addAction(act_next)
        menu.addSeparator()
        menu.addAction(act_quit)

        self.tray_icon.setContextMenu(menu)
        self.tray_icon.show()

    def _minimize_to_tray(self):
        self.hide()
        self.tray_icon.showMessage(
            "NeonPlayer",
            "Свёрнут в трей. Нажмите на иконку для восстановления.",
            QSystemTrayIcon.Information, 2000
        )

    def _show_from_tray(self):
        self.show()
        self.raise_()
        self.activateWindow()
        QTimer.singleShot(100, self._apply_win32_flags)

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self._show_from_tray()

    # ── Горячие клавиши ─────────────────────────────────────────────────────
    def _setup_hotkeys(self):
        if kb is None:
            return
        try:
            kb.add_hotkey(
                self.config.get("hotkey_play", "media play pause"),
                self.toggle_play, suppress=False
            )
            kb.add_hotkey(
                self.config.get("hotkey_next", "media next track"),
                self.next_track, suppress=False
            )
            kb.add_hotkey(
                self.config.get("hotkey_prev", "media previous track"),
                self.prev_track, suppress=False
            )
            kb.add_hotkey(
                self.config.get("hotkey_vol_up", "ctrl+alt+up"),
                lambda: self._adjust_volume(+5), suppress=False
            )
            kb.add_hotkey(
                self.config.get("hotkey_vol_down", "ctrl+alt+down"),
                lambda: self._adjust_volume(-5), suppress=False
            )
            print("[Hotkeys] Глобальные горячие клавиши зарегистрированы")
        except Exception as e:
            print(f"[Hotkeys] Ошибка: {e}")

    def _adjust_volume(self, delta: int):
        new_vol = max(0, min(100, self.config["volume"] + delta))
        self.config["volume"] = new_vol
        self.player.set_volume(new_vol)
        # Обновляем слайдер из главного потока
        QTimer.singleShot(0, lambda: self.vol_slider.setValue(new_vol))

    # ── Загрузка треков ─────────────────────────────────────────────────────
    def _load_url(self):
        url = self.url_input.text().strip()
        if not url:
            self._set_status("⚠ Введите ссылку на YouTube", error=True)
            return
        if self._loading:
            self._set_status("⟳ Уже загружается...", error=False)
            return

        self._loading = True
        self._set_status("⟳ Получение информации о треках...")
        self.player.stop()

        self._yt_thread = YtDlpThread(url, self)
        self._yt_thread.tracks_ready.connect(self._on_tracks_ready)
        self._yt_thread.error_occurred.connect(self._on_load_error)
        self._yt_thread.progress.connect(self._set_status)
        self._yt_thread.start()

    def _on_tracks_ready(self, tracks: List[TrackInfo]):
        self._loading = False
        if not tracks:
            self._set_status("⚠ Треки не найдены", error=True)
            return

        self.tracks = tracks
        self.current_index = 0
        n = len(tracks)
        self._set_status(
            f"✓ Загружено треков: {n}. Воспроизведение..."
        )
        self._play_current()

    def _on_load_error(self, msg: str):
        self._loading = False
        self._set_status(f"✕ Ошибка: {msg}", error=True)
        print(f"[YtDlp] Ошибка: {msg}")

    # ── Управление воспроизведением ─────────────────────────────────────────
    def _play_current(self):
        if not self.tracks:
            return
        t = self.tracks[self.current_index]

        # Метаданные
        self.lbl_title.setText(t.title)
        self.lbl_artist.setText(t.artist)
        self._update_tracklist_label()
        self._update_like_button(t.webpage_url)

        # Обложка
        self.artwork.set_pixmap(QPixmap())  # сброс
        if t.thumbnail:
            self.artwork.set_pixmap(t.thumbnail)
        elif t.thumbnail_url:
            self._thumb_loader = ThumbnailLoader(
                t.thumbnail_url, t.video_id, self
            )
            self._thumb_loader.loaded.connect(self._on_thumbnail_loaded)
            self._thumb_loader.start()

        # Воспроизведение
        if t.url:
            self.player.play_url(t.url)
            self.player.set_volume(self.config["volume"])
            self.btn_play.setText("⏸")
            self.visualizer.set_playing(True)
        else:
            self._set_status("⚠ URL потока не найден", error=True)

    def _on_thumbnail_loaded(self, px: QPixmap, video_id: str):
        # Сохраняем в кэш
        if self.tracks and self.tracks[self.current_index].video_id == video_id:
            self.tracks[self.current_index].thumbnail = px
            self.artwork.set_pixmap(px)

    def toggle_play(self):
        if not self.tracks:
            return
        if self.player.is_playing():
            self.player.pause()
            self.btn_play.setText("▶")
            self.visualizer.set_playing(False)
        else:
            self.player.pause()   # VLC: pause() при остановленном = resume
            self.btn_play.setText("⏸")
            self.visualizer.set_playing(True)

    def next_track(self):
        if not self.tracks:
            return
        self.current_index = (self.current_index + 1) % len(self.tracks)
        self._play_current()

    def prev_track(self):
        if not self.tracks:
            return
        # Если прошло > 3 сек — возвращаемся к началу текущего
        if self.player.get_time() > 3000:
            self.player.set_position(0.0)
        else:
            self.current_index = (self.current_index - 1) % len(self.tracks)
            self._play_current()

    def _seek(self, value: int):
        """Перемотка по ползунку прогресса (0–1000)."""
        pos = value / 1000.0
        self.player.set_position(pos)

    # ── Лайки ───────────────────────────────────────────────────────────────
    def _toggle_like(self):
        if not self.tracks:
            return
        url = self.tracks[self.current_index].webpage_url
        if url in self.likes:
            self.likes.remove(url)
            self.btn_like.setText("♡")
        else:
            self.likes.append(url)
            self.btn_like.setText("♥")
        save_likes(self.likes)

    def _update_like_button(self, url: str):
        self.btn_like.setText("♥" if url in self.likes else "♡")

    # ── Таймеры обновления ───────────────────────────────────────────────────
    def _update_progress(self):
        if not self.tracks:
            return
        pos = self.player.get_position()
        if not self.progress_bar.isSliderDown():
            self.progress_bar.setValue(int(pos * 1000))
        cur_ms = self.player.get_time()
        total_ms = self.player.get_length()
        cur_s   = cur_ms // 1000
        total_s = total_ms // 1000

        def fmt(s):
            return f"{s // 60}:{s % 60:02d}"

        self.lbl_time.setText(f"{fmt(cur_s)} / {fmt(total_s)}")

    def _check_ended(self):
        """Автоматически переходит к следующему треку."""
        if self.tracks and self.player.ended():
            self.next_track()

    def _update_tracklist_label(self):
        n = len(self.tracks)
        if n > 1:
            self.lbl_tracklist.setText(
                f"Трек {self.current_index + 1} из {n}"
            )
        else:
            self.lbl_tracklist.setText("")

    # ── Настройки ────────────────────────────────────────────────────────────
    def _open_settings(self):
        devices = self.player.get_audio_devices()
        dlg = SettingsDialog(self.config, devices, self)
        dlg.settings_changed.connect(self._apply_settings)
        dlg.exec_()

    def _apply_settings(self, new_cfg: dict):
        self.config.update(new_cfg)
        save_config(self.config)
        self.setWindowOpacity(self.config["opacity"])
        self.resize(self.config["width"], self.config["height"])
        self.player.set_volume(self.config["volume"])
        self.vol_slider.setValue(self.config["volume"])
        self._set_status("✓ Настройки сохранены")

    # ── Утилиты UI ─────────────────────────────────────────────────────────
    def _on_volume_changed(self, val: int):
        self.config["volume"] = val
        self.player.set_volume(val)
        self.lbl_vol_val.setText(f"{val}%")

    def _set_status(self, msg: str, error: bool = False):
        color = "#ff0066" if error else "#00ffdc"
        self.lbl_status.setStyleSheet(
            f"color: {color}; font: italic 9px 'Segoe UI';"
        )
        self.lbl_status.setText(msg)

    # ── Закрытие / выход ────────────────────────────────────────────────────
    def _quit(self):
        self._save_position()
        if kb is not None:
            try:
                kb.unhook_all()
            except Exception:
                pass
        self.player.stop()
        self.tray_icon.hide()
        QApplication.quit()

    def _save_position(self):
        pos = self.pos()
        self.config["pos_x"] = pos.x()
        self.config["pos_y"] = pos.y()
        save_config(self.config)

    def closeEvent(self, e):
        e.ignore()
        self._minimize_to_tray()

    # ── Перетаскивание окна ──────────────────────────────────────────────────
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            # Перетаскивание только если не кликнули по интерактивному виджету
            child = self.childAt(e.pos())
            interactive = (QPushButton, QSlider, QLineEdit, QComboBox)
            if child is None or not isinstance(child, interactive):
                self._drag_pos = e.globalPos() - self.frameGeometry().topLeft()
                e.accept()

    def mouseMoveEvent(self, e):
        if self._drag_pos is not None and e.buttons() & Qt.LeftButton:
            self.move(e.globalPos() - self._drag_pos)
            e.accept()

    def mouseReleaseEvent(self, e):
        self._drag_pos = None

    # ── Отрисовка фона (стекломорфизм + рамка) ──────────────────────────────
    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = self.rect()

        # Основной тёмный фон
        path = QPainterPath()
        path.addRoundedRect(r.x(), r.y(), r.width(), r.height(), 14, 14)
        p.fillPath(path, C_BG)

        # Стеклянный блик сверху
        glare = QLinearGradient(0, 0, 0, r.height() // 3)
        glare.setColorAt(0.0, QColor(255, 255, 255, 22))
        glare.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.fillPath(path, glare)

        # Неоновая рамка — градиент фиолетовый→бирюзовый
        border_grad = QLinearGradient(0, 0, r.width(), r.height())
        border_grad.setColorAt(0.0, C_VIOLET)
        border_grad.setColorAt(0.5, C_PINK)
        border_grad.setColorAt(1.0, C_CYAN)
        pen = QPen(QBrush(border_grad), 1.5)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(
            r.adjusted(1, 1, -1, -1), 14, 14
        )


# ══════════════════════════════════════════════════════════════════════════════
#  Точка входа
# ══════════════════════════════════════════════════════════════════════════════
def check_dependencies() -> bool:
    """Проверяет наличие обязательных зависимостей."""
    missing = []
    if vlc is None:
        missing.append("python-vlc")
    if yt_dlp is None:
        missing.append("yt-dlp")
    if missing:
        print(f"[ERROR] Не установлены: {', '.join(missing)}")
        print("Выполните: pip install " + " ".join(missing))
        return False
    return True


def main():
    # На Windows включаем DPI awareness для чёткого рендеринга
    if platform.system() == "Windows":
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass

    # Обязательные зависимости
    if not check_dependencies():
        sys.exit(1)

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(VERSION)

    # Предотвращаем закрытие при закрытии всех окон
    app.setQuitOnLastWindowClosed(False)

    # Встраиваем шрифт Segoe UI Symbol если он есть
    QFontDatabase.addApplicationFont(":/fonts/segoe")

    window = NeonPlayerWindow()

    print(f"""
╔═══════════════════════════════════════╗
║  NeonPlayer v{VERSION} запущен            ║
║  Конфиг: {str(CONFIG_DIR):<29} ║
╚═══════════════════════════════════════╝
  Горячие клавиши:
    Media Play/Pause  — play/pause
    Media Next/Prev   — следующий/пред.
    Ctrl+Alt+↑/↓      — громкость
    Двойной клик трей — показать окно
""")

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
