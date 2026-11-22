"""Cache verified book cover images inside the published Pages artifact.

GitHub Issue image URLs are the source of truth. Cache only explicitly curated
book issues, so ordinary game art and unverified images stay untouched.
This avoids brittle third-party hotlinks on the client side.
"""
from __future__ import annotations

import argparse
from io import BytesIO
import json
from pathlib import Path
from urllib.request import Request, urlopen

from PIL import Image, UnidentifiedImageError

# The covers have been checked against the photographed spines and book titles.
BOOK_ISSUES = {359, 360, 361, 362, 363}
MAX_DOWNLOAD_BYTES = 8 * 1024 * 1024
IMAGE_LIMIT = (680, 1000)
USER_AGENT = "Mozilla/5.0 (compatible; CollectionInventoryCoverCache/1.0)"


def fetch_image(url: str) -> bytes:
    if not url.startswith("https://"):
        raise ValueError("Only HTTPS book image URLs are supported")
    request = Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "image/avif,image/webp,image/apng,image/png,image/jpeg,image/*;q=0.8",
    })
    with urlopen(request, timeout=30) as response:
        content_type = response.headers.get("Content-Type", "").split(";")[0].lower()
        if not content_type.startswith("image/"):
            raise ValueError(f"Unexpected content type: {content_type}")
        content = response.read(MAX_DOWNLOAD_BYTES + 1)
    if len(content) > MAX_DOWNLOAD_BYTES:
        raise ValueError("Cover image exceeds the maximum download size")
    return content


def encode_jpeg(source: bytes) -> bytes:
    with Image.open(BytesIO(source)) as opened:
        if opened.format not in ("PNG", "JPEG", "WEBP"):
            raise ValueError("Unsupported cover image format")
        opened.load()
        if opened.width < 90 or opened.height < 90:
            raise ValueError("Cover image is too small or is probably a placeholder")
        image = opened.convert("RGB")
        image.thumbnail(IMAGE_LIMIT, Image.Resampling.LANCZOS)
        buffer = BytesIO()
        image.save(buffer, format="JPEG", quality=85, optimize=True, progressive=True)
        return buffer.getvalue()


def update_catalog(catalog_path: Path, site_dir: Path) -> None:
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    cached = []
    covers_dir = site_dir / "covers" / "books"
    covers_dir.mkdir(parents=True, exist_ok=True)
    for item in catalog.get("items", []):
        issue_url = item.get("issue_url", "")
        try:
            issue_number = int(issue_url.rsplit("/", 1)[-1])
        except (ValueError, TypeError):
            continue
        if issue_number not in BOOK_ISSUES:
            continue
        if item.get("category") != "書籍":
            raise ValueError(f"Issue #{issue_number} changed category, refusing to cache")
        url = item.get("cover", "")
        if not url:
            raise ValueError(f"Issue #{issue_number} is missing a cover URL")
        try:
            image_bytes = encode_jpeg(fetch_image(url))
        except (OSError, ValueError, UnidentifiedImageError) as error:
            raise RuntimeError(
                f"Issue #{issue_number}: cannot download and verify {url}: {error}"
            ) from error
        local_name = f"{issue_number}.jpg"
        (covers_dir / local_name).write_bytes(image_bytes)
        item["cover"] = f"./covers/books/{local_name}"
        item["cover_source"] = "local"
        cached.append(issue_number)
        print(f"Cached book cover #{issue_number}: {len(image_bytes)} JPEG bytes")
    if set(cached) != BOOK_ISSUES:
        raise ValueError(f"Missing book issues in catalog: {sorted(BOOK_ISSUES - set(cached))}")
    catalog_path.write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print("Published cached book covers: " + ", ".join(map(str, sorted(cached))))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", default="site/data/collection.json")
    parser.add_argument("--site", default="site")
    args = parser.parse_args()
    update_catalog(Path(args.catalog), Path(args.site))


if __name__ == "__main__":
    main()
