"""Storing, classifying and converting message media (images, video, voice, files)."""

import asyncio
import logging
import re
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


@dataclass
class OutboundMedia:
    """A media file saved locally and reachable at a public URL."""

    kind: str  # image | video | voice | audio | file
    path: Path
    url: str
    file_name: str
    content_type: str | None
    size: int


def safe_file_name(name: str, default: str = "attachment") -> str:
    cleaned = _SAFE_NAME.sub("-", Path(name).name).strip("-")[:120]
    return cleaned or default


def detect_kind(content_type: str | None) -> str:
    major = (content_type or "").split("/", 1)[0].lower()
    return {"image": "image", "video": "video", "audio": "audio"}.get(major, "file")


def save_bytes(content: bytes, file_name: str) -> tuple[Path, str]:
    """Write bytes under the upload dir with an unguessable name; return (path, public URL)."""
    settings = get_settings()
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}-{safe_file_name(file_name)}"
    path = upload_dir / stored_name
    path.write_bytes(content)
    return path, public_url(path)


def _ffmpeg_path() -> str | None:
    """System ffmpeg if installed, else the static binary bundled by imageio-ffmpeg."""
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:  # not installed, or no binary for this platform
        return None


def public_url(path: Path) -> str:
    return f"{get_settings().public_base_url.rstrip('/')}/uploads/{path.name}"


async def convert_to_ogg_opus(src: Path) -> Path | None:
    """Re-encode a recording to OGG/Opus (the format Telegram voice notes require).

    Returns None when ffmpeg is unavailable or fails, so callers can fall back
    to sending the original file as a document.
    """
    ffmpeg = _ffmpeg_path()
    if ffmpeg is None:
        logger.warning("ffmpeg not found; sending voice recording as a plain file")
        return None
    dest = src.with_suffix(".ogg")
    proc = await asyncio.create_subprocess_exec(
        ffmpeg, "-y", "-loglevel", "error", "-i", str(src), "-vn", "-c:a", "libopus", "-b:a", "32k", str(dest),
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0 or not dest.exists():
        logger.warning("ffmpeg voice conversion failed: %s", stderr.decode(errors="replace").strip())
        return None
    return dest
