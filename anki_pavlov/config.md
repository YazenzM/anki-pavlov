**Pavlov** shows a random photo from your folder when you get cards right.

Most of these are easier to change in *Tools > Pavlov > Settings*.

- `photo_folder`: folder to pick photos from. For Google Drive, install Google Drive for Desktop and pick a folder under its drive letter (e.g. `G:/My Drive/Photos`).
- `include_subfolders`: also look inside subfolders.
- `reward_mode`: when a photo appears.
  - `every`: after each right answer, subject to `chance`.
  - `streak`: after `answers_needed` right answers in a row. A wrong answer resets the streak.
  - `count`: after every `answers_needed` right answers. Wrong answers don't reset the count.
- `answers_needed`: right answers needed for a photo in `streak` and `count` modes.
- `chance`: probability of a photo per right answer in `every` mode, from `0.0` to `1.0`. Lower values make rewards a surprise.
- `reward_on_buttons`: which answer buttons count as right. `1` = Again, `2` = Hard, `3` = Good, `4` = Easy. Any other button counts as wrong.
- `flair`: `true` shows a confetti burst and a streak counter after each right answer.
- `layout`: where the photo appears: `bottom-right`, `bottom-left`, `top-right`, `top-left` (a corner, leaving the card visible), `side` (a panel on the right, with the card moved over to make room) or `fullscreen`.
- `photo_size`: how much of the window the photo may take up, from `10` to `90` percent. Not used by `fullscreen`.
- `display_seconds`: how long the photo stays up. `0` keeps it until you click it. Clicking or tapping always dismisses it early.
- `max_image_size`: photos are scaled down to fit this many pixels on their longest side.
- `mobile_photo_count`: how many photos *Tools > Pavlov > Copy Photos to Phone/Tablet* copies into Anki to sync. Each is roughly 0.3 MB.

Streaks and counts restart from zero each time you open Anki.

**Phones and tablets** (AnkiMobile, AnkiDroid) can't run add-ons. Use *Copy Photos to Phone/Tablet*, then sync: a random photo appears when you reveal an answer. They can't tell which button you pressed, so there's no flair there, and `streak` and `count` modes become odds instead: needing 5 right answers shows a photo on about 1 card in 5. Setting changes reach them the next time you sync.

Supported formats: JPG, PNG, GIF (first frame), WebP, BMP.
