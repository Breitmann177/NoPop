<p align="center">
  <img src="docs/logo.png" width="120" alt="NoPop logo">
</p>

<h1 align="center">NoPop</h1>

<p align="center">
  <b>Stops the annoying "pop" from your laptop speakers when audio starts or stops.</b><br>
  Tiny, free, open source. Lives quietly in your system tray.
</p>

<p align="center">
  <a href="../../releases/latest"><b>⬇ Download</b></a> ·
  <a href="README.de.md">Deutsch</a>
</p>

---

## The problem

You pause a YouTube video, a friend stops talking on Discord, a song ends – and your speakers go **"pop"**.
Many laptops (Cirrus Logic, Realtek and other "smart amps") switch the speaker amplifier off a moment after the sound stops,
and switch it back on when the next sound starts. That switching is the pop.

## How NoPop fixes it

When any sound plays, NoPop keeps the speakers awake for a few minutes (you choose how long) by playing an
**inaudible** 20 Hz tone at about −70 dB. Pause and resume as much as you like – no pop.
When nothing has played for that long, NoPop lets the speakers sleep again and waits for the next sound.

> Plain digital silence is not enough: smart amps detect silence and turn off anyway. That's why NoPop uses an inaudible tone.

<p align="center">
  <img src="docs/screenshot-en.png" width="300" alt="NoPop window">
</p>

## Features

- **One button**: on / off
- **Keep awake for X minutes** after the last sound (type the number, 1–240)
- **Starts with Windows** (also on battery) – optional
- **Tray icon** lights up in your chosen color while the speakers are kept awake
- **Light on resources**: one process, ~25–45 MB RAM, ~0 % CPU while waiting
- **Private**: no internet connection, no tracking, no account. It only reads the volume level of your speaker.
- English and German (follows your Windows language)

## Install

1. Download `NoPop-x.y.z-windows-x64.zip` from the [latest release](../../releases/latest).
2. Right-click the zip → **Extract All**.
3. Double-click **`Install.cmd`** in the extracted folder.

No admin rights needed. NoPop installs to `%LOCALAPPDATA%\Programs\NoPop`, adds a Start menu entry and opens.
You'll find its icon in the system tray (click the **^** arrow next to the clock).

**"Windows protected your PC"?** NoPop isn't signed with a paid certificate, so Windows may warn you about the
install script. Click **More info → Run anyway**. Everything NoPop runs is in this repository, and the bundled
Python runtime is the official one from python.org, signed by the Python Software Foundation.

## Uninstall

**Settings → Apps → Installed apps → NoPop → Uninstall.** This removes the program, its autostart entry,
Start menu entry and settings.

## FAQ

**Does it drain my battery?** Barely. While waiting it uses practically no CPU. While keeping the speakers
awake, the main cost is the speaker amplifier staying on (roughly 0.2–0.5 W) – only for the minutes you set.

**It still pops when I start something after a long break.** Expected: at that moment the speakers really
were asleep. NoPop prevents the pops *between* sounds.

**Bluetooth headphones / USB audio?** NoPop follows your default playback device, so it works with them too,
but the pop problem usually only happens on built-in speakers.

## Build from source

Requires Windows 10/11 and Python 3.12 (64-bit) from python.org.

```
python nopop.py                 # run directly (uses only the standard library)
python packaging/build.py       # build dist/NoPop-<version>-windows-x64.zip
```

`logo.py` regenerates the icons (needs Pillow). The `tests/` folder contains small manual checks.

| File | Purpose |
|---|---|
| `nopop.py` | app, window (tkinter), settings, autostart |
| `kern.py` | sound detection (Windows audio meter via COM) and the inaudible keep-awake tone |
| `tray.py` | tray icon via the Windows API |
| `texte.py` | German / English texts |
| `packaging/` | build script, installer, uninstaller |

## License

[MIT](LICENSE) – free to use, change and share.
