#!/usr/bin/env python3
"""Render the social-sharing Open Graph image from owned game artwork.

No AI artwork, guessed game covers, user photographs, or arbitrary remote HTML.
The catalog must have been generated from GitHub Issues first.
"""
import argparse
from io import BytesIO
import ipaddress
import json
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from PIL import Image, ImageDraw, ImageFont, ImageOps, UnidentifiedImageError

SIZE = (1200, 630)
FEATURED_ISSUES = (
    217, 218, 220, 223, 224, 4, 28, 100, 97, 71, 159, 209,
    124, 48, 200, 14, 34, 1, 31, 32, 35, 175,
)
HOST_ALLOWLIST = frozenset((
    "raw.githubusercontent.com", "github.com", "objects.githubusercontent.com",
    "shared.fastly.steamstatic.com", "cdn.cloudflare.steamstatic.com",
    "cdn.akamai.steamstatic.com", "steamcdn-a.akamaihd.net",
    "8-bits.cl", "trader-akiba.com", "www.classic-gameshop.com",
    "image.gamebase.com.tw", "ec.treasure-f.com", "www.4gamer.net",
    "gamerszone.jp", "www.gamerszone.jp", "pcengine.co.uk",
    "www.pcengine.co.uk", "static.mercdn.net", "suruga-ya.jp",
    "www.suruga-ya.jp", "www.suruga-ya.com", "store.kadokawa.co.jp",
    "image.api.playstation.com", "m.media-amazon.com",
    "images-na.ssl-images-amazon.com", "shop.r10s.jp",
    "thumbnail.image.rakuten.co.jp", "image.yodobashi.com",
    "www.famitsu.com", "www.gamecity.ne.jp", "images.nintendolife.com",
))
MAX_DOWNLOAD_BYTES = 5 * 1024 * 1024
MAX_SOURCE_PIXELS = 25_000_000
Image.MAX_IMAGE_PIXELS = MAX_SOURCE_PIXELS


def permitted_url(url):
    """Restrict remote media to known HTTPS image domains, not arbitrary Issue URLs."""
    if not isinstance(url, str):
        return False
    try:
        parsed = urlsplit(url)
        host = (parsed.hostname or "").lower().rstrip(".")
        if parsed.scheme != "https" or not host or parsed.username or parsed.password:
            return False
        if parsed.port not in (None, 443):
            return False
        try:
            ipaddress.ip_address(host)
            return False
        except ValueError:
            pass
        return host in HOST_ALLOWLIST
    except ValueError:
        return False


class SafeRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not permitted_url(newurl):
            raise ValueError("Rejected image redirect outside allowlisted HTTPS hosts")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def download_image(url):
    if not permitted_url(url):
        return None
    opener = build_opener(SafeRedirects())
    try:
        request = Request(
            url, headers={"User-Agent": "Collection-Inventory-OGP/1.0",
                          "Accept": "image/avif,image/webp,image/png,image/jpeg,image/*;q=0.7"},
        )
        with opener.open(request, timeout=6) as response:
            if not permitted_url(response.geturl()):
                return None
            payload = response.read(MAX_DOWNLOAD_BYTES + 1)
        if len(payload) > MAX_DOWNLOAD_BYTES:
            return None
        with Image.open(BytesIO(payload)) as image:
            if image.width * image.height > MAX_SOURCE_PIXELS:
                return None
            return ImageOps.exif_transpose(image).convert("RGB")
    except (OSError, ValueError, UnidentifiedImageError, SyntaxError) as exc:
        print("Skipped unavailable artwork:", urlsplit(url).hostname, type(exc).__name__)
        return None


def candidates(catalog):
    """Prefer distinct, recognisable owned titles; use only real catalog images."""
    items = [
        item for item in catalog.get("items", [])
        if item.get("category") == "ゲームソフト"
        and item.get("ownership") == "所有"
        and item.get("cover")
        and permitted_url(item["cover"])
    ]
    priority = {f"INV-{n:03d}": i for i, n in enumerate(FEATURED_ISSUES)}
    items.sort(key=lambda x: (
        priority.get(x.get("id"), 10000),
        str(x.get("title", "")), str(x.get("id", "")),
    ))
    seen_titles = set()
    for item in items:
        title = item.get("title") or ""
        if not title or title in seen_titles:
            continue
        seen_titles.add(title)
        yield item


def choose_artwork(catalog, fetch=download_image, limit=9):
    results = []
    for item in candidates(catalog):
        sources = [item["cover"]]
        fallback = item.get("cover_fallback", "")
        if fallback and fallback != sources[0]:
            sources.append(fallback)
        image = None
        for source in sources:
            image = fetch(source)
            if image is not None:
                break
        if image is not None:
            results.append((item, image))
            print("OGP artwork:", item["id"], item.get("title", ""))
        if len(results) >= limit:
            break
    return results


def font(size, *, bold=False, japanese=False):
    if japanese:
        paths = (
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc" if bold
            else "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc" if bold
            else "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        )
    else:
        paths = (
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
            else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        )
    for path in paths:
        if Path(path).is_file():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def render(artwork):
    """Create a 1200×630 RGB JPEG-free PNG for broad social crawler support."""
    canvas = Image.new("RGB", SIZE, (13, 24, 40))
    draw = ImageDraw.Draw(canvas)
    for y in range(SIZE[1]):
        t = y / (SIZE[1] - 1)
        draw.line((0, y, SIZE[0], y),
                  fill=(int(13 + 7*t), int(24 + 13*t), int(40 + 18*t)))

    # Restrained layout: product photography, not invented cover art or ornaments.
    draw.rectangle((0, 0, 10, 630), fill=(197, 150, 88))
    draw.rectangle((57, 86, 115, 90), fill=(224, 177, 113))
    draw.text((61, 47), "PERSONAL COLLECTION ARCHIVE",
              font=font(20, bold=True), fill=(224, 177, 113))

    draw.text((58, 194), "Collection", font=font(69, bold=True),
              fill=(249, 248, 244), stroke_width=0)
    draw.text((58, 280), "Inventory", font=font(77, bold=True),
              fill=(224, 177, 113), stroke_width=0)
    draw.line((62, 393, 515, 393), fill=(136, 109, 76), width=2)
    draw.text((62, 427), "ゲーム・書籍・音楽・映像",
              font=font(25, japanese=True), fill=(229, 234, 243))
    draw.text((62, 468), "好きなものを、ひとつずつ。",
              font=font(20, japanese=True), fill=(168, 183, 202))
    draw.text((62, 561), "GAMES   /   BOOKS   /   MUSIC   /   VIDEO",
              font=font(15, bold=True), fill=(166, 184, 206))

    start_x, start_y = 642, 35
    cell_width, cell_height = 159, 174
    gap_x, gap_y = 17, 18
    draw.rounded_rectangle((627, 20, 1162, 609), radius=15,
                           outline=(78, 90, 108), width=2,
                           fill=(16, 29, 46))
    for position in range(9):
        col, row = position % 3, position // 3
        x = start_x + col*(cell_width+gap_x)
        y = start_y + row*(cell_height+gap_y)
        draw.rounded_rectangle((x+3, y+6, x+cell_width+3, y+cell_height+6),
                               radius=8, fill=(8, 17, 29))
        draw.rounded_rectangle((x, y, x+cell_width, y+cell_height),
                               radius=8, fill=(33, 47, 65),
                               outline=(85, 104, 127), width=2)
        if position >= len(artwork):
            # Honest empty display slots rather than invented/fake jackets.
            draw.line((x+24, y+cell_height//2,
                       x+cell_width-24, y+cell_height//2), fill=(59, 76, 98), width=2)
            continue
        _, source = artwork[position]
        tile = ImageOps.contain(source, (cell_width-12, cell_height-12),
                                method=Image.Resampling.LANCZOS)
        image_x = x + (cell_width-tile.width)//2
        image_y = y + (cell_height-tile.height)//2
        canvas.paste(tile, (image_x, image_y))
    return canvas


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="site/data/collection.json")
    parser.add_argument("--output", default="site/ogp.png")
    args = parser.parse_args()
    with open(args.input, encoding="utf-8") as file:
        catalog = json.load(file)
    artwork = choose_artwork(catalog)
    if len(artwork) < 6:
        raise RuntimeError(
            f"Only {len(artwork)} verified, downloadable game covers; "
            "refusing to publish a misleading or mostly empty OGP grid."
        )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    render(artwork).save(output, format="PNG", optimize=True)
    print(f"Rendered {output}: {SIZE[0]}x{SIZE[1]}, {len(artwork)} real game images")


if __name__ == "__main__":
    main()
