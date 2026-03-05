import os
import shutil
import subprocess
import sys
import tempfile
import datetime

# =========================
# USER SETTINGS
# =========================

# Before overwriting, move the original file to the Windows Recycle Bin (if possible)
SEND_OLD_TO_RECYCLE_BIN = True

# Create "<original file>.<ext>.bak"
SAVE_BAK_FILE = False

# Mono behavior:
# - "drop_right": keep LEFT channel only (fast, default)
# - "sum": average L+R to mono (can reduce phase issues in some cases, but can also cause cancellations)
MONO_MODE = "drop_right"

# (for debugging) log to "monofy.log" next to the exe
ENABLE_LOGGING = False

# Overwrite the original file or create a new file next to it with the suffix "_mono"
# Ableton "Edit" workflow expects this to be true
OVERWRITE_IN_PLACE = True

# For lossy formats (mp3, m4a, etc.), re-encoding is required to change to mono
# This is a target bitrate for mp3
MP3_BITRATE = "320k"

# =========================
# END USER SETTINGS
# =========================

def exe_dir():
    return os.path.dirname(os.path.abspath(sys.argv[0]))


def log(msg: str):
    if not ENABLE_LOGGING:
        return
    try:
        with open(os.path.join(exe_dir(), "monofy.log"), "a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now().isoformat()}  {msg}\n")
    except Exception:
        pass


def find_ffmpeg():
    # Prefer ffmpeg.exe next to the exe, otherwise rely on PATH
    local = os.path.join(exe_dir(), "ffmpeg.exe")
    if os.path.isfile(local):
        return local
    return "ffmpeg"


def try_send_to_recycle_bin(path: str) -> bool:
    """
    Send a file to Recycle Bin on Windows.
    This uses SHFileOperationW (older but widely compatible)
    If this fails, fall back to normal delete/move behavior (non-fatal)
    """
    if os.name != "nt":
        return False

    try:
        import ctypes
        from ctypes import wintypes

        FO_DELETE = 3
        FOF_ALLOWUNDO = 0x0040
        FOF_NOCONFIRMATION = 0x0010
        FOF_SILENT = 0x0004

        class SHFILEOPSTRUCTW(ctypes.Structure):
            _fields_ = [
                ("hwnd", wintypes.HWND),
                ("wFunc", wintypes.UINT),
                ("pFrom", wintypes.LPCWSTR),
                ("pTo", wintypes.LPCWSTR),
                ("fFlags", wintypes.UINT),
                ("fAnyOperationsAborted", wintypes.BOOL),
                ("hNameMappings", wintypes.LPVOID),
                ("lpszProgressTitle", wintypes.LPCWSTR),
            ]

        shell32 = ctypes.windll.shell32
        # pFrom must be double-null-terminated
        pFrom = path + "\0\0"
        op = SHFILEOPSTRUCTW()
        op.hwnd = None
        op.wFunc = FO_DELETE
        op.pFrom = pFrom
        op.pTo = None
        op.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT

        res = shell32.SHFileOperationW(ctypes.byref(op))
        # res == 0 means success
        return res == 0 and not op.fAnyOperationsAborted
    except Exception as e:
        log(f"RecycleBin failed: {e!r}")
        return False


def build_audio_filter() -> str:
    if MONO_MODE == "sum":
        return "pan=mono|c0=0.5*c0+0.5*c1"
    # default: drop right (keep left)
    return "pan=mono|c0=c0"


def codec_args_for_extension(ext_lower: str):
    """
    Aim for: keep container, keep sample rate, avoid lossy changes where possible.
    Notes:
    - WAV/AIFF: we write PCM (lossless). Sample rate preserved by default unless you set -ar.
    - FLAC: lossless but re-encoded (still lossless).
    - MP3: must re-encode to change channels. We'll target MP3 bitrate.
    - Other: let ffmpeg choose reasonable defaults (may re-encode).
    """
    if ext_lower in (".wav",):
        # Use 24-bit PCM; if you need exact original bit depth, you'd need ffprobe.
        return ["-c:a", "pcm_s24le"]
    if ext_lower in (".aif", ".aiff"):
        # Many tools expect big-endian for AIFF, but ffmpeg will handle it; codec selection can vary by build.
        # Using pcm_s24be is typical.
        return ["-c:a", "pcm_s24be"]
    if ext_lower == ".flac":
        # Lossless; compression_level 0 is faster, still lossless.
        return ["-c:a", "flac", "-compression_level", "0"]
    if ext_lower == ".mp3":
        return ["-c:a", "libmp3lame", "-b:a", MP3_BITRATE]
    # For m4a/aac/ogg/etc: you could add explicit codecs here if desired.
    return []


def main():
    log(f"argv={sys.argv!r}")

    if len(sys.argv) < 2:
        log("No file argument; exiting.")
        return 0

    in_path = sys.argv[1].strip('"')
    log(f"in_path={in_path}")

    if not os.path.isfile(in_path):
        log("Input path not a file.")
        return 1

    ffmpeg = find_ffmpeg()
    log(f"ffmpeg={ffmpeg}")

    in_dir = os.path.dirname(in_path)
    base, ext = os.path.splitext(os.path.basename(in_path))
    ext_l = ext.lower()

    # Output path: either temp (for overwrite) or new file
    if OVERWRITE_IN_PLACE:
        fd, tmp_out = tempfile.mkstemp(prefix=base + "_", suffix=ext, dir=in_dir)
        os.close(fd)
        out_path = tmp_out
    else:
        out_path = os.path.join(in_dir, f"{base}_mono{ext}")

    if SAVE_BAK_FILE:
        bak_path = in_path + ".bak"
        if not os.path.exists(bak_path):
            try:
                shutil.copy2(in_path, bak_path)
                log(f"backup created: {bak_path}")
            except Exception as e:
                log(f"backup failed: {e!r}")

    audio_filter = build_audio_filter()
    cargs = codec_args_for_extension(ext_l)

    cmd = [
        ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
        "-i", in_path,
        "-filter:a", audio_filter,
        "-ac", "1",
        *cargs,
        out_path
    ]
    log(f"cmd={' '.join(cmd)}")

    r = subprocess.run(cmd, capture_output=True, text=True)
    log(f"ffmpeg returncode={r.returncode}")
    if r.stdout:
        log(f"ffmpeg stdout={r.stdout.strip()}")
    if r.stderr:
        log(f"ffmpeg stderr={r.stderr.strip()}")

    if r.returncode != 0:
        # Clean temp output
        if OVERWRITE_IN_PLACE:
            try:
                os.remove(out_path)
            except Exception:
                pass
        return 2

    if not OVERWRITE_IN_PLACE:
        log(f"wrote non-destructive output: {out_path}")
        return 0

    # Overwrite flow:
    # We currently have original file (in_path) and converted temp (out_path).
    # To be "non-destructive", we can send the original to Recycle Bin *before* replacing it.
    # However, Ableton expects the same path. So we:
    # 1) Move original aside temporarily
    # 2) Put new file in its place
    # 3) Send the old one to recycle bin (best effort), else delete it
    try:
        fd, old_tmp = tempfile.mkstemp(prefix=base + "_old_", suffix=ext, dir=in_dir)
        os.close(fd)
        os.remove(old_tmp)  # just reserving a unique name

        os.replace(in_path, old_tmp)     # move original out of the way
        os.replace(out_path, in_path)    # move mono file into original path
        log(f"replaced original with mono: {in_path}")

        if SEND_OLD_TO_RECYCLE_BIN:
            ok = try_send_to_recycle_bin(old_tmp)
            log(f"sent old to recycle bin: {ok}")
            if not ok:
                try:
                    os.remove(old_tmp)
                    log("old tmp deleted (recycle failed).")
                except Exception as e:
                    log(f"failed to delete old tmp: {e!r}")
        else:
            try:
                os.remove(old_tmp)
                log("old tmp deleted (recycle disabled).")
            except Exception as e:
                log(f"failed to delete old tmp: {e!r}")

        return 0

    except Exception as e:
        log(f"overwrite exception: {e!r}")
        # best-effort cleanup
        try:
            if os.path.exists(out_path):
                os.remove(out_path)
        except Exception:
            pass
        return 3


if __name__ == "__main__":
    raise SystemExit(main())