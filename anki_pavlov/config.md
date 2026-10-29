**Pavlov** shows a random photo from your folder after you answer a card.

Most of these are easier to change in *Tools > Pavlov > Settings*.

- `photo_folder`: folder to pick photos from. For Google Drive, install Google Drive for Desktop and pick a folder under its drive letter (e.g. `G:/My Drive/Photos`).
- `include_subfolders`: also look inside subfolders.
- `layout`: where the photo appears: `bottom-right`, `bottom-left`, `top-right`, `top-left` (a corner, leaving the card visible), `side` (a panel on the right, with the card moved over to make room) or `fullscreen`.
- `photo_size`: how much of the window the photo may take up, from `10` to `90` percent. Not used by `fullscreen`.
- `display_seconds`: how long the photo stays up. `0` keeps it until you click it. Clicking or tapping always dismisses it early.
- `reward_on_buttons`: which answer buttons earn a photo. `1` = Again, `2` = Hard, `3` = Good, `4` = Easy. Desktop only: phones and tablets can't tell which button you pressed.
- `chance`: probability of a photo per qualifying answer, from `0.0` to `1.0`. Lower values make rewards a surprise.
- `max_image_size`: photos are scaled down to fit this many pixels on their longest side.
- `mobile_photo_count`: how many photos *Tools > Pavlov > Copy Photos to Phone/Tablet* copies into Anki to sync. Each is roughly 0.3 MB.

**Phones and tablets** (AnkiMobile, AnkiDroid) can't run add-ons. Use *Copy Photos to Phone/Tablet*, then sync: a random photo appears when you reveal an answer. Setting changes reach them the next time you sync.

Supported formats: JPG, PNG, GIF (first frame), WebP, BMP.
