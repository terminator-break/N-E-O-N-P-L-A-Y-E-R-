[README (3).md](https://github.com/user-attachments/files/28831883/README.3.md)
<div align="center">

```
╔══════════════════════════════════════════════════════╗
║   ⬡  N E O N  P L A Y E R  ⬡                        ║
║   YouTube Audio Overlay · Cyberpunk Edition          ║
╚══════════════════════════════════════════════════════╝
```

**Always-on-top оверлей для воспроизведения музыки с YouTube.**  
Работает поверх полноэкранных игр. Не мешает. Звучит.

[![Python](https://img.shields.io/badge/Python-3.8%2B-blueviolet?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![PyQt5](https://img.shields.io/badge/PyQt5-5.15%2B-cyan?style=flat-square)](https://pypi.org/project/PyQt5/)
[![yt-dlp](https://img.shields.io/badge/yt--dlp-latest-ff0080?style=flat-square)](https://github.com/yt-dlp/yt-dlp)
[![VLC](https://img.shields.io/badge/python--vlc-3.0%2B-blueviolet?style=flat-square)](https://pypi.org/project/python-vlc/)
[![License](https://img.shields.io/badge/license-MIT-00ffdc?style=flat-square)](LICENSE)

</div>

---

## ✦ Что это

NeonPlayer — компактный полупрозрачный плеер, который висит поверх всего, включая полноэкранные DirectX/OpenGL-игры. Вставляете ссылку на видео или плейлист YouTube — приложение тянет только аудиопоток через `yt-dlp` и воспроизводит через `VLC`. Никакого видео, никакого скачивания.

Интерфейс в стиле **киберпанк / стекломорфизм**: тёмный полупрозрачный фон, неоновые обводки с градиентом фиолетовый→розовый→бирюзовый, светящиеся кнопки.

---

## ✦ Возможности

| Функция | Описание |
|---|---|
| 🎵 **Аудио без видео** | Только аудиопоток — `yt-dlp` + `--no-video` в VLC |
| 📋 **Плейлисты** | Автоматическое разворачивание, навигация по трекам |
| 🖼 **Обложки** | Загрузка thumbnail с YouTube, кэширование в памяти |
| ⬡ **Всегда поверх** | `WindowStaysOnTopHint` + Win32 `HWND_TOPMOST` для fullscreen-игр |
| 🖱 **Клики сквозь окно** | `WS_EX_TRANSPARENT` — пустые зоны не перехватывают мышь |
| 🎛 **Визуализатор** | 16 анимированных столбиков с lerp-сглаживанием |
| ⌨️ **Глобальные хоткеи** | Media-клавиши + собственные комбинации, работают в фоне |
| ❤️ **Лайки** | Сохраняются локально в `~/.neonplayer/likes.json` |
| 🔊 **Аудиоустройства** | Выбор выхода через настройки VLC |
| 🗂 **Трей** | Сворачивание в системный трей, восстановление двойным кликом |
| ⚙️ **Настройки** | Громкость, прозрачность, размер, устройство вывода |

---

## ✦ Скриншот

```
┌─────────────────────────────────┐  ← полупрозрачное окно, без рамки
│ ⬡ NEON PLAYER          ⚙ — ✕  │  ← перетаскивается за любую зону
│                                 │
│  ┌──────┐  Название трека       │
│  │  ♪   │  Исполнитель          │  ← обложка 80×80
│  └──────┘  0:42 / 3:55      ♥  │
│                                 │
│  ▐▌▐▌▐▌▐▌▐▌▐▌▐▌▐▌▐▌▐▌▐▌▐▌▐▌▐▌  │  ← визуализатор
│  ████████████░░░░░░░░░░░░░░░░░  │  ← прогресс-бар
│                                 │
│       ⏮   ⏸   ⏭               │  ← prev / play / next
│  🔊 ████████████░░░  72%        │  ← громкость
│  ─────────────────────────────  │
│  YouTube URL или плейлист:      │
│  [ https://youtu.be/...      ]  │
│  [ ▶ Загрузить ]                │
│  ✓ Воспроизведение              │
│  Трек 3 из 12                   │
└─────────────────────────────────┘
```

> Неоновая рамка с градиентом `#b400ff → #ff0080 → #00ffdc`

---

## ✦ Установка

### Требования

- **Python 3.8+**
- **VLC Media Player** — должен быть установлен в системе:
  - Windows: [videolan.org/vlc](https://www.videolan.org/vlc/)
  - Linux: `sudo apt install vlc` / `sudo dnf install vlc`
  - macOS: `brew install vlc`

### Шаги

```bash
# 1. Клонируем репозиторий
git clone https://github.com/terminator-break/N-E-O-N-P-L-A-Y-E-R-
cd neonplayer

# 2. (Опционально) создаём виртуальное окружение
python -m venv .venv
source .venv/bin/activate       # Linux/macOS
.venv\Scripts\activate          # Windows

# 3. Устанавливаем зависимости
pip install -r requirements.txt

# 4. Запускаем
python main.py
```

### requirements.txt

```
PyQt5>=5.15.0
yt-dlp>=2024.1.0
python-vlc>=3.0.18122
keyboard>=0.13.5
requests>=2.31.0
Pillow>=10.0.0
```

---

## ✦ Горячие клавиши

Работают **глобально** — даже когда NeonPlayer не в фокусе (в игре, в браузере, где угодно).

| Клавиша | Действие |
|---|---|
| `Media Play/Pause` | Play / Pause |
| `Media Next Track` | Следующий трек |
| `Media Previous Track` | Предыдущий трек |
| `Ctrl + Alt + ↑` | Громкость +5% |
| `Ctrl + Alt + ↓` | Громкость −5% |
| Двойной клик по трею | Показать/скрыть окно |

Все комбинации можно изменить в `~/.neonplayer/config.json`:

```json
{
  "hotkey_play":      "media play pause",
  "hotkey_next":      "media next track",
  "hotkey_prev":      "media previous track",
  "hotkey_vol_up":    "ctrl+alt+up",
  "hotkey_vol_down":  "ctrl+alt+down"
}
```

---

## ✦ Настройки

Открываются кнопкой **⚙** в шапке окна.

| Параметр | Описание | По умолчанию |
|---|---|---|
| Громкость | 0–100% | 70 |
| Прозрачность | 0.30–1.00 | 0.88 |
| Ширина окна | 260–600 px | 340 |
| Высота окна | 360–800 px | 480 |
| Аудиоустройство | Список устройств VLC | По умолчанию |

Конфиг сохраняется в `~/.neonplayer/config.json`. Позиция окна запоминается автоматически при выходе.

---

## ✦ Платформы

| ОС | Статус | Особенности |
|---|---|---|
| **Windows 10/11** | ✅ Полная поддержка | Win32 `HWND_TOPMOST` + `WS_EX_TRANSPARENT` для fullscreen-игр |
| **Linux (X11)** | ✅ Поддерживается | Для глобальных хоткеев нужны root-права или `udev` правило |
| **Linux (Wayland)** | ⚠️ Частичная | Always-on-top работает, глобальные хоткеи — нет |
| **macOS** | ⚠️ Частичная | Протестировано с ограничениями; Accessibility для хоткеев |

### Linux: глобальные хоткеи без sudo

```bash
# Добавляем пользователя в группу input
sudo usermod -aG input $USER
# Создаём udev правило
echo 'KERNEL=="event*", GROUP="input", MODE="0664"' | \
  sudo tee /etc/udev/rules.d/99-input.rules
sudo udevadm control --reload-rules
# Перелогиниться
```

### Windows: запуск поверх fullscreen-игр

На некоторых играх с эксклюзивным fullscreen (`D3D Exclusive`) окно может быть перекрыто. Решение — переключить игру в **Borderless Windowed** режим. Большинство современных игр поддерживают его в настройках графики.

---

## ✦ Структура проекта

```
neonplayer/
├── main.py              # Весь код приложения
├── requirements.txt     # Python-зависимости
├── README.md
└── ~/.neonplayer/       # Пользовательские данные (создаётся автоматически)
    ├── config.json      # Настройки
    └── likes.json       # Лайкнутые треки (URL)
```

### Ключевые классы

```
NeonPlayerWindow         Главное окно — UI, перетаскивание, координация
├── VLCPlayer            Обёртка python-vlc, только аудио
├── YtDlpThread          QThread: извлечение URL и метаданных без скачивания
├── ThumbnailLoader      QThread: фоновая загрузка обложек
├── Visualizer           QWidget: анимированные столбики (псевдо-спектр)
├── TrackArtwork         QLabel: обложка с закруглёнными углами и свечением
├── NeonButton           QPushButton: неоновый градиент + glow-эффект
├── IconButton           QPushButton: символьная иконка с подсветкой
├── GlassSlider          QSlider: стекломорфный стиль
└── SettingsDialog       QDialog: настройки приложения
```

---

## ✦ Как это работает

```
Пользователь вводит URL
        │
        ▼
  YtDlpThread (фон)
  yt-dlp extract_info()
  → список TrackInfo
  → прямые URL аудиопотоков
        │
        ▼
  VLCPlayer.play_url()
  vlc.Instance(--no-video)
  → аудио на выбранное устройство
        │
        ▼
  QTimer (500ms)
  → обновление прогресс-бара
  → обновление времени
  → проверка окончания трека
  → авто-переход к следующему
```

---

## ✦ Частые вопросы

**Q: Аудио не воспроизводится**  
A: Убедитесь что VLC установлен в системе (не только python-vlc). Проверьте `python -c "import vlc; print(vlc.__file__)"`.

**Q: yt-dlp возвращает ошибку "Sign in to confirm your age"**  
A: YouTube требует авторизации. Используйте `yt-dlp --cookies-from-browser chrome` или передайте cookies файл.

**Q: Окно не отображается поверх игры**  
A: Переключите игру в Borderless Windowed. Эксклюзивный fullscreen захватывает весь вывод GPU.

**Q: Глобальные хоткеи не работают на Linux**  
A: Нужны права на `/dev/input/event*`. Смотрите раздел «Linux: глобальные хоткеи без sudo».

**Q: Как убрать окно с экрана временно**  
A: Нажмите `—` (свернуть в трей) или кнопку `✕` в трее.

---

## ✦ Зависимости

| Пакет | Зачем |
|---|---|
| `PyQt5` | GUI, рендеринг, системный трей |
| `yt-dlp` | Извлечение аудио-URL с YouTube без скачивания |
| `python-vlc` | Воспроизведение аудиопотока |
| `keyboard` | Глобальные горячие клавиши |
| `Pillow` | Обработка изображений обложек |
| `requests` | HTTP-запросы (опционально) |

---

## ✦ Лицензия

MIT — делайте что хотите, упоминание приветствуется.

---

<div align="center">

```
  ⬡ made with PyQt5, yt-dlp and too much neon ⬡
```

</div>
