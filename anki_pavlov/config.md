**Pavlov** shows a random photo from your folder after you answer a card.

- `photo_folder`: folder to pick photos from. Easiest to set via *Tools > Pavlov > Choose Photo Folder*. For Google Drive, install Google Drive for Desktop and pick a folder under its drive letter (e.g. `G:/My Drive/Photos`).
- `include_subfolders`: also look inside subfolders.
- `reward_on_buttons`: which answer buttons earn a photo. `1` = Again, `2` = Hard, `3` = Good, `4` = Easy. Desktop only: phones and tablets can't tell which button you pressed.
- `chance`: probability of a photo per qualifying answer, from `0.0` to `1.0`. Lower values make rewards a surprise.
- `display_seconds`: how long the photo stays up. Click or tap it to dismiss it early.
- `max_image_size`: photos are scaled down to fit this many pixels on their longest side.
- `mobile_photo_count`: how many photos *Tools > Pavlov > Copy Photos to Phone/Tablet* copies into Anki to sync. Each is roughly 0.3 MB.

**Phones and tablets** (AnkiMobile, AnkiDroid) can't run add-ons. Use *Copy Photos to Phone/Tablet*, then sync: a random photo appears when you reveal an answer. Changes to `chance` and `display_seconds` reach phones and tablets only after you run it again.

Supported formats: JPG, PNG, GIF (first frame), WebP, BMP.
