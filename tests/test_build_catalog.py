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

    def test_official_genroku_kaikitan_package_art_is_not_standard_muramasa(self):
        title = "朧村正＋元禄怪奇譚 DLC全四篇プロダクトコード入りパッケージ"
        item = inventory_item(self.issue(
            78, f"- タイトル：{title}\n- 機種：PlayStation Vita\n"
        ))
        self.assertEqual(item["cover_source"], "curated")
        self.assertEqual(item["cover"], "https://www.marv.jp/uploads/title/687/67aecdff316a0.jpg")
        self.assertTrue(item["reading"].startswith("オボロムラマサ"))
        self.assertNotIn("PCSG00150", item["cover"])
        wii = inventory_item(self.issue(
            120, "- タイトル：朧村正\n- 機種：Wii\n"
        ))
        self.assertEqual(wii["cover_source"], "libretro")

    def test_p4_golden_vita_standard_and_best_covers_are_distinct(self):
        cases = [
            (79, "通常版", "PCSG00004.png"),
            (181, "PlayStation Vita the Best", "PCSG00563.png"),
        ]
        items = []
        for number, edition, filename in cases:
            item = inventory_item(self.issue(
                number, "- タイトル：ペルソナ4 ザ・ゴールデン\n"
                "- 機種：PlayStation Vita\n" + f"- エディション：{edition}\n"
            ))
            self.assertEqual(item["cover_source"], "curated")
            self.assertTrue(item["cover"].endswith("/PSVita/" + filename))
            self.assertEqual(item["reading"], "ペルソナ4 ザゴールデン")
            items.append(item)
        self.assertEqual(len(build([
            self.issue(number, "- タイトル：ペルソナ4 ザ・ゴールデン\n"
                       "- 機種：PlayStation Vita\n" + f"- エディション：{edition}\n")
            for number, edition, _ in cases
        ])["items"]), 2)
        self.assertNotEqual(items[0]["cover"], items[1]["cover"])

    def test_ps3_tomb_raider_reference_is_only_ps3(self):
        item = inventory_item(self.issue(
            180, "- タイトル：トゥームレイダー\n- 機種：PlayStation 3\n"
        ))
        self.assertEqual(item["cover_source"], "curated")
        self.assertTrue(item["cover"].endswith("/PS3/BLJM60557.JPG"))
        self.assertEqual(item["reading"], "トゥームレイダー")
        other = inventory_item(self.issue(
            182, "- タイトル：トゥームレイダー\n- 機種：PlayStation 2\n"
        ))
        self.assertNotEqual(other["cover"], item["cover"])

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

    def test_bofv_ico_limited_and_psp_titles_get_exact_platform_covers(self):
        cases = (
            (183, "ブレス オブ ファイアV ドラゴンクォーター", "PlayStation 2",
             "/ps2-covers/main/covers/default/SLPM-65196.jpg",
             "ブレスオブファイア5 ドラゴンクォーター"),
            (184, "ICO/ワンダと巨像 Limited Box", "PlayStation 3",
             "/PS3/BCJS30073.JPG", "イコ ワンダトキョゾウ リミテッドボックス"),
            (185, "Another Century's Episode Portable", "PSP",
             "/Covers/PSP/ULJS00322.png", "アナザーセンチュリーズエピソード ポータブル"),
            (186, "機動戦士ガンダム ギレンの野望 アクシズの脅威V", "PSP",
             "/Covers/PSP/ULJS00178.png",
             "キドウセンシガンダム ギレンノヤボウ アクシズノキョウイ5"),
        )
        issues = []
        for number, title, platform, suffix, reading in cases:
            issue = self.issue(
                number,
                f"- タイトル：{title}\n- 分類：ゲームソフト\n- 機種：{platform}\n"
            )
            item = inventory_item(issue)
            self.assertEqual(item["cover_source"], "curated")
            self.assertTrue(item["cover"].endswith(suffix), title)
            self.assertEqual(item["reading"], reading)
            issues.append(issue)
        self.assertEqual(len(build(issues)["items"]), 4)

    def test_ico_limited_box_is_one_set_not_two_separate_copies(self):
        item = inventory_item(self.issue(
            184,
            "- タイトル：ICO/ワンダと巨像 Limited Box\n"
            "- 機種：PlayStation 3\n"
            "- エディション：Limited Box（数量限定セット）\n"
            "- 個体：限定セット1箱\n",
        ))
        self.assertEqual(item["title"], "ICO/ワンダと巨像 Limited Box")
        self.assertEqual(item["edition"], "Limited Box（数量限定セット）")
        self.assertEqual(item["platform"], "PlayStation 3")

    def test_nine_standard_and_deluxe_are_separate_owned_copies(self):
        cases = (
            (81, "通常版（スタンドアローン版）",
             "Shin%20Megami%20Tensei%20-%20NINE%20%28Japan%29.png"),
            (188, "限定デラックスパック", "m9000003newfront.jpg"),
        )
        issues = []
        images = set()
        for number, edition, image_name in cases:
            issue = self.issue(
                number,
                "- タイトル：真・女神転生 NINE\n"
                "- 分類：ゲームソフト\n"
                "- 機種：Xbox\n"
                + f"- エディション：{edition}\n",
            )
            item = inventory_item(issue)
            self.assertEqual(item["edition"], edition)
            self.assertEqual(item["cover_source"], "curated")
            self.assertTrue(item["cover"].endswith(image_name))
            self.assertEqual(item["reading"], "シンメガミテンセイ ナイン")
            images.add(item["cover"])
            issues.append(issue)
        self.assertEqual(len(images), 2)
        self.assertEqual(len(build(issues)["items"]), 2)

    def test_blue_dragon_x360_reference_cover_and_kana(self):
        item = inventory_item(self.issue(
            189,
            "- タイトル：ブルードラゴン\n"
            "- 機種：Xbox 360\n"
            "- エディション：未確認\n",
        ))
        self.assertEqual(item["cover_source"], "curated")
        self.assertTrue(item["cover"].endswith("/titles/4D5307DF/artwork/boxart.jpg"))
        self.assertEqual(item["reading"], "ブルードラゴン")
        self.assertEqual(item["platform"], "Xbox 360")
        self.assertEqual(
            inventory_item(self.issue(
                190, "- タイトル：ブルードラゴン\n- 機種：Xbox\n"
            ))["cover"],
            "",
        )

    def test_new_sfc_wonder_project_j_and_shin_momotaro_are_distinct(self):
        cases = (
            (
                191, "ワンダープロジェクトJ 機械の少年ピーノ",
                "Wonder%20Project%20J%20-%20Kikai%20no%20Shounen%20Pino%20%28Japan%29.png",
                "ワンダープロジェクトジェイ キカイノショウネンピーノ",
            ),
            (
                192, "新桃太郎伝説",
                "Shin%20Momotarou%20Densetsu%20%28Japan%29.png",
                "シンモモタロウデンセツ",
            ),
        )
        issues = []
        for number, title, file_name, expected_reading in cases:
            issue = self.issue(
                number, f"- タイトル：{title}\n"
                "- 分類：ゲームソフト\n"
                "- 機種：スーパーファミコン\n"
                "- エディション：未確認\n",
            )
            item = inventory_item(issue)
            self.assertEqual(item["platform"], "スーパーファミコン")
            self.assertEqual(item["cover_source"], "libretro")
            self.assertTrue(item["cover"].endswith(file_name))
            self.assertEqual(item["reading"], expected_reading)
            issues.append(issue)
        self.assertEqual(len(build(issues)["items"]), 2)

    def test_saturn_soul_hackers_two_copies_without_obi(self):
        copies = [
            self.issue(n,
                "- タイトル：デビルサマナー ソウルハッカーズ\n"
                "- 分類：ゲームソフト\n"
                "- 機種：セガサターン\n"
                "- エディション：未確認\n"
                "- 帯：なし（ユーザー申告）\n")
            for n in (87, 194)
        ]
        data = build(copies)["items"]
        self.assertEqual(len(data), 2)
        self.assertEqual({x["id"] for x in data}, {"INV-087", "INV-194"})
        for item in data:
            self.assertEqual(item["obi"], "no")
            self.assertEqual(item["cover_source"], "libretro")
            self.assertTrue(item["cover"].endswith(
                "/Devil%20Summoner%20-%20Soul%20Hackers%20%28Japan%29.png"
            ))

    def test_saturn_akuma_zensho_second_volume_has_own_cover(self):
        item = inventory_item(self.issue(
            195,
            "- タイトル：デビルサマナー ソウルハッカーズ 悪魔全書 第二集\n"
            "- 分類：ゲームソフト\n"
            "- 機種：セガサターン\n"
            "- 帯：未確認\n"
        ))
        self.assertEqual(item["platform"], "セガサターン")
        self.assertEqual(item["obi"], "unknown")
        self.assertEqual(item["cover_source"], "libretro")
        self.assertTrue(item["cover"].endswith(
            "/Devil%20Summoner%20-%20Soul%20Hackers%20-%20Akuma%20Zensho%20Daini-shuu%20%28Japan%29.png"
        ))
        self.assertEqual(item["reading"],
            "デビルサマナー ソウルハッカーズ アクマゼンショ ダイニシュウ")

    def test_smt_iv_final_dedicated_cover_not_regular_iv(self):
        final = inventory_item(self.issue(
            49,
            "- タイトル：真・女神転生IV FINAL\n"
            "- 機種：ニンテンドー3DS\n"
            "- エディション：未確認\n"
        ))
        original = inventory_item(self.issue(
            48,
            "- タイトル：真・女神転生IV\n"
            "- 機種：ニンテンドー3DS\n"
            "- エディション：未確認\n"
        ))
        self.assertEqual(final["cover_source"], "curated")
        self.assertTrue(final["cover"].endswith(
            "/Shin%20Megami%20Tensei%20IV%20-%20Final%20%28Japan%29.png"
        ))
        self.assertTrue(original["cover"].endswith(
            "/Shin%20Megami%20Tensei%20IV%20%28Japan%29.png"
        ))
        self.assertNotEqual(final["cover"], original["cover"])

    def test_ds_caduceus_atlus_best_has_edition_specific_art(self):
        item = inventory_item(self.issue(
            44,
            "- タイトル：超執刀 カドゥケウス\n"
            "- 分類：ゲームソフト\n"
            "- 機種：ニンテンドーDS\n"
            "- エディション：アトラス ベスト コレクション\n",
        ))
        self.assertEqual(item["edition"], "アトラス ベスト コレクション")
        self.assertEqual(item["cover_source"], "curated")
        self.assertEqual(item["cover"],
            "https://item-shopping.c.yimg.jp/i/n/media-world_10202011001")
        self.assertEqual(item["reading"], "チョウシットウ カドゥケウス")
        standard = inventory_item(self.issue(
            244,
            "- タイトル：超執刀 カドゥケウス\n"
            "- 機種：ニンテンドーDS\n"
            "- エディション：通常版\n",
        ))
        self.assertNotEqual(standard["cover"], item["cover"])
        self.assertEqual(standard["cover"], "")

    def test_famicom_sanma_no_meitantei_art_and_gojuon(self):
        item = inventory_item(self.issue(
            197,
            "- タイトル：さんまの名探偵\n"
            "- 分類：ゲームソフト\n"
            "- 機種：ファミリーコンピュータ\n"
            "- エディション：未確認\n",
        ))
        self.assertEqual(item["cover_source"], "libretro")
        self.assertTrue(item["cover"].endswith(
            "/Sanma%20no%20Meitantei%20%28Japan%29.png"
        ))
        self.assertEqual(item["reading"], "サンマノメイタンテイ")
        self.assertEqual(item["platform"], "ファミリーコンピュータ")

    def test_legacy_pc_engine_titles_are_games_not_uncategorized(self):
        legacy = [
            self.issue(35,
                "- 管理番号: INV-035\n"
                "- 機種: PCエンジン\n"
                "- 分類: ゲームソフト\n"
                "- タイトル: 真・女神転生\n"),
            self.issue(36,
                "- 管理番号: INV-036\n"
                "- 機種: PCエンジン\n"
                "- 分類: ゲームソフト\n"
                "- タイトル: 天外魔境II 卍MARU\n"),
        ]
        items = build(legacy)["items"]
        self.assertEqual(len(items), 2)
        self.assertEqual({i["id"] for i in items}, {"INV-035", "INV-036"})
        self.assertEqual({i["category"] for i in items}, {"ゲームソフト"})
        self.assertEqual({i["platform"] for i in items}, {"PCエンジン"})

    def test_pce_gba_and_n64_own_titles_have_correct_platform_covers(self):
        cases = (
            (199, "イースI・II", "PCエンジン",
             "NEC_-_PC_Engine_CD_-_TurboGrafx-CD",
             "Ys%20I%20_%20II%20%28Japan%29.png", "イース1・2"),
            (200, "真・女神転生", "ゲームボーイアドバンス",
             "Nintendo_-_Game_Boy_Advance",
             "Shin%20Megami%20Tensei%20%28Japan%29.png", "シンメガミテンセイ"),
            (201, "真・女神転生II", "ゲームボーイアドバンス",
             "Nintendo_-_Game_Boy_Advance",
             "Shin%20Megami%20Tensei%20II%20%28Japan%29.png", "シンメガミテンセイ2"),
            (202, "ブレス オブ ファイア", "ゲームボーイアドバンス",
             "Nintendo_-_Game_Boy_Advance",
             "Breath%20of%20Fire%20-%20Ryuu%20no%20Senshi%20%28Japan%29.png",
             "ブレスオブファイア"),
            (203, "MOTHER 1+2", "ゲームボーイアドバンス",
             "Nintendo_-_Game_Boy_Advance",
             "Mother%201%2B2%20%28Japan%29.png", "マザー1+2"),
            (204, "ワンダープロジェクトJ2 コルロの森のジョゼット", "NINTENDO64",
             "Nintendo_-_Nintendo_64",
             "Wonder%20Project%20J2%20-%20Koruro%20no%20Mori%20no%20Jozet%20%28Japan%29.png",
             "ワンダープロジェクトジェイ2 コルロノモリノジョゼット"),
        )
        issues = []
        for number, title, platform, repository, image, reading in cases:
            issue = self.issue(
                number, f"- タイトル：{title}\n"
                "- 分類：ゲームソフト\n"
                + f"- 機種：{platform}\n"
                "- エディション：未確認\n",
            )
            item = inventory_item(issue)
            self.assertEqual(item["id"], f"INV-{number}")
            self.assertEqual(item["platform"], platform)
            self.assertEqual(item["category"], "ゲームソフト")
            self.assertEqual(item["cover_source"], "libretro")
            self.assertIn(repository, item["cover"])
            self.assertTrue(item["cover"].endswith(image), title)
            self.assertEqual(item["reading"], reading)
            issues.append(issue)
        self.assertEqual(len(build(issues)["items"]), 6)

    def test_same_title_gba_not_confused_with_sfc(self):
        gba = inventory_item(self.issue(
            200, "- タイトル：真・女神転生\n- 機種：ゲームボーイアドバンス\n"
        ))
        sfc = inventory_item(self.issue(
            97, "- タイトル：真・女神転生\n- 機種：スーパーファミコン\n"
        ))
        self.assertNotEqual(gba["platform"], sfc["platform"])
        self.assertNotEqual(gba["cover"], sfc["cover"])

    def test_unknown_game_is_not_given_wrong_artwork(self):
        item = inventory_item(self.issue(
            225, "- タイトル：架空のタイトル\n- 機種：PSP\n"
        ))
        self.assertEqual(item["cover"], "")
        self.assertEqual(item["cover_source"], "")


if __name__ == "__main__":
    unittest.main()
