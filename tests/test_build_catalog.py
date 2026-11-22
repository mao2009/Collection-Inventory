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
        self.assertEqual(item["cover_source"], "curated")
        self.assertEqual(item["cover"], "https://raw.githubusercontent.com/SvenGDK/PSMT-Covers/main/PS3/BLJM61041.JPG")

    def test_verified_vita_reference_cover(self):
        item = inventory_item(self.issue(
            78, "- タイトル：朧村正\n- 機種：PlayStation Vita\n"
        ))
        self.assertEqual(item["cover_source"], "curated")
        self.assertTrue(item["cover"].endswith("/PSVita/PCSG00150.png"))
        self.assertEqual(
            inventory_item(self.issue(90, "- タイトル：朧村正\n- 機種：Wii\n"))["cover_source"],
            "libretro",
        )

    def test_psp_reference_cover(self):
        item = inventory_item(self.issue(
            75, "- タイトル：ロックマンDASH 鋼の冒険心\n- 機種：PSP\n"
        ))
        self.assertEqual(item["cover_source"], "curated")
        self.assertTrue(item["cover"].endswith("/Covers/PSP/ULJM05030.png"))

    def test_xbox_reference_cover_and_duplicate_copy(self):
        for number in (82, 133):
            item = inventory_item(self.issue(
                number,
                "- タイトル：アーマード・コア フォーアンサー\n"
                "- 機種：Xbox 360\n"
            ))
            self.assertEqual(item["cover_source"], "curated")
            self.assertTrue(item["cover"].endswith("/titles/465307DA/artwork/boxart.jpg"))

    def test_issue_image_precedes_supplemental_cover(self):
        item = inventory_item(self.issue(
            114,
            "- タイトル：ドラゴンズクラウン\n"
            "- 機種：PlayStation 3\n"
            "- 画像URL：https://example.org/owned.jpg\n"
        ))
        self.assertEqual(item["cover_source"], "issue")
        self.assertEqual(item["cover"], "https://example.org/owned.jpg")

    def test_persona_fes_append_cover_is_not_standard(self):
        common = "- タイトル：ペルソナ3 フェス\n- 機種：PlayStation 2\n"
        normal = inventory_item(self.issue(123, common + "- エディション：通常版（単独起動版）\n"))
        append = inventory_item(self.issue(124, common + "- エディション：アペンド版\n"))
        best = inventory_item(self.issue(125, common + "- エディション：PlayStation 2 the Best\n"))
        self.assertTrue(normal["cover"].endswith("/SLPM-66690.jpg"))
        self.assertTrue(append["cover"].endswith("/SLPM-66689.jpg"))
        self.assertTrue(best["cover"].endswith("/SLPM-74277.jpg"))
        self.assertEqual(len({normal["cover"], append["cover"], best["cover"]}), 3)

    def test_persona_best_without_verified_art_does_not_fall_back(self):
        for title, platform, edition in (
            ("ペルソナ4", "PlayStation 2", "PlayStation 2 the Best"),
            ("ペルソナ3 ポータブル", "PSP", "PSP the Best"),
        ):
            item = inventory_item(self.issue(
                136, f"- タイトル：{title}\n- 機種：{platform}\n- エディション：{edition}\n"
            ))
            self.assertEqual(item["cover"], "")
            self.assertEqual(item["cover_source"], "")

    def test_persona_explicit_issue_cover_takes_precedence_over_edition_art(self):
        item = inventory_item(self.issue(
            124,
            "- タイトル：ペルソナ3 フェス\n- 機種：PlayStation 2\n"
            "- エディション：アペンド版\n"
            "- 画像URL：https://example.org/actual-append.jpg\n"
        ))
        self.assertEqual(item["cover"], "https://example.org/actual-append.jpg")
        self.assertEqual(item["cover_source"], "issue")

    def test_maken_shao_three_distinct_editions(self):
        base = "- タイトル：魔剣爻\n- 機種：PlayStation 2\n"
        cases = {
            "初回限定版": "SLPS-25042.jpg",
            "通常版": "SLPS-25043.jpg",
            "アトラス・ベストコレクション": "SLPM-65144.jpg",
        }
        urls = []
        for edition, filename in cases.items():
            item = inventory_item(self.issue(
                139, base + f"- エディション：{edition}\n"
            ))
            self.assertEqual(item["cover_source"], "curated")
            self.assertTrue(item["cover"].endswith("/" + filename))
            urls.append(item["cover"])
        self.assertEqual(len(set(urls)), 3)

    def test_maken_shao_issue_image_remains_authoritative(self):
        item = inventory_item(self.issue(
            34,
            "- タイトル：魔剣爻\n- 機種：PlayStation 2\n"
            "- エディション：初回限定版\n"
            "![現物写真](https://example.org/actual.jpg)\n",
        ))
        self.assertEqual(item["cover_source"], "issue")
        self.assertEqual(item["cover"], "https://example.org/actual.jpg")

    def test_sfc_shin_megami_tensei_ii_owns_three_separate_lots(self):
        lot_cases = (
            (98, "初期ロット"),
            (141, "2次ロット"),
            (142, "3次ロット"),
        )
        issues = [
            self.issue(
                number,
                "- タイトル：真・女神転生II\n"
                "- 分類：ゲームソフト\n"
                "- 機種：スーパーファミコン\n"
                + f"- エディション：{lot}\n- ロット：{lot}\n",
            )
            for number, lot in lot_cases
        ]
        exported = build(issues)["items"]
        self.assertEqual(len(exported), 3)
        self.assertEqual({item["edition"] for item in exported}, {x[1] for x in lot_cases})
        self.assertEqual({item["platform"] for item in exported}, {"スーパーファミコン"})
        self.assertEqual({item["id"] for item in exported}, {"INV-098", "INV-141", "INV-142"})
        self.assertEqual(len({item["cover"] for item in exported}), 1)
        self.assertEqual(exported[0]["cover_source"], "libretro")

    def test_sfc_last_bible_iii_uses_verified_reference_cover(self):
        item = inventory_item(self.issue(
            143,
            "- タイトル：ラストバイブルIII\n"
            "- 分類：ゲームソフト\n"
            "- 機種：スーパーファミコン\n"
            "- 所持：所有中（ユーザー申告）\n",
        ))
        self.assertEqual(item["title"], "ラストバイブルIII")
        self.assertEqual(item["platform"], "スーパーファミコン")
        self.assertTrue(item["cover"].endswith("/Last%20Bible%20III%20%28Japan%29.png"))
        self.assertEqual(item["cover_source"], "libretro")

    def test_sfc_misidentified_majin_tensei_ii_excluded_after_retraction(self):
        item = self.issue(
            102,
            "- 旧登録タイトル：魔神転生II\n"
            "- 機種：スーパーファミコン\n"
            "- 所有：未所持\n"
            "- 正しく所持しているタイトル：ラストバイブルIII\n",
            title="[未所持・誤認訂正] 魔神転生II（スーパーファミコン）",
            labels=[],
        )
        self.assertIsNone(inventory_item(item))
        self.assertEqual(build([item])["items"], [])

    def test_shelf_reference_covers_are_exact_platform_matches(self):
        examples = {
            "オーディンスフィア": "Odin%20Sphere%20%28Japan%29.png",
            "グローランサーII": "Growlanser%20II%20-%20The%20Sense%20of%20Justice%20%28Japan%29.png",
            "グローランサーIII": "Growlanser%20III%20-%20The%20Dual%20Darkness%20%28Japan%29.png",
            "幻想水滸伝V": "Gensou%20Suikoden%20V%20%28Japan%29.png",
            "ステラデウス": "Stella%20Deus%20%28Japan%29.png",
        }
        for title, filename in examples.items():
            item = inventory_item(self.issue(180, f"- タイトル：{title}\n- 機種：PlayStation 2\n"))
            self.assertEqual(item["cover_source"], "libretro")
            self.assertTrue(item["cover"].endswith(filename))
        # Only the PS3 game titled "レイヴスラシル" has its own PS3 cover;
        # the original PS2 game's plain title must not inherit that image.
        self.assertEqual(
            inventory_item(self.issue(
                181, "- タイトル：オーディンスフィア\n- 機種：PlayStation 3\n"
            ))["cover_source"],
            "",
        )
        self.assertEqual(
            inventory_item(self.issue(
                182, "- タイトル：オーディンスフィア レイヴスラシル\n- 機種：PlayStation 3\n"
            ))["cover_source"],
            "curated",
        )

    def test_curated_kana_readings_for_gojuon_sorting(self):
        examples = {
            "真・女神転生II": "シンメガミテンセイ2",
            "幻想水滸伝III": "ゲンソウスイコデン3",
            "魔剣爻": "マケンシャオ",
            "BAROQUE 歪んだ妄想": "バロック ユガンダモウソウ",
            "BUSIN ～Wizardry Alternative～": "ブシン ウィザードリィオルタナティブ",
            "DIGITAL DEVIL SAGA アバタール・チューナー": "デジタルデビルサーガ アバタールチューナー",
        }
        for title, expected in examples.items():
            item = inventory_item(self.issue(180, f"- タイトル：{title}\n- 機種：PlayStation 2\n"))
            self.assertEqual(item["reading"], expected)

    def test_issue_specific_reading_overrides_curated_dictionary(self):
        item = inventory_item(self.issue(
            180, "- タイトル：真・女神転生II\n- 読み：シンメガテンツー\n"
        ))
        self.assertEqual(item["reading"], "シンメガテンツー")
        fallback = inventory_item(self.issue(
            181, "- タイトル：カナヨミミトウロク\n"
        ))
        self.assertEqual(fallback["reading"], "カナヨミミトウロク")

    def test_photo_audited_ps2_titles_and_duplicate_physical_copies(self):
        titles = [
            ("グローランサーII", 151),
            ("グローランサーIII", 152),
            ("幻想水滸伝III", 157),
            ("DIGITAL DEVIL SAGA アバタール・チューナー", 170),
            ("FRONT MISSION 4", 168),
            ("FRONT MISSION 4", 169),
        ]
        issues = [
            self.issue(number, f"- タイトル：{title}\n- 機種：PlayStation 2\n")
            for title, number in titles
        ]
        items = build(issues)["items"]
        self.assertEqual(len(items), 6)
        self.assertEqual(len([item for item in items if item["title"] == "FRONT MISSION 4"]), 2)
        self.assertEqual(len({item["id"] for item in items}), 6)

    def test_unknown_game_is_not_given_wrong_artwork(self):
        item = inventory_item(self.issue(
            225, "- タイトル：架空のタイトル\n- 機種：PSP\n"
        ))
        self.assertEqual(item["cover"], "")
        self.assertEqual(item["cover_source"], "")


if __name__ == "__main__":
    unittest.main()
