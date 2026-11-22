"""Static share-control checks for buttons and branded assets."""
from html.parser import HTMLParser
from pathlib import Path
import unittest
from urllib.parse import parse_qs, urlparse
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parents[1] / "site"


class ShareParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.by_id = {}
        self.images = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.by_id[attrs["id"]] = (tag, attrs)
        if tag == "img" and attrs.get("src", "").startswith("./icons/"):
            self.images.append(attrs)


class ShareControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (ROOT / "index.html").read_text(encoding="utf-8")
        cls.js = (ROOT / "app.js").read_text(encoding="utf-8")
        cls.parser = ShareParser()
        cls.parser.feed(cls.html)

    def test_share_url_is_canonical_for_each_service(self):
        base = "https://mao2009.github.io/Collection-Inventory/"
        expected = {
            "share-line": ("social-plugins.line.me", "/lineit/share"),
            "share-x": ("x.com", "/intent/tweet"),
            "share-bluesky": ("bsky.app", "/intent/compose"),
            "share-facebook": ("www.facebook.com", "/sharer/sharer.php"),
        }
        for key, (hostname, path) in expected.items():
            with self.subTest(key=key):
                tag, attrs = self.parser.by_id[key]
                self.assertEqual(tag, "a")
                url = urlparse(attrs["href"])
                self.assertEqual((url.scheme, url.hostname, url.path), ("https", hostname, path))
                query = parse_qs(url.query)
                values = query.get("url", []) + query.get("u", []) + query.get("text", [])
                self.assertTrue(any(base in value for value in values))
                self.assertEqual(attrs["target"], "_blank")
                self.assertIn("noopener", attrs["rel"])
                self.assertTrue(attrs["aria-label"])

    def test_real_logos_are_local_vector_assets(self):
        images = {x["src"] for x in self.parser.images}
        for name in ("line", "x", "bluesky", "facebook"):
            path = f"./icons/{name}.svg"
            self.assertIn(path, images)
            root = ElementTree.parse(ROOT / "icons" / f"{name}.svg").getroot()
            self.assertTrue(root.tag.endswith("svg"))
            self.assertEqual(root.attrib["viewBox"], "0 0 24 24")
            self.assertTrue(any(child.tag.endswith("path") for child in root))

    def test_native_share_and_copy_have_accessible_controls(self):
        for name in ("share-copy", "share-native"):
            tag, attrs = self.parser.by_id[name]
            self.assertEqual(tag, "button")
            self.assertEqual(attrs["type"], "button")
            self.assertTrue(attrs["aria-label"])
        self.assertIn('id="share-status" role="status"', self.html)
        self.assertIn("await navigator.clipboard.writeText(SHARE_URL)", self.js)
        self.assertIn("await navigator.share(", self.js)
        self.assertIn('if (typeof navigator.share === "function")', self.js)


if __name__ == "__main__":
    unittest.main()
