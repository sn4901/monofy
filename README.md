# Monofy (Ableton Sample Editor mono fixer)

`monofy` is a small utility intended to be used as **Ableton Live's Sample Editor**. When Ableton launches it with an audio file path, it converts that file to **mono** and overwrites the original so Ableton updates the sample in-place.

The use case for this is when you run Ableton's "Bounce in Place", it bounces as stereo even if the original source is mono (I assume since you could have stereo effects on the channel). A more detailed use case is since Ableton lacks ARA support, I often find myself bouncing a Melodyne or VocAlign vocal track in place so I can actually see and modify the waveform. This is a quick way to get the audio file back to mono to save on space and CPU power.

When you set the .exe as your Sample Editor in Ableton (Settings > File & Folder > Sample Editor) the "Edit" button on the sample becomes a 1 click mono button. The original file gets sent to the Recycle Bin and a new one is saved in place.

## Requirements

### 1) FFmpeg
Monofy relies on **FFmpeg** for reading/writing audio.

You must have FFmpeg available in **one** of these ways:

**A) Put FFmpeg next to `monofy.exe`**
Place these in the same folder:
- `monofy.exe`
- `ffmpeg.exe`

Many FFmpeg Windows builds also require additional `*.dll` files in the same folder as `ffmpeg.exe`.  
If you see missing DLL errors, copy **everything** from the FFmpeg `bin\` folder (including DLLs) next to `monofy.exe`.

**B) Install FFmpeg and add it to PATH**
If `ffmpeg` runs from PowerShell (`ffmpeg -version`), Monofy will use it.

**Download FFmpeg (Windows):**
- https://www.ffmpeg.org/

### 2) Windows
This is for Windows only. For macOS support, the trash feature needs to be coded. I don't have a macOS device to build/test this on. Linux support isn't planned since Ableton Live doesn't run on Linux.

## Supported formats
Any audio format FFmpeg can read/write, including:
- WAV
- AIFF
- FLAC
- MP3

**Notes about preserving settings:**
- Sample rate is preserved unless explicitly changed
- For WAV/AIFF/FLAC, output is lossless (FLAC is re-encoded losslessly)
- For MP3 and other lossy formats, mono conversion requires re-encoding. Bitrate/encoding details cannot be preserved byte-for-byte.

## Using with Ableton Live
1. Put `monofy.exe` (and `ffmpeg.exe` + required DLLs) somewhere on your computer.
2. In Ableton Live:
   - Preferences → File & Folder → Sample Editor
   - Select `monofy.exe`
3. Click **Edit** on a sample in Live.
4. Live will call Monofy with the file path; Monofy overwrites the file as mono; Live reloads it.

## Building

### Python
You need Python installed.

### PyInstaller
Used to build a single-file executable.

### Install
```powershell
python -m pip install --upgrade pip
python -m pip install pyinstaller
python -m PyInstaller --onefile monofy.py
```