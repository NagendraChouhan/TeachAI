"""Free images for slides / reading material: AI illustration (Pollinations), web image search as fallback."""
import hashlib
import io
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image
from ddgs import DDGS

from .config import DATA

IMG_DIR = DATA / "images"
IMG_DIR.mkdir(parents=True, exist_ok=True)
STYLE = "colorful flat vector illustration, clean, bright colors, educational, no text, no letters"


def _download(url: str, timeout: int) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=timeout).read()


def _save(data: bytes, path: Path) -> bool:
    try:
        img = Image.open(io.BytesIO(data)).convert("RGB")
        if img.width < 200 or img.height < 150:
            return False
        img.thumbnail((1200, 1200))
        img.save(path, "JPEG", quality=85)
        return True
    except Exception:
        return False


def fetch_image(prompt: str) -> Path | None:
    path = IMG_DIR / f"{hashlib.md5(prompt.encode()).hexdigest()}.jpg"
    if path.exists():
        return path
    try:  # 1) AI illustration
        url = ("https://image.pollinations.ai/prompt/" + urllib.parse.quote(f"{prompt}, {STYLE}")
               + "?width=960&height=720&nologo=true")
        if _save(_download(url, 60), path):
            return path
    except Exception:
        pass
    try:  # 2) web image search
        for r in DDGS().images(prompt + " diagram illustration", max_results=4):
            try:
                if _save(_download(r["image"], 15), path):
                    return path
            except Exception:
                continue
    except Exception:
        pass
    return None


def fetch_many(prompts: list[str]) -> list[Path | None]:
    """Fetch in parallel; empty prompt -> None."""
    with ThreadPoolExecutor(max_workers=3) as ex:
        return list(ex.map(lambda p: fetch_image(p) if p.strip() else None, prompts))
