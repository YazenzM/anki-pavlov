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
from aqt.qt import QBuffer, QByteArray, QFileDialog, QImage, QImageReader, QIODevice, QMenu, Qt
from aqt.utils import askUser, qconnect, showInfo, showWarning, tooltip

PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}

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

# Plain ES5 so it also runs in the older web views used by phone and tablet apps.
_OVERLAY_JS = """(function (src, ms) {
    var old = document.getElementById("pavlov-reward");
    if (old) old.parentNode.removeChild(old);
    var overlay = document.createElement("div");
    overlay.id = "pavlov-reward";
    overlay.style.cssText = "position:fixed;top:0;right:0;bottom:0;left:0;z-index:99999;display:flex;" +
        "align-items:center;justify-content:center;background:rgba(0,0,0,.8);opacity:0;transition:opacity .25s;cursor:pointer";
    var img = document.createElement("img");
    img.style.cssText = "max-width:90vw;max-height:90vh;border-radius:12px;box-shadow:0 8px 40px rgba(0,0,0,.6)";
    img.onerror = close;
    img.src = src;
    overlay.appendChild(img);
    document.body.appendChild(overlay);
    void overlay.offsetWidth;
    overlay.style.opacity = "1";
    function close() {
        overlay.style.opacity = "0";
        setTimeout(function () { if (overlay.parentNode) overlay.parentNode.removeChild(overlay); }, 250);
    }
    overlay.addEventListener("click", close);
    setTimeout(close, ms);
})(%s, %d);"""

_MOBILE_JS = """(function () {
    if (Math.random() >= %s) return;
    var n = String(1 + Math.floor(Math.random() * %d));
    while (n.length < 4) n = "0" + n;
    %s
})();"""

_HIDE_JS = 'document.getElementById("pavlov-reward")?.remove();'


def _config() -> dict:
    return mw.addonManager.getConfig(__name__) or {}


def _photo_folder(config: dict) -> str | None:
    folder = config.get("photo_folder", "")
    return folder if folder and os.path.isdir(folder) else None


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
    global _loading, _warned_no_folder
    config = _config()
    if ease not in config.get("reward_on_buttons", [2, 3, 4]):
        return
    if random.random() >= config.get("chance", 1.0):
        return

    folder = _photo_folder(config)
    if not folder:
        if not _warned_no_folder:
            tooltip("Pavlov: choose a photo folder via Tools > Pavlov > Choose Photo Folder")
            _warned_no_folder = True
        return
    if _loading:
        return

    _loading = True
    recursive = config.get("include_subfolders", True)
    max_size = config.get("max_image_size", 1600)
    duration_ms = int(config.get("display_seconds", 3) * 1000)

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
            mw.reviewer.web.eval(_OVERLAY_JS % (json.dumps(uri), duration_ms))

    mw.taskman.run_in_background(lambda: _pick_and_load(folder, recursive, max_size), on_done)


def _on_show_answer(card) -> None:
    mw.reviewer.web.eval(_HIDE_JS)


def _on_card_will_show(text: str, card, kind: str) -> str:
    # The desktop add-on rewards answers itself, so the phone/tablet script is dropped from desktop reviews.
    # Previews keep it, which makes them a handy way to check the phone/tablet version.
    if kind.startswith("review"):
        return SNIPPET_RE.sub("", text)
    return text


def _choose_folder() -> None:
    config = _config()
    folder = QFileDialog.getExistingDirectory(mw, "Choose your reward photo folder", config.get("photo_folder", ""))
    if not folder:
        return
    config["photo_folder"] = folder
    mw.addonManager.writeConfig(__name__, config)
    tooltip(f"Pavlov will show photos from:<br>{folder}")


def _mobile_name(number: int) -> str:
    return f"{MOBILE_PREFIX}{number:04d}.jpg"


def _mobile_snippet(count: int, chance: float, duration_ms: int) -> str:
    src = json.dumps(MOBILE_PREFIX) + ' + n + ".jpg"'
    js = _MOBILE_JS % (chance, count, _OVERLAY_JS % (src, duration_ms))
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
        showWarning("Choose a photo folder first via Tools > Pavlov > Choose Photo Folder.")
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
    duration_ms = int(config.get("display_seconds", 3) * 1000)
    media_dir = mw.col.media.dir()

    def on_success(written: int) -> None:
        if written == 0:
            showWarning(f"No photos found in {folder}")
            return
        _set_snippet(_mobile_snippet(written, config.get("chance", 1.0), duration_ms))
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

_menu = QMenu("Pavlov", mw)
for _label, _handler in (
    ("Choose Photo Folder...", _choose_folder),
    ("Copy Photos to Phone/Tablet...", _copy_to_mobile),
    ("Remove from Phone/Tablet...", _remove_from_mobile),
):
    qconnect(_menu.addAction(_label).triggered, _handler)
mw.form.menuTools.addMenu(_menu)
