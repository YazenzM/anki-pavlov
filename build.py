"""Package the add-on as dist/anki_pavlov.ankiaddon. Double-click the result to install it into Anki."""

import zipfile
from pathlib import Path

ROOT = Path(__file__).parent
SOURCE = ROOT / "anki_pavlov"
OUTPUT = ROOT / "dist" / "anki_pavlov.ankiaddon"

OUTPUT.parent.mkdir(exist_ok=True)
with zipfile.ZipFile(OUTPUT, "w", zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(SOURCE.rglob("*")):
        # meta.json holds a user's own settings and must not ship with the add-on.
        if path.is_file() and "__pycache__" not in path.parts and path.name != "meta.json":
            archive.write(path, path.relative_to(SOURCE))
    archive.write(ROOT / "LICENSE", "LICENSE")
print(f"Built {OUTPUT}")
