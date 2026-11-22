"""Regression tests for reliable book artwork in GitHub Pages."""
from io import BytesIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from PIL import Image
from scripts.cache_book_covers import BOOK_ISSUES, encode_jpeg, update_catalog


class CacheBookCoversTests(unittest.TestCase):
    @staticmethod
    def sample_image():
        out = BytesIO()
        Image.new("RGB", (220, 330), (35, 60, 90)).save(out, "PNG")
        return out.getvalue()

    def test_valid_images_are_cached_and_catalog_points_to_local_files(self):
        with TemporaryDirectory() as root:
            site = Path(root) / "site"
            catalog_path = site / "data" / "collection.json"
            catalog_path.parent.mkdir(parents=True)
            original = {"items": [
                {"title": f"Book {n}", "category": "書籍",
                 "issue_url": f"https://github.com/mao2009/Collection-Inventory/issues/{n}",
                 "cover": f"https://books.example.org/{n}.png", "cover_source": "issue"}
                for n in sorted(BOOK_ISSUES)
            ]}
            original["items"].append({"title": "Game", "category": "ゲームソフト",
                "issue_url": "https://github.com/mao2009/Collection-Inventory/issues/1",
                "cover": "https://games.example.org/1.jpg"})
            catalog_path.write_text(json.dumps(original), encoding="utf-8")
            with patch("scripts.cache_book_covers.fetch_image", return_value=self.sample_image()) as getter:
                update_catalog(catalog_path, site)
            self.assertEqual(getter.call_count, len(BOOK_ISSUES))
            output = json.loads(catalog_path.read_text(encoding="utf-8"))
            for issue, item in zip(sorted(BOOK_ISSUES), output["items"]):
                self.assertEqual(item["cover"], f"./covers/books/{issue}.jpg")
                self.assertEqual(item["cover_source"], "local")
                self.assertTrue((site / "covers" / "books" / f"{issue}.jpg").is_file())
                with Image.open(site / "covers" / "books" / f"{issue}.jpg") as image:
                    self.assertEqual(image.format, "JPEG")
            self.assertEqual(output["items"][-1], original["items"][-1])

    def test_reject_non_image_bytes(self):
        with self.assertRaises((OSError, ValueError)):
            encode_jpeg(b"<html>This is an error page</html>")

    def test_reject_placeholder_size(self):
        img = BytesIO()
        Image.new("RGB", (1, 1)).save(img, "PNG")
        with self.assertRaisesRegex(ValueError, "too small"):
            encode_jpeg(img.getvalue())


if __name__ == "__main__":
    unittest.main()
