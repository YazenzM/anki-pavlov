# Pavlov: photo rewards for Anki

Pavlov is an Anki add-on that shows you a random photo from your own collection each time you get a card right. Use holiday snaps, pets, family or anything else you enjoy. It's a small, personal reward that gives you something to look forward to in every review session.

## Features

- Shows a random photo after you press **Hard**, **Good** or **Easy**. You choose which buttons count as right.
- Streak mode: earn a photo with a run of right answers in a row. Or count mode: earn one every few right answers, without misses resetting your progress.
- Optional flair: a burst of confetti and a streak counter each time you get a card right.
- Puts the photo in a corner or a side panel so it doesn't block your next card, or full screen if you prefer.
- Uses any folder on your computer, including Google Drive through Google Drive for Desktop.
- Shows every photo once before repeating any.
- Optional surprise mode: set a chance below 100% so rewards are unpredictable.
- Also works on AnkiMobile (iPhone and iPad) and AnkiDroid, through a batch of photos synced with your collection.

## Install

- **From AnkiWeb** (coming soon).
- **From a file:** download `anki_pavlov.ankiaddon` from [Releases](../../releases) and double-click it, or in Anki use **Tools → Add-ons → Install from file…**.

## Getting started

1. In Anki, open **Tools → Pavlov → Settings…** and pick a folder of photos.
2. Study as usual. A photo fades in after each qualifying answer. Click it to close it early.

**Google Drive:** install [Google Drive for Desktop](https://www.google.com/drive/download/) and pick a folder on the drive it creates, such as `G:\My Drive\Photos`. Right-click the folder and choose **Available offline** so photos appear without a download delay.

## Phones and tablets

AnkiMobile and AnkiDroid can't run add-ons, so Pavlov sends photos to them through Anki's normal sync:

1. On your computer, open **Tools → Pavlov → Copy Photos to Phone/Tablet…**. This copies a random batch of photos into your Anki media and adds a small script to the back of your card types.
2. Sync on your computer, then on your phone or tablet.

A random photo then appears each time you reveal an answer. Phone and tablet apps don't tell add-ons which button you pressed, so the photo shows whether or not you got the card right, and there's no confetti or streak counter. Streak and count modes become matching odds instead: needing 5 right answers shows a photo on about 1 card in 5. Tap a photo to close it.

Run the copy again for a fresh batch. **Tools → Pavlov → Remove from Phone/Tablet…** removes the photos and the script.

## Settings

Open **Tools → Pavlov → Settings…** to choose:

- **Photo folder**, and whether to include its subfolders
- **When to show a photo:**
  - after each right answer, with an optional chance for surprise rewards
  - after a streak of right answers in a row, where a miss resets the streak
  - after a number of right answers, where misses don't reset the count
- **Which answers count as right**, for example only Good and Easy (computer only)
- **Layout:** a corner, a panel on the right that moves the card over to make room, or full screen
- **Photo size**, as a share of the window
- **How long each photo shows.** Set it to 0 to keep each photo up until you click it.
- **Flair:** confetti and a streak counter on right answers (computer only)

Streaks and counts restart from zero each time you open Anki.

Setting changes reach your phone or tablet the next time you sync.

Two advanced settings are only in **Tools → Add-ons → Pavlov → Config**:

| Setting | Default | What it does |
| --- | --- | --- |
| `max_image_size` | `1600` | Longest side in pixels that photos are scaled down to. |
| `mobile_photo_count` | `100` | How many photos are copied for phones and tablets, about 0.3 MB each. |

## Supported formats

JPG, PNG, WebP, BMP and GIF (first frame only). HEIC, the iPhone camera default, isn't supported: convert those photos to JPG, or set the iPhone camera to **Settings → Camera → Formats → Most Compatible**.

## Building from source

```
python build.py
```

This writes `dist/anki_pavlov.ankiaddon`, ready to install or upload to AnkiWeb.

## License

[MIT](LICENSE)
