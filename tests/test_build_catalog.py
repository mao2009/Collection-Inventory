import unittest

from scripts.build_catalog import build, fields_from_body, inventory_item, obi_status, platform_name


class CatalogTests(unittest.TestCase):
    def issue(self, number, body, title="[所有] ゲーム", labels=None):
        return {
            "number": number,
            "title": title,
            "body": body,
            "labels": [{"name": label} for label in (labels if labels is not None else ["所有"])],
        }

    def test_original_issue(self):
        body = """## 基本情報
- 管理番号：INV-028
- タイトル：女神異聞録ペルソナ
- 分類：ゲームソフト
- 機種：PlayStation（PS1）
- エディション：通常版
- 製品型番（ユーザー申告）：SLPS-00500
- 帯：あり（ユーザー申告）
- 購入価格：6,000円
- 保管場所：自宅
![参考](https://example.org/cover.jpg)
"""
        item = inventory_item(self.issue(28, body))
        self.assertEqual(item["id"], "INV-028")
        self.assertEqual(item["title"], "女神異聞録ペルソナ")
        self.assertEqual(item["platform"], "PlayStation")
        self.assertEqual(item["obi"], "yes")
        self.assertEqual(item["serial"], "SLPS-00500")
        self.assertEqual(item["cover"], "https://example.org/cover.jpg")
        self.assertNotIn("購入価格", str(item))
        self.assertNotIn("保管場所", str(item))
        self.assertNotIn("6,000", str(item))

    def test_issue_form(self):
        body = """### タイトル

プリンセスクラウン

### カテゴリ

ゲームソフト

### プラットフォーム・対応機種

セガサターン

### 所持状態

所有

### 画像URL（任意）

https://example.org/game.jpg
"""
        item = inventory_item(self.issue(42, body, title="[登録] ", labels=[]))
        self.assertEqual(item["id"], "INV-042")
        self.assertEqual(item["category"], "ゲームソフト")
        self.assertEqual(item["platform"], "セガサターン")
        self.assertEqual(item["ownership"], "所有")

    def test_non_inventory_and_pull_request_excluded(self):
        self.assertIsNone(inventory_item(self.issue(4, "Bug report", title="Website bug", labels=[])))
        issue = self.issue(4, "- 管理番号：INV-004\n- タイトル：X")
        issue["pull_request"] = {}
        self.assertEqual(build([issue])["items"], [])

    def test_identity_per_copy_and_duplicate_guard(self):
        a = self.issue(1, "- 管理番号：INV-001\n- タイトル：真・女神転生II")
        b = self.issue(2, "- 管理番号：INV-002\n- タイトル：真・女神転生II")
        self.assertEqual(len(build([a, b])["items"]), 2)
        b["body"] = "- 管理番号：INV-001\n- タイトル：真・女神転生II"
        with self.assertRaises(ValueError):
            build([a, b])

    def test_unsafe_cover_rejected(self):
        item = inventory_item(self.issue(8, "- 管理番号：INV-008\n- タイトル：ゲーム\n- 画像URL：https://example.org@evil.org/x"))
        self.assertEqual(item["cover"], "")
        item = inventory_item(self.issue(8, "- 管理番号：INV-008\n- タイトル：ゲーム\n- 画像URL：javascript:alert(1)"))
        self.assertEqual(item["cover"], "")

    def test_platform_and_obi(self):
        self.assertEqual(platform_name("PlayStation 2"), "PlayStation 2")
        self.assertEqual(platform_name("PlayStation（PS1）"), "PlayStation")
        self.assertEqual(obi_status("未確認"), "unknown")
        self.assertEqual(obi_status("欠品"), "no")
        self.assertEqual(obi_status("帯付き"), "yes")

    def test_form_fields_not_mixed_with_bullets(self):
        data = fields_from_body("- 管理番号: INV-013\n### タイトル\n\nクロノ・クロス\n\n### 状態\n\n- 帯：未確認")
        self.assertEqual(data["タイトル"], "クロノ・クロス")
        self.assertEqual(data["管理番号"], "INV-013")

    def test_curated_reference_cover_used_when_issue_has_none(self):
        item = inventory_item(self.issue(
            38,
            "- タイトル：真・女神転生 STRANGE JOURNEY\n"
            "- 機種：ニンテンドーDS\n"
        ))
        self.assertEqual(item["cover_source"], "libretro")
        self.assertIn("Nintendo_-_Nintendo_DS", item["cover"])
        self.assertTrue(item["cover"].endswith("Shin%20Megami%20Tensei%20-%20Strange%20Journey%20%28Japan%29.png"))

    def test_explicit_issue_cover_takes_precedence(self):
        item = inventory_item(self.issue(
            38,
            "- タイトル：真・女神転生 STRANGE JOURNEY\n"
            "- 機種：ニンテンドーDS\n"
            "- 画像URL：https://example.org/my-cover.png\n"
        ))
        self.assertEqual(item["cover_source"], "issue")
        self.assertEqual(item["cover"], "https://example.org/my-cover.png")

    def test_verified_ps3_reference_cover(self):
        item = inventory_item(self.issue(
            114,
            "- タイトル：ドラゴンズクラウン\n- 機種：PlayStation 3\n"
        ))
        self.assertEqual(item["cover_source"], "psmt")
        self.assertEqual(item["cover"], "https://raw.githubusercontent.com/SvenGDK/PSMT-Covers/main/PS3/BLJM61041.JPG")

    def test_verified_vita_reference_cover(self):
        item = inventory_item(self.issue(
            78, "- タイトル：朧村正\n- 機種：PlayStation Vita\n"
        ))
        self.assertEqual(item["cover_source"], "psmt")
        self.assertTrue(item["cover"].endswith("/PSVita/PCSG00150.png"))
        self.assertEqual(
            inventory_item(self.issue(90, "- タイトル：朧村正\n- 機種：Wii\n"))["cover_source"],
            "libretro",
        )

    def test_issue_image_precedes_supplemental_cover(self):
        item = inventory_item(self.issue(
            114,
            "- タイトル：ドラゴンズクラウン\n"
            "- 機種：PlayStation 3\n"
            "- 画像URL：https://example.org/owned.jpg\n"
        ))
        self.assertEqual(item["cover_source"], "issue")
        self.assertEqual(item["cover"], "https://example.org/owned.jpg")

    def test_unknown_game_is_not_given_wrong_artwork(self):
        item = inventory_item(self.issue(
            225, "- タイトル：架空のタイトル\n- 機種：PSP\n"
        ))
        self.assertEqual(item["cover"], "")
        self.assertEqual(item["cover_source"], "")


if __name__ == "__main__":
    unittest.main()
