"""Offline tests for share-preview artwork, requiring no network or user media."""
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from scripts.generate_ogp import (
    SIZE, candidates, choose_artwork, permitted_url, render,
)


def owned(number, title, platform="PlayStation 2", category="ゲームソフト",
          cover="https://raw.githubusercontent.com/example/cover.jpg"):
    return {
        "id": f"INV-{number:03d}", "title": title, "platform": platform,
        "category": category, "ownership": "所有", "cover": cover,
    }


class OGPTests(unittest.TestCase):
    def test_only_real_owned_games_with_allowlisted_cover_urls(self):
        catalog = {"items": [
            owned(217, "Metaphor"),
            owned(100, "Other", category="ポスター"),
            owned(71, "Sold", cover="http://example.com/image.jpg"),
            {**owned(28, "No longer owned"), "ownership": "譲渡・売却済み"},
            owned(4, "Maniax"),
            owned(5, "Maniax"),  # No duplicate-title promotion.
        ]}
        self.assertEqual(
            [item["id"] for item in candidates(catalog)],
            ["INV-217", "INV-004"],
        )

    def test_reject_untrusted_and_non_https_media(self):
        self.assertTrue(permitted_url(
            "https://raw.githubusercontent.com/libretro-thumbnails/X.png"))
        for url in [
            "http://raw.githubusercontent.com/img.png",
            "https://localhost/cover.png",
            "https://127.0.0.1/cover.png",
            "https://raw.githubusercontent.com.evil.test/cover.png",
            "https://username:password@raw.githubusercontent.com/cover.png",
            "https://raw.githubusercontent.com:1234/cover.png",
        ]:
            with self.subTest(url=url):
                self.assertFalse(permitted_url(url))

    def test_uses_actual_cover_images_and_falls_back(self):
        primary = "https://raw.githubusercontent.com/example/main.jpg"
        backup = "https://shared.fastly.steamstatic.com/backup.jpg"
        records = [owned(217, "A"), {**owned(4, "B"), "cover_fallback": backup}]
        asked = []

        def downloader(url):
            asked.append(url)
            if url == primary and len(asked) > 1:
                return None
            return Image.new("RGB", (100, 160), (190, 38, 40))

        selected = choose_artwork({"items": records}, fetch=downloader, limit=2)
        self.assertEqual(len(selected), 2)
        self.assertEqual(asked, [primary, primary, backup])

    def test_png_dimensions_and_no_generated_mock_covers(self):
        records = [
            (owned(n, f"Game {n}"), Image.new("RGB", (130, 200), (x*20, 80, 130)))
            for x, n in enumerate([217, 218, 220, 223, 224, 4, 28, 100, 97])
        ]
        rendered = render(records)
        self.assertEqual(rendered.size, SIZE)
        self.assertEqual(rendered.mode, "RGB")
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "ogp.png"
            rendered.save(path, format="PNG")
            with Image.open(path) as verified:
                self.assertEqual(verified.size, (1200, 630))
                self.assertEqual(verified.format, "PNG")


if __name__ == "__main__":
    unittest.main()
