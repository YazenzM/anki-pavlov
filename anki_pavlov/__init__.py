"""Pavlov: reward yourself with a random photo from your own collection after answering a card."""

from __future__ import annotations

import base64
import json
import os
import random
import re
from concurrent.futures import Future

from aqt import gui_hooks, mw
from aqt.operations import QueryOp
from aqt.qt import (
    QBuffer,
    QByteArray,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QImage,
    QImageReader,
    QIODevice,
    QLineEdit,
    QMenu,
    QPushButton,
    QSpinBox,
    Qt,
)
from aqt.utils import askUser, qconnect, showInfo, showWarning, tooltip

PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}

LAYOUTS = {
    "bottom-right": "Bottom-right corner",
    "bottom-left": "Bottom-left corner",
    "top-right": "Top-right corner",
    "top-left": "Top-left corner",
    "side": "Panel on the right",
    "fullscreen": "Full screen",
}
DEFAULT_LAYOUT = "bottom-right"
BUTTON_NAMES = ("Again", "Hard", "Good", "Easy")

REWARD_MODES = {
    "every": "After each right answer",
    "streak": "After a streak of right answers (a miss resets it)",
    "count": "After a number of right answers (misses don't reset it)",
}
DEFAULT_MODE = "every"

# Phones and tablets can't run add-ons, so for them photos are copied into Anki's media folder as
# _pavlov_0001.jpg, _pavlov_0002.jpg, ... and a script on the back of every card picks one at random.
# The leading underscore stops Check Media from reporting the files as unused.
MOBILE_PREFIX = "_pavlov_"
SNIPPET_START = "<!-- pavlov-start -->"
SNIPPET_END = "<!-- pavlov-end -->"
SNIPPET_RE = re.compile(re.escape(SNIPPET_START) + ".*?" + re.escape(SNIPPET_END), re.DOTALL)

# Photos not yet shown in the current cycle, so nothing repeats until every photo has been seen.
_queue: list[str] = []
_queue_source: tuple[str, bool] | None = None
_loading = False
_warned_no_folder = False

# Right answers in a row, and in total, since Anki started.
_streak = 0
_right_count = 0

# Plain ES5 so it also runs in the older web views used by phone and tablet apps.
# The side panel pads the page so the card reflows beside it instead of underneath.
_OVERLAY_JS = """(function (src, ms, layout, size) {
    var old = document.getElementById("pavlov-reward");
    if (old) old.parentNode.removeChild(old);
    var root = document.documentElement;
    var box = document.createElement("div");
    var img = document.createElement("img");
    var boxCss = "position:fixed;z-index:99999;opacity:0;transition:opacity .25s;cursor:pointer;";
    var imgCss = "display:block;border-radius:12px;box-shadow:0 8px 40px rgba(0,0,0,.6);";
    if (layout === "fullscreen") {
        boxCss += "top:0;right:0;bottom:0;left:0;display:flex;align-items:center;justify-content:center;background:rgba(0,0,0,.8)";
        imgCss += "max-width:90vw;max-height:90vh";
    } else if (layout === "side") {
        boxCss += "top:0;right:0;bottom:0;width:" + size + "vw;display:flex;align-items:center;justify-content:center";
        imgCss += "max-width:calc(100%% - 24px);max-height:calc(100%% - 24px)";
    } else {
        var edges = layout.split("-");
        boxCss += edges[0] + ":16px;" + edges[1] + ":16px";
        imgCss += "max-width:" + size + "vw;max-height:" + size + "vh";
    }
    box.id = "pavlov-reward";
    box.style.cssText = boxCss;
    img.style.cssText = imgCss;
    img.onerror = close;
    img.src = src;
    box.appendChild(img);
    document.body.appendChild(box);
    root.style.paddingRight = layout === "side" ? size + "vw" : "";
    void box.offsetWidth;
    box.style.opacity = "1";
    function close() {
        if (document.getElementById("pavlov-reward") !== box) return;
        box.style.opacity = "0";
        setTimeout(function () {
            if (box.parentNode) box.parentNode.removeChild(box);
            if (!document.getElementById("pavlov-reward")) root.style.paddingRight = "";
        }, 250);
    }
    box.addEventListener("click", close);
    if (ms > 0) setTimeout(close, ms);
})(%s, %d, %s, %d);"""

_MOBILE_JS = """(function () {
    if (Math.random() >= %s) return;
    var n = String(1 + Math.floor(Math.random() * %d));
    while (n.length < 4) n = "0" + n;
    %s
})();"""

_HIDE_JS = """(function () {
    document.getElementById("pavlov-reward")?.remove();
    document.documentElement.style.paddingRight = "";
})();"""

# A badge with the given text pops up at the bottom of the screen with a burst of confetti behind it.
# Called as _FLAIR_JS + "(text);". Desktop only, since phones and tablets can't tell right from wrong.
_FLAIR_JS = """(function (text) {
    document.getElementById("pavlov-flair")?.remove();
    var layer = document.createElement("div");
    layer.id = "pavlov-flair";
    layer.style.cssText = "position:fixed;left:50%;bottom:32px;z-index:100000;pointer-events:none";
    var badge = document.createElement("div");
    badge.textContent = text;
    badge.style.cssText = "transform:translateX(-50%) scale(.6);opacity:0;transition:transform .3s cubic-bezier(.2,1.6,.4,1),opacity .3s;" +
        "padding:6px 14px;border-radius:999px;background:#16a34a;color:#fff;font:600 15px system-ui,sans-serif;" +
        "white-space:nowrap;box-shadow:0 4px 14px rgba(0,0,0,.25)";
    layer.appendChild(badge);
    var calm = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    var colors = ["#f43f5e", "#f59e0b", "#10b981", "#3b82f6", "#a855f7"];
    var bits = [];
    for (var i = 0; !calm && i < 24; i++) {
        var bit = document.createElement("div");
        bit.style.cssText = "position:absolute;left:-4px;top:0;width:8px;height:8px;border-radius:2px;background:" +
            colors[i % colors.length] + ";transition:transform .9s cubic-bezier(.1,.8,.3,1),opacity .9s ease-in";
        layer.appendChild(bit);
        bits.push(bit);
    }
    document.body.appendChild(layer);
    void layer.offsetWidth;
    badge.style.transform = "translateX(-50%) scale(1)";
    badge.style.opacity = "1";
    bits.forEach(function (bit) {
        var angle = Math.PI * (0.1 + 0.8 * Math.random());
        var distance = 60 + 100 * Math.random();
        bit.style.transform = "translate(" + Math.cos(angle) * distance + "px," + -Math.sin(angle) * distance + "px) " +
            "rotate(" + 720 * Math.random() + "deg)";
        bit.style.opacity = "0";
    });
    setTimeout(function () { badge.style.opacity = "0"; }, 1300);
    setTimeout(function () { layer.remove(); }, 1700);
})"""


def _config() -> dict:
    return mw.addonManager.getConfig(__name__) or {}


def _photo_folder(config: dict) -> str | None:
    folder = config.get("photo_folder", "")
    return folder if folder and os.path.isdir(folder) else None


def _layout(config: dict) -> str:
    layout = config.get("layout", DEFAULT_LAYOUT)
    return layout if layout in LAYOUTS else DEFAULT_LAYOUT


def _mode(config: dict) -> str:
    mode = config.get("reward_mode", DEFAULT_MODE)
    return mode if mode in REWARD_MODES else DEFAULT_MODE


def _overlay_js(src: str, config: dict) -> str:
    """JS that shows the photo at src, which must itself be a JS expression."""
    size = max(10, min(int(config.get("photo_size", 30)), 90))
    duration_ms = int(config.get("display_seconds", 20) * 1000)
    return _OVERLAY_JS % (src, duration_ms, json.dumps(_layout(config)), size)


def _scan(folder: str, recursive: bool) -> list[str]:
    paths = []
    for root, _dirs, files in os.walk(folder):
        for name in files:
            if os.path.splitext(name)[1].lower() in PHOTO_EXTENSIONS:
                paths.append(os.path.join(root, name))
        if not recursive:
            break
    return paths


def _next_photo(folder: str, recursive: bool) -> str | None:
    global _queue, _queue_source
    # Rescan when the folder settings change or a cycle ends, which also picks up newly added photos.
    if _queue_source != (folder, recursive) or not _queue:
        _queue = _scan(folder, recursive)
        random.shuffle(_queue)
        _queue_source = (folder, recursive)
    return _queue.pop() if _queue else None


def _load_image(path: str, max_size: int) -> QImage | None:
    reader = QImageReader(path)
    reader.setAutoTransform(True)  # honour EXIF rotation from phone cameras
    size = reader.size()
    if size.isValid() and (size.width() > max_size or size.height() > max_size):
        size.scale(max_size, max_size, Qt.AspectRatioMode.KeepAspectRatio)
        reader.setScaledSize(size)
    image = reader.read()
    return None if image.isNull() else image


def _encode(image: QImage, fmt: str) -> bytes:
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, fmt, 85)
    buffer.close()
    return bytes(data)


def _pick_and_load(folder: str, recursive: bool, max_size: int) -> str | None:
    # Skip past a few unreadable files before giving up.
    for _ in range(5):
        path = _next_photo(folder, recursive)
        if path is None:
            return None
        image = _load_image(path, max_size)
        if image is not None:
            fmt, mime = ("PNG", "image/png") if image.hasAlphaChannel() else ("JPEG", "image/jpeg")
            return f"data:{mime};base64,{base64.b64encode(_encode(image, fmt)).decode()}"
    return None


def _on_answer(reviewer, card, ease: int) -> None:
    global _streak, _right_count
    config = _config()
    if ease not in config.get("reward_on_buttons", [2, 3, 4]):
        _streak = 0
        return
    _streak += 1
    _right_count += 1

    mode = _mode(config)
    needed = max(1, int(config.get("answers_needed", 5)))
    if config.get("flair", True):
        if mode == "count":
            text = f"✓ {(_right_count - 1) % needed + 1} of {needed}"
        else:
            text = f"🔥 {_streak} in a row" if _streak > 1 else "✓"
        mw.reviewer.web.eval(f"{_FLAIR_JS}({json.dumps(text)});")

    if mode == "streak":
        earned = _streak % needed == 0
    elif mode == "count":
        earned = _right_count % needed == 0
    else:
        earned = random.random() < config.get("chance", 1.0)
    if earned:
        _show_photo(config)


def _show_photo(config: dict) -> None:
    global _loading, _warned_no_folder
    folder = _photo_folder(config)
    if not folder:
        if not _warned_no_folder:
            tooltip("Pavlov: choose a photo folder via Tools > Pavlov > Settings")
            _warned_no_folder = True
        return
    if _loading:
        return

    _loading = True
    recursive = config.get("include_subfolders", True)
    max_size = config.get("max_image_size", 1600)

    # Loading runs off the main thread so slow drives (e.g. Google Drive streaming) don't freeze reviews.
    def on_done(future: Future) -> None:
        global _loading
        _loading = False
        try:
            uri = future.result()
        except Exception as err:
            tooltip(f"Pavlov: couldn't load a photo ({err})")
            return
        if uri is None:
            tooltip(f"Pavlov: no photos found in {folder}")
            return
        if mw.state == "review":
            mw.reviewer.web.eval(_overlay_js(json.dumps(uri), config))

    mw.taskman.run_in_background(lambda: _pick_and_load(folder, recursive, max_size), on_done)


def _on_show_answer(card) -> None:
    # A full-screen photo covers the card, so it makes way for the answer. Other layouts wait for their timer.
    if _layout(_config()) == "fullscreen":
        mw.reviewer.web.eval(_HIDE_JS)


def _on_card_will_show(text: str, card, kind: str) -> str:
    # The desktop add-on rewards answers itself, so the phone/tablet script is dropped from desktop reviews.
    # Previews keep it, which makes them a handy way to check the phone/tablet version.
    if kind.startswith("review"):
        return SNIPPET_RE.sub("", text)
    return text


class SettingsDialog(QDialog):
    def __init__(self) -> None:
        super().__init__(mw)
        self.setWindowTitle("Pavlov Settings")
        config = _config()

        self.folder = QLineEdit(config.get("photo_folder", ""))
        browse = QPushButton("Browse...")
        qconnect(browse.clicked, self._browse)
        folder_row = QHBoxLayout()
        folder_row.addWidget(self.folder)
        folder_row.addWidget(browse)

        self.subfolders = QCheckBox("Include subfolders")
        self.subfolders.setChecked(config.get("include_subfolders", True))

        self.mode_choice = QComboBox()
        for key, label in REWARD_MODES.items():
            self.mode_choice.addItem(label, key)
        self.mode_choice.setCurrentIndex(self.mode_choice.findData(_mode(config)))
        qconnect(self.mode_choice.currentIndexChanged, self._update_enabled)

        self.needed = QSpinBox()
        self.needed.setRange(2, 100)
        self.needed.setValue(int(config.get("answers_needed", 5)))

        self.layout_choice = QComboBox()
        for key, label in LAYOUTS.items():
            self.layout_choice.addItem(label, key)
        self.layout_choice.setCurrentIndex(self.layout_choice.findData(_layout(config)))
        qconnect(self.layout_choice.currentIndexChanged, self._update_enabled)

        self.photo_size = QSpinBox()
        self.photo_size.setRange(10, 90)
        self.photo_size.setSuffix("% of the window")
        self.photo_size.setValue(int(config.get("photo_size", 30)))

        self.seconds = QSpinBox()
        self.seconds.setRange(0, 600)
        self.seconds.setSuffix(" seconds")
        self.seconds.setSpecialValueText("Until clicked")
        self.seconds.setValue(int(config.get("display_seconds", 20)))

        self.chance = QSpinBox()
        self.chance.setRange(0, 100)
        self.chance.setSuffix("%")
        self.chance.setValue(round(config.get("chance", 1.0) * 100))

        rewarded = config.get("reward_on_buttons", [2, 3, 4])
        self.answer_boxes = []
        answers_row = QHBoxLayout()
        for ease, name in enumerate(BUTTON_NAMES, start=1):
            box = QCheckBox(name)
            box.setChecked(ease in rewarded)
            self.answer_boxes.append(box)
            answers_row.addWidget(box)

        self.flair = QCheckBox("Celebrate right answers with confetti and a streak counter")
        self.flair.setChecked(config.get("flair", True))

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        qconnect(buttons.accepted, self.accept)
        qconnect(buttons.rejected, self.reject)

        form = QFormLayout(self)
        form.addRow("Photo folder:", folder_row)
        form.addRow("", self.subfolders)
        form.addRow("Show a photo:", self.mode_choice)
        form.addRow("Right answers needed:", self.needed)
        form.addRow("Chance of a photo:", self.chance)
        form.addRow("Count as right:", answers_row)
        form.addRow("Layout:", self.layout_choice)
        form.addRow("Photo size:", self.photo_size)
        form.addRow("Show each photo for:", self.seconds)
        form.addRow("", self.flair)
        form.addRow(buttons)
        self._update_enabled()

    def _browse(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Choose your reward photo folder", self.folder.text())
        if folder:
            self.folder.setText(folder)

    def _update_enabled(self) -> None:
        every = self.mode_choice.currentData() == "every"
        self.needed.setEnabled(not every)
        self.chance.setEnabled(every)
        self.photo_size.setEnabled(self.layout_choice.currentData() != "fullscreen")

    def accept(self) -> None:
        config = _config()
        config.update(
            photo_folder=self.folder.text().strip(),
            include_subfolders=self.subfolders.isChecked(),
            reward_mode=self.mode_choice.currentData(),
            answers_needed=self.needed.value(),
            flair=self.flair.isChecked(),
            layout=self.layout_choice.currentData(),
            photo_size=self.photo_size.value(),
            display_seconds=self.seconds.value(),
            chance=self.chance.value() / 100,
            reward_on_buttons=[ease for ease, box in enumerate(self.answer_boxes, start=1) if box.isChecked()],
        )
        mw.addonManager.writeConfig(__name__, config)
        _refresh_mobile_snippet(config)
        super().accept()


def _open_settings() -> None:
    SettingsDialog().exec()


def _mobile_name(number: int) -> str:
    return f"{MOBILE_PREFIX}{number:04d}.jpg"


def _mobile_snippet(count: int, config: dict) -> str:
    # Phones and tablets can't see which button was pressed, so streak and count modes become matching odds:
    # "every 5 right answers" shows a photo on about 1 card in 5.
    if _mode(config) == "every":
        chance = config.get("chance", 1.0)
    else:
        chance = 1 / max(1, int(config.get("answers_needed", 5)))
    src = json.dumps(MOBILE_PREFIX) + ' + n + ".jpg"'
    js = _MOBILE_JS % (chance, count, _overlay_js(src, config))
    return f"{SNIPPET_START}\n<script>\n{js}\n</script>\n{SNIPPET_END}"


def _set_snippet(snippet: str | None) -> None:
    """Put the snippet at the end of every card type's back template, or remove it when snippet is None."""
    for entry in mw.col.models.all_names_and_ids():
        notetype = mw.col.models.get(entry.id)
        changed = False
        for template in notetype["tmpls"]:
            afmt = SNIPPET_RE.sub("", template["afmt"])
            if snippet:
                afmt = afmt.rstrip() + "\n\n" + snippet
            elif afmt != template["afmt"]:
                afmt = afmt.rstrip()
            if afmt != template["afmt"]:
                template["afmt"] = afmt
                changed = True
        if changed:
            mw.col.models.update_dict(notetype)


def _refresh_mobile_snippet(config: dict) -> None:
    """Bring the phone/tablet script in line with new settings, if photos have been copied for it."""
    if mw.col is None:
        return
    count = sum(1 for name in os.listdir(mw.col.media.dir()) if name.startswith(MOBILE_PREFIX))
    if count:
        _set_snippet(_mobile_snippet(count, config))


def _export_photos(folder: str, recursive: bool, count: int, max_size: int, media_dir: str) -> int:
    paths = _scan(folder, recursive)
    random.shuffle(paths)
    kept: set[str] = set()
    for path in paths:
        if len(kept) == count:
            break
        image = _load_image(path, max_size)
        if image is None:
            continue
        name = _mobile_name(len(kept) + 1)
        target = os.path.join(media_dir, name)
        # Delete before writing: Anki only rescans the media folder for changes when the folder itself changes.
        if os.path.exists(target):
            os.remove(target)
        with open(target, "wb") as file:
            file.write(_encode(image, "JPEG"))
        kept.add(name)
        done = len(kept)
        mw.taskman.run_on_main(
            lambda: mw.progress.update(label=f"Copying photos for phone/tablet ({done}/{count})...")
        )

    # Clear out photos left over from an earlier, larger copy.
    for name in os.listdir(media_dir):
        if name.startswith(MOBILE_PREFIX) and name not in kept:
            os.remove(os.path.join(media_dir, name))
    return len(kept)


def _copy_to_mobile() -> None:
    config = _config()
    folder = _photo_folder(config)
    if not folder:
        showWarning("Choose a photo folder first via Tools > Pavlov > Settings.")
        return

    count = min(config.get("mobile_photo_count", 100), 9999)
    if not askUser(
        f"Copy {count} random photos into Anki so they sync to your phone or tablet?\n\n"
        "This also adds a small script to the back of every card type that shows one of them "
        "when you reveal an answer on a phone or tablet. "
        "Use Tools > Pavlov > Remove from Phone/Tablet to undo it."
    ):
        return

    recursive = config.get("include_subfolders", True)
    max_size = config.get("max_image_size", 1600)
    media_dir = mw.col.media.dir()

    def on_success(written: int) -> None:
        if written == 0:
            showWarning(f"No photos found in {folder}")
            return
        _set_snippet(_mobile_snippet(written, config))
        showInfo(
            f"Copied {written} photos.\n\n"
            "Now sync Anki on this computer, then sync on your phone or tablet. "
            "Run this again any time for a fresh batch of photos."
        )

    QueryOp(
        parent=mw,
        op=lambda col: _export_photos(folder, recursive, count, max_size, media_dir),
        success=on_success,
    ).with_progress("Copying photos for phone/tablet...").run_in_background()


def _remove_from_mobile() -> None:
    if not askUser("Remove Pavlov's photos and card script for phones and tablets?"):
        return
    _set_snippet(None)
    media_dir = mw.col.media.dir()
    for name in os.listdir(media_dir):
        if name.startswith(MOBILE_PREFIX):
            os.remove(os.path.join(media_dir, name))
    tooltip("Pavlov removed from phone/tablet. Sync Anki to apply it to your other devices.")


gui_hooks.reviewer_did_answer_card.append(_on_answer)
gui_hooks.reviewer_did_show_answer.append(_on_show_answer)
gui_hooks.card_will_show.append(_on_card_will_show)
mw.addonManager.setConfigUpdatedAction(__name__, _refresh_mobile_snippet)

_menu = QMenu("Pavlov", mw)
for _label, _handler in (
    ("Settings...", _open_settings),
    ("Copy Photos to Phone/Tablet...", _copy_to_mobile),
    ("Remove from Phone/Tablet...", _remove_from_mobile),
):
    qconnect(_menu.addAction(_label).triggered, _handler)
mw.form.menuTools.addMenu(_menu)
