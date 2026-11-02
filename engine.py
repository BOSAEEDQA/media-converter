"""محرك التحويل: يبني أوامر FFmpeg ويقرأ معلومات الملفات."""
import os
import re
import subprocess

import imageio_ffmpeg

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

# على ويندوز: منع ظهور نافذة سوداء (Console) مع كل استدعاء لـ ffmpeg
NO_WINDOW = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}


class ConvertError(Exception):
    pass


# صيغ الفيديو المقبولة كمدخل
VIDEO_INPUT_EXTS = (
    ".avi", ".mp4", ".m4v", ".mov", ".mkv", ".webm", ".wmv", ".asf", ".flv", ".f4v",
    ".mpg", ".mpeg", ".m2v", ".vob", ".ts", ".mts", ".m2ts", ".3gp", ".3g2", ".ogv",
    ".divx", ".xvid", ".rm", ".rmvb", ".dv", ".mxf", ".gif",
)

# صيغ الصوت المقبولة كمدخل (تُحوَّل كلها إلى MP3)
AUDIO_INPUT_EXTS = (
    ".wav", ".wave", ".mp3", ".m4a", ".m4b", ".aac", ".flac", ".ogg", ".oga", ".opus",
    ".aif", ".aiff", ".aifc", ".caf", ".wma", ".mp2", ".ac3", ".eac3", ".dts", ".amr",
    ".3ga", ".ape", ".wv", ".tta", ".mka", ".au", ".snd", ".ra", ".weba",
)

# (المفتاح، الاسم، الامتداد، الوصف، صوت فقط؟)
VIDEO_FORMATS = [
    ("mp4", "MP4", ".mp4", "الأكثر توافقاً", False),
    ("mkv", "MKV", ".mkv", "حاوية مرنة", False),
    ("mov", "MOV", ".mov", "أجهزة أبل", False),
    ("webm", "WEBM", ".webm", "مثالي للويب", False),
    ("wmv", "WMV", ".wmv", "ويندوز ميديا", False),
    ("flv", "FLV", ".flv", "فلاش فيديو", False),
    ("mpeg", "MPEG", ".mpg", "MPEG-2 / DVD", False),
    ("3gp", "3GP", ".3gp", "للجوالات", False),
    ("gif", "GIF", ".gif", "صورة متحركة", False),
    ("mp3", "MP3", ".mp3", "استخراج الصوت", True),
    ("m4a", "M4A", ".m4a", "صوت AAC", True),
    ("wav", "WAV", ".wav", "صوت بدون ضغط", True),
]
FORMAT_BY_KEY = {f[0]: f for f in VIDEO_FORMATS}

# الجودة: 0 عالية، 1 متوازنة، 2 حجم صغير
X264_CRF = [18, 23, 28]
VP9_CRF = [24, 32, 40]
QSCALE = [2, 5, 9]
AUDIO_BR = ["256k", "192k", "128k"]
GIF_FPS = [15, 12, 10]

MPEG2_RATES = [23.976, 24, 25, 29.97, 30, 50, 59.94, 60]


def probe(path):
    """يقرأ المدة ووجود الصوت/الفيديو ومعدل الإطارات من مخرجات ffmpeg -i."""
    info = {"duration": 0.0, "has_audio": False, "has_video": False,
            "fps": None, "width": None, "height": None, "cover": False}
    try:
        out = subprocess.run([FFMPEG, "-hide_banner", "-i", path],
                             capture_output=True, text=True, encoding="utf-8",
                             errors="replace", timeout=20, **NO_WINDOW).stderr
    except Exception:
        return info
    m = re.search(r"Duration: (\d+):(\d+):(\d+(?:\.\d+)?)", out)
    if m:
        h, mi, s = m.groups()
        info["duration"] = int(h) * 3600 + int(mi) * 60 + float(s)
    for line in out.splitlines():
        if "Stream #" not in line:
            continue
        if "Video:" in line and not info["has_video"]:
            info["has_video"] = True
            # صورة غلاف مدمجة في ملف صوتي (M4A/FLAC/MP3) يمكن نقلها كما هي إلى MP3
            info["cover"] = "attached pic" in line and bool(re.search(r"Video: (mjpeg|png)", line))
            size = re.search(r"\b(\d{2,5})x(\d{2,5})\b", line)
            if size:
                info["width"], info["height"] = int(size.group(1)), int(size.group(2))
            fps = re.search(r"(\d+(?:\.\d+)?) (?:fps|tbr)", line)
            if fps:
                info["fps"] = float(fps.group(1))
        elif "Audio:" in line:
            info["has_audio"] = True
    return info


def unique_path(path):
    """يضيف (1)، (2)… إذا كان الملف موجوداً حتى لا نكتب فوقه."""
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    i = 1
    while os.path.exists(f"{base} ({i}){ext}"):
        i += 1
    return f"{base} ({i}){ext}"


def _scale_filter(height):
    # يحافظ على أبعاد زوجية (مطلوبة لـ H.264) ولا يكبّر الفيديو أبداً
    if height:
        return f"scale=-2:'trunc(min({height},ih)/2)*2'"
    return "scale='trunc(iw/2)*2':'trunc(ih/2)*2'"


def _nearest_mpeg2_rate(fps):
    if not fps:
        return "25"
    best = min(MPEG2_RATES, key=lambda r: abs(r - fps))
    return {23.976: "24000/1001", 29.97: "30000/1001", 59.94: "60000/1001"}.get(best, str(best))


def build_video_cmd(src, out_dir, fmt_key, quality, height, info):
    key, _, ext, _, audio_only = FORMAT_BY_KEY[fmt_key]
    name = os.path.splitext(os.path.basename(src))[0]
    dst = unique_path(os.path.join(out_dir, name + ext))

    if audio_only and not info.get("has_audio"):
        raise ConvertError("الملف لا يحتوي على مسار صوتي")
    if not audio_only and info.get("has_video") is False and info.get("duration"):
        raise ConvertError("الملف لا يحتوي على فيديو")

    args = ["-hide_banner", "-y", "-nostdin", "-i", src]
    abr = AUDIO_BR[quality]

    if key in ("mp4", "mkv", "mov", "flv", "3gp"):
        args += ["-map", "0:v:0", "-map", "0:a?", "-vf", _scale_filter(height),
                 "-c:v", "libx264", "-preset", "medium", "-crf", str(X264_CRF[quality]),
                 "-pix_fmt", "yuv420p"]
        if key == "3gp":
            args += ["-profile:v", "baseline", "-level", "3.0"]
        args += ["-c:a", "aac", "-b:a", "128k" if key == "3gp" else abr]
        if key in ("mp4", "mov"):
            args += ["-movflags", "+faststart"]
    elif key == "webm":
        args += ["-map", "0:v:0", "-map", "0:a?", "-vf", _scale_filter(height),
                 "-c:v", "libvpx-vp9", "-crf", str(VP9_CRF[quality]), "-b:v", "0",
                 "-row-mt", "1", "-deadline", "good", "-cpu-used", "4",
                 "-c:a", "libopus", "-b:a", "160k" if quality == 0 else "128k"]
    elif key == "wmv":
        args += ["-map", "0:v:0", "-map", "0:a?", "-vf", _scale_filter(height),
                 "-c:v", "wmv2", "-q:v", str(QSCALE[quality]),
                 "-c:a", "wmav2", "-b:a", abr]
    elif key == "mpeg":
        args += ["-map", "0:v:0", "-map", "0:a?", "-vf", _scale_filter(height),
                 "-c:v", "mpeg2video", "-q:v", str(QSCALE[quality]),
                 "-r", _nearest_mpeg2_rate(info.get("fps")), "-pix_fmt", "yuv420p",
                 "-c:a", "mp2", "-b:a", "192k", "-ar", "48000"]
    elif key == "gif":
        h = height or 480
        fps = GIF_FPS[quality]
        args += ["-an", "-filter_complex",
                 f"[0:v]fps={fps},scale=-1:'min({h},ih)':flags=lanczos,split[a][b];"
                 f"[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=4",
                 "-loop", "0"]
    elif key == "mp3":
        args += ["-vn", "-c:a", "libmp3lame", "-b:a", ["320k", "192k", "128k"][quality],
                 "-id3v2_version", "3"]
    elif key == "m4a":
        args += ["-vn", "-c:a", "aac", "-b:a", abr, "-movflags", "+faststart"]
    elif key == "wav":
        args += ["-vn", "-c:a", "pcm_s16le"]

    args += ["-progress", "pipe:1", "-nostats", dst]
    return args, dst


def build_audio_cmd(src, out_dir, bitrate, sample_rate, channels, cover=False):
    name = os.path.splitext(os.path.basename(src))[0]
    dst = unique_path(os.path.join(out_dir, name + ".mp3"))
    args = ["-hide_banner", "-y", "-nostdin", "-i", src, "-map", "0:a:0"]
    if cover:
        args += ["-map", "0:v:0", "-c:v", "copy", "-disposition:v:0", "attached_pic"]
    args += ["-map_metadata", "0", "-c:a", "libmp3lame", "-b:a", f"{bitrate}k"]
    if sample_rate:
        args += ["-ar", str(sample_rate)]
    if channels:
        args += ["-ac", str(channels)]
    args += ["-id3v2_version", "3", "-progress", "pipe:1", "-nostats", dst]
    return args, dst


def ffmpeg_version():
    try:
        out = subprocess.run([FFMPEG, "-version"], capture_output=True, text=True,
                             encoding="utf-8", errors="replace", **NO_WINDOW).stdout
        return out.split()[2].split("-")[0]
    except Exception:
        return "?"
