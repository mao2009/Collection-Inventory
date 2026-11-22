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

    def test_photo_verified_nintendo_switch_shelf_catalog_entries(self):
        cases = (
            (206, "キャサリン・フルボディ for Nintendo Switch",
             "/ec_media_images/5150726-01.jpg",
             "キャサリン フルボディ フォーニンテンドースイッチ"),
            (207, "幻影異聞録♯FE Encore",
             "/images/productimage/fullscale/K0001187541.jpg",
             "ゲンエイイブンロク シャープエフイー アンコール"),
            (208, "十三機兵防衛圏",
             "/i/f/digitalisland_4984995905259",
             "ジュウサンキヘイボウエイケン"),
            (209, "真・女神転生V Vengeance",
             "/i/f/rd-lohaco_rj15719",
             "シンメガミテンセイ5 ヴェンジェンス"),
            (210, "RAIDOU Remastered: 超力兵団奇譚",
             "/beab1151f056d00ba8d3aba74970ab0b.jpg",
             "ライドウ リマスタード チョウリキヘイダンキタン"),
        )
        issues = []
        for number, title, suffix, reading in cases:
            issue = self.issue(
                number,
                f"- タイトル：{title}\n"
                "- 分類：ゲームソフト\n"
                "- 機種：Nintendo Switch\n"
                "- エディション：未確認\n",
            )
            item = inventory_item(issue)
            self.assertEqual(item["category"], "ゲームソフト")
            self.assertEqual(item["platform"], "Nintendo Switch")
            self.assertEqual(item["reading"], reading)
            self.assertEqual(item["cover_source"], "curated")
            self.assertTrue(item["cover"].endswith(suffix), title)
            self.assertEqual(item["id"], f"INV-{number:03}")
            issues.append(issue)
        self.assertEqual(len(build(issues)["items"]), 5)

    def test_card_summoner_is_game_boy_color_game_not_card_merchandise(self):
        issue = self.issue(
            211,
            "- タイトル：真・女神転生トレーディングカード カードサマナー\n"
            "- 分類：ゲームソフト\n"
            "- 機種：ゲームボーイカラー\n"
            "- エディション：未確認\n",
        )
        item = inventory_item(issue)
        self.assertEqual(item["category"], "ゲームソフト")
        self.assertEqual(item["platform"], "ゲームボーイカラー")
        self.assertEqual(item["cover_source"], "libretro")
        self.assertIn("Nintendo_-_Game_Boy_Color", item["cover"])
        self.assertTrue(item["cover"].endswith(
            "/Shin%20Megami%20Tensei%20Trading%20Card%20-%20Card%20Summoner%20%28Japan%29.png"
        ))
        self.assertEqual(
            item["reading"],
            "シンメガミテンセイ トレーディングカード カードサマナー",
        )

    def test_switch_raido_is_not_ps2_original_and_vengeance_is_not_base_v(self):
        raido = inventory_item(self.issue(
            210, "- タイトル：RAIDOU Remastered: 超力兵団奇譚\n"
                 "- 機種：Nintendo Switch\n"
        ))
        original = inventory_item(self.issue(
            131, "- タイトル：デビルサマナー 葛葉ライドウ対超力兵団\n"
                 "- 機種：PlayStation 2\n"
        ))
        self.assertNotEqual(raido["platform"], original["platform"])
        self.assertNotEqual(raido["cover"], original["cover"])
        vengeance = inventory_item(self.issue(
            209, "- タイトル：真・女神転生V Vengeance\n"
                 "- 機種：Nintendo Switch\n"
        ))
        base_game = inventory_item(self.issue(
            299, "- タイトル：真・女神転生V\n"
                 "- 機種：Nintendo Switch\n"
        ))
        self.assertNotEqual(vengeance["title"], base_game["title"])
        self.assertNotEqual(vengeance["cover"], base_game["cover"])

    def test_vita_persona4_dancing_limited_and_no_obi(self):
        limited = inventory_item(self.issue(
            80,
            "- タイトル：ペルソナ4 ダンシング・オールナイト\n"
            "- 機種：PlayStation Vita\n"
            "- エディション：クレイジー・バリューパック\n"
            "- 帯：なし（ユーザー申告）\n",
        ))
        self.assertEqual(limited["edition"], "クレイジー・バリューパック")
        self.assertEqual(limited["obi"], "no")
        self.assertEqual(limited["cover_source"], "curated")
        self.assertTrue(limited["cover"].endswith("/ATS-1506.jpg?v=2"))
        self.assertEqual(limited["reading"], "ペルソナ4 ダンシングオールナイト")
        normal = inventory_item(self.issue(
            280,
            "- タイトル：ペルソナ4 ダンシング・オールナイト\n"
            "- 機種：PlayStation Vita\n"
            "- エディション：通常版\n",
        ))
        self.assertNotEqual(normal["cover"], limited["cover"])
        self.assertTrue(normal["cover"].endswith("/PSVita/PCSG00364.png"))

    def test_ps4_catherine_dynamite_full_body_box(self):
        item = inventory_item(self.issue(
            213,
            "- タイトル：キャサリン・フルボディ\n"
            "- 分類：ゲームソフト\n"
            "- 機種：PlayStation 4\n"
            "- エディション：ダイナマイト・フルボディ BOX（初回生産限定版）\n",
        ))
        self.assertEqual(item["category"], "ゲームソフト")
        self.assertEqual(item["platform"], "PlayStation 4")
        self.assertEqual(item["cover_source"], "curated")
        self.assertTrue(item["cover"].endswith(
            "/eOMAAOSwPjFm2XtL/s-l1200.png"
        ))
        self.assertEqual(item["reading"], "キャサリン フルボディ")
        switch = inventory_item(self.issue(
            206,
            "- タイトル：キャサリン・フルボディ for Nintendo Switch\n"
            "- 機種：Nintendo Switch\n",
        ))
        self.assertNotEqual(switch["cover"], item["cover"])

    def test_ds3_deep_strange_journey_special_box_is_separate(self):
        title = "真・女神転生 DEEP STRANGE JOURNEY"
        issues = [
            self.issue(50,
                f"- タイトル：{title}\n"
                "- 機種：ニンテンドー3DS\n"
                "- エディション：未確認\n"),
            self.issue(214,
                f"- タイトル：{title}\n"
                "- 機種：ニンテンドー3DS\n"
                "- エディション：真・女神転生25周年記念スペシャルボックス（初回生産限定版）\n"),
        ]
        items = build(issues)["items"]
        self.assertEqual(len(items), 2)
        original, special = items
        self.assertEqual(original["cover_source"], "curated")
        self.assertTrue(original["cover"].endswith(
            "/Shin%20Megami%20Tensei%20-%20Deep%20Strange%20Journey%20%28Japan%29.png"
        ))
        self.assertEqual(special["cover_source"], "curated")
        self.assertTrue(special["cover"].endswith("/storage/product/10130126/00.webp"))
        self.assertEqual(
            special["edition"],
            "真・女神転生25周年記念スペシャルボックス（初回生産限定版）",
        )
        self.assertNotEqual(original["cover"], special["cover"])
        self.assertEqual(original["platform"], "ニンテンドー3DS")
        self.assertEqual(special["reading"], "シンメガミテンセイ ディープストレンジジャーニー")

    def test_ps2_nocturne_standard_and_deluxe_reference_images_are_separate(self):
        title = "真・女神転生III NOCTURNE"
        cases = (
            (1, "通常版", "/SLPM-65242.jpg"),
            (216, "デラックスパック", "/SLPM-65241.jpg"),
        )
        urls = []
        for issue_number, edition, suffix in cases:
            item = inventory_item(self.issue(
                issue_number, f"- タイトル：{title}\n"
                "- 機種：PlayStation 2\n" + f"- エディション：{edition}\n"
            ))
            self.assertEqual(item["cover_source"], "curated")
            self.assertTrue(item["cover"].endswith(suffix), edition)
            urls.append(item["cover"])
        self.assertNotEqual(urls[0], urls[1])
        self.assertEqual(urls[0], "https://raw.githubusercontent.com/xlenore/ps2-covers/main/covers/default/SLPM-65242.jpg")
        self.assertEqual(urls[1], "https://raw.githubusercontent.com/xlenore/ps2-covers/main/covers/default/SLPM-65241.jpg")
        # Historical Issue #1 includes an inline reference image, which has
        # higher precedence than a catalog fallback. It must now be normal art.
        historical = inventory_item(self.issue(
            1,
            f"- タイトル：{title}\n- 機種：PlayStation 2\n"
            "- エディション：通常版\n"
            "![normal](https://raw.githubusercontent.com/xlenore/ps2-covers/"
            "main/covers/default/SLPM-65242.jpg)\n",
        ))
        self.assertEqual(historical["cover_source"], "issue")
        self.assertEqual(historical["cover"], urls[0])

    def test_mega_cd_smt_and_ps2_us_nocturne_covers_are_distinct(self):
        mega_cd_url = (
            "https://raw.githubusercontent.com/libretro-thumbnails/"
            "Sega_-_Mega-CD_-_Sega_CD/master/Named_Boxarts/"
            "Shin%20Megami%20Tensei%20%28Japan%29.png"
        )
        us_nocturne_url = (
            "https://raw.githubusercontent.com/xlenore/ps2-covers/"
            "main/covers/default/SLUS-20911.jpg"
        )
        mega = inventory_item(self.issue(
            234, "- タイトル：真・女神転生\n"
            "- 機種：メガドライブ（メガCD）\n"
            "- エディション：日本版（メガCD専用）\n"
            "- 製品型番（資料上）：T-44044\n",
        ))
        us = inventory_item(self.issue(
            235, "- タイトル：真・女神転生III NOCTURNE\n"
            "- 機種：PlayStation 2\n"
            "- エディション：北米版（Shin Megami Tensei: Nocturne）\n"
            "- 製品型番（資料上）：SLUS-20911\n",
        ))
        self.assertEqual(mega["platform"], "メガドライブ（メガCD）")
        self.assertEqual(mega["serial"], "T-44044")
        self.assertEqual(mega["cover"], mega_cd_url)
        self.assertEqual(mega["cover_source"], "curated")
        self.assertEqual(us["serial"], "SLUS-20911")
        self.assertEqual(us["cover"], us_nocturne_url)
        self.assertEqual(us["cover_source"], "curated")
        self.assertEqual(mega["reading"], "シンメガミテンセイ")
        self.assertEqual(us["reading"], "シンメガミテンセイ3 ノクターン")

        # GitHub Issue image URLs take precedence and must match the edition.
        explicit = inventory_item(self.issue(
            235, "- タイトル：真・女神転生III NOCTURNE\n"
            "- 機種：PlayStation 2\n"
            "- エディション：北米版（Shin Megami Tensei: Nocturne）\n"
            + "- 画像URL：" + us_nocturne_url + "\n",
        ))
        self.assertEqual(explicit["cover"], us_nocturne_url)
        self.assertEqual(explicit["cover_source"], "issue")

        jp_standard = inventory_item(self.issue(
            1, "- タイトル：真・女神転生III NOCTURNE\n"
            "- 機種：PlayStation 2\n- エディション：通常版\n",
        ))
        jp_deluxe = inventory_item(self.issue(
            216, "- タイトル：真・女神転生III NOCTURNE\n"
            "- 機種：PlayStation 2\n- エディション：デラックスパック\n",
        ))
        all_items = build([
            self.issue(1, "- タイトル：真・女神転生III NOCTURNE\n"),
            self.issue(216, "- タイトル：真・女神転生III NOCTURNE\n"),
            self.issue(234, "- タイトル：真・女神転生\n"),
            self.issue(235, "- タイトル：真・女神転生III NOCTURNE\n"),
        ])["items"]
        self.assertEqual(len(all_items), 4)
        self.assertEqual(len({item["id"] for item in all_items}), 4)
        self.assertEqual(len({
            jp_standard["cover"], jp_deluxe["cover"],
            mega["cover"], us["cover"]
        }), 4)

    def test_new_limited_box_art_and_platforms(self):
        cases = (
            (213, "キャサリン・フルボディ", "PlayStation 4",
             "ダイナマイト・フルボディ BOX（初回生産限定版）", "/eOMAAOSwPjFm2XtL/s-l1200.png"),
            (217, "メタファー：リファンタジオ", "PlayStation 5",
             "アトラスブランド35thアニバーサリーエディション", "metaphorcollectorjapan.jpg?v=1729096903&width=1100"),
            (218, "ペルソナ3 リロード", "PlayStation 5",
             "PERSONA3 RELOAD LIMITED BOX", "0000021594021-01.jpg?v=1757155393&width=3024"),
            (219, "ペルソナ5", "PlayStation 4",
             "20thアニバーサリー・エディション", "persona-5-20th-anniversary-limited-edition-ps4-used-good-condition-es.jpg"),
            (220, "ペルソナ5 ザ・ロイヤル", "PlayStation 4",
             "ストレートフラッシュ・エディション", "600x600.webp"),
            (221, "ペルソナ5 スクランブル ザ ファントム ストライカーズ", "PlayStation 4",
             "オタカラBOX", "700x700.jpg?v=1614071482"),
            (223, "ユニコーンオーバーロード", "Nintendo Switch",
             "モナークエディション", "4351978.jpg"),
            (224, "真・女神転生V", "Nintendo Switch",
             "禁断のナホビノBOX", "1076002169839024_01_7545w.jpeg"),
            (226, "幻影異聞録♯FE", "Wii U",
             "Fortissimo Edition", "/5092405.jpg"),
            (227, "ソウルハッカーズ2", "PlayStation 5",
             "25thアニバーサリーエディション", "1078002052333135_02_8697w.jpeg"),
            (228, "ペルソナダンシング デラックス・ツインプラス", "PlayStation Vita",
             "デラックス・ツインプラス", "persona-dancing-deluxe-twin-plus-limited-edition-sony-playstation-vita-psvita-japan-occasion.jpg"),
            (229, "真・女神転生III NOCTURNE HD REMASTER", "PlayStation 4",
             "現実魔界化BOX", "CIMG6234111-700x525.jpg"),
        )
        issues = []
        for number, title, platform, edition, suffix in cases:
            issue = self.issue(
                number, f"- タイトル：{title}\n"
                "- 分類：ゲームソフト\n"
                + f"- 機種：{platform}\n- エディション：{edition}\n",
            )
            item = inventory_item(issue)
            self.assertEqual(item["category"], "ゲームソフト")
            self.assertEqual(item["platform"], platform)
            self.assertEqual(item["edition"], edition)
            self.assertEqual(item["cover_source"], "curated", title)
            self.assertTrue(item["cover"].endswith(suffix), title)
            self.assertNotEqual(item["reading"], title if title.startswith("真・") else "")
            issues.append(issue)
        self.assertEqual(len(build(issues)["items"]), len(cases))

    def test_limited_box_obi_pairs_have_distinct_ids_and_shared_art(self):
        cases = (
            ("ペルソナ5 スクランブル ザ ファントム ストライカーズ",
             "PlayStation 4", "オタカラBOX", 221, 222),
            ("真・女神転生V", "Nintendo Switch", "禁断のナホビノBOX", 224, 225),
            ("真・女神転生III NOCTURNE HD REMASTER",
             "PlayStation 4", "現実魔界化BOX", 229, 230),
        )
        for title, platform, edition, yes_id, no_id in cases:
            issues = [
                self.issue(
                    issue_id, f"- タイトル：{title}\n"
                    + f"- 機種：{platform}\n"
                    + f"- エディション：{edition}\n"
                    + f"- 帯：{obi}\n",
                )
                for issue_id, obi in ((yes_id, "あり"), (no_id, "なし"))
            ]
            items = build(issues)["items"]
            self.assertEqual(len(items), 2)
            self.assertEqual(len({x["id"] for x in items}), 2)
            self.assertEqual({x["obi"] for x in items}, {"yes", "no"})
            self.assertEqual(len({x["cover"] for x in items}), 1)
            self.assertEqual(items[0]["edition"], items[1]["edition"])

    def test_five_new_collector_items_preserve_originals_and_exact_box_images(self):
        cases = (
            (237, "偽典・女神転生 東京黙示録",
             "Windows",
             "Windows 95/98版（1999年）",
             "https://cdn-ak.f.st-hatena.com/images/fotolife/t/tmurana/20250315/20250315084011.jpg"),
            (238, "ラジアントヒストリア パーフェクトクロノロジー",
             "ニンテンドー3DS", "PERFECT EDITION（限定版）",
             "https://mediaworld.co.jp/cdn/shop/products/cg10220753_dadc7285-08ad-43b5-ab72-edffbb626922.jpg?v=1631173984"),
            (239, "グローランサーIII", "PlayStation 2",
             "萌え萌えラッキーパック（限定版）",
             "https://eccdn.geo-online.co.jp/ec_media_images/0010834-01.jpg"),
            (240, "世界樹と不思議のダンジョン2", "ニンテンドー3DS",
             "世界樹の迷宮 10th Anniversary BOX（初回生産限定版）",
             "https://buy.nojima.co.jp/assets/web/img/product_image/game/nintendo-3ds/5101448.jpg"),
            (241, "世界樹の迷宮V 長き神話の果て", "ニンテンドー3DS",
             "コレクターズパック（限定版）",
             "https://mediaworld.co.jp/cdn/shop/products/cg10220650_6cb34bac-8318-4984-b9aa-393bfd9456fd.jpg?v=1631245427"),
        )
        records = []
        for number, title, platform, edition, expected in cases:
            item = inventory_item(self.issue(
                number, f"- タイトル：{title}\n"
                f"- 機種：{platform}\n- エディション：{edition}\n",
            ))
            self.assertEqual(item["id"], f"INV-{number:03d}")
            self.assertEqual(item["title"], title)
            self.assertEqual(item["platform"], platform)
            self.assertEqual(item["edition"], edition)
            self.assertEqual(item["cover"], expected)
            self.assertEqual(item["cover_source"], "curated")
            records.append(item)
        self.assertEqual(len({item["id"] for item in records}), 5)
        self.assertEqual(records[0]["reading"], "ギテン メガミテンセイ トウキョウモクシロク")
        # The confirmed Windows 95/98 edition must show its own box art,
        # not the distinct PC-98 edition or an image-free placeholder.
        self.assertEqual(records[0]["cover"], "https://cdn-ak.f.st-hatena.com/images/fotolife/t/tmurana/20250315/20250315084011.jpg")
        self.assertEqual(records[0]["platform"], "Windows")
        self.assertEqual(records[0]["edition"], "Windows 95/98版（1999年）")
        # The original PC-98 edition must not inherit the Windows-only cover.
        pc98 = inventory_item(self.issue(
            999, "- タイトル：偽典・女神転生 東京黙示録\n"
            "- 機種：PC-9801/9821\n"
            "- エディション：PC-98版\n",
        ))
        self.assertNotEqual(pc98["cover"], records[0]["cover"])
        self.assertEqual(pc98["cover"], "")
        # GitHub Issue #237 explicitly supplies the same Windows-art URL.
        explicit_win = inventory_item(self.issue(
            237, "- タイトル：偽典・女神転生 東京黙示録\n"
            "- 機種：Windows\n"
            "- エディション：Windows 95/98版（1999年）\n"
            "- 製品型番（資料上）：2071301\n"
            "- 画像URL：" + "https://cdn-ak.f.st-hatena.com/images/fotolife/t/tmurana/20250315/20250315084011.jpg" + "\n",
        ))
        self.assertEqual(explicit_win["cover"], records[0]["cover"])
        self.assertEqual(explicit_win["cover_source"], "issue")
        self.assertEqual(explicit_win["serial"], "2071301")
        # The first Etrian Mystery Dungeon is a different title; its normal art
        # cannot be substituted for the second game's 10th Anniversary box.
        first = inventory_item(self.issue(
            56, "- タイトル：世界樹と不思議のダンジョン\n"
            "- 機種：ニンテンドー3DS\n- エディション：未確認\n",
        ))
        self.assertNotEqual(first["cover"], records[3]["cover"])
        # Explicit Issue image URLs must match the curated edition cover.
        example = inventory_item(self.issue(
            239, "- タイトル：グローランサーIII\n"
            "- 機種：PlayStation 2\n"
            "- エディション：萌え萌えラッキーパック（限定版）\n"
            "- 画像URL：https://eccdn.geo-online.co.jp/ec_media_images/0010834-01.jpg\n",
        ))
        self.assertEqual(example["cover"], records[2]["cover"])
        self.assertEqual(example["cover_source"], "issue")
        # Adding collector copies must not overwrite older per-issue copies.
        earlier = self.issue(
            152, "- タイトル：グローランサーIII\n"
            "- 機種：PlayStation 2\n- エディション：未確認\n",
        )
        newer = self.issue(
            239, "- タイトル：グローランサーIII\n"
            "- 機種：PlayStation 2\n"
            "- エディション：萌え萌えラッキーパック（限定版）\n",
        )
        results = build([earlier, newer])["items"]
        self.assertEqual({item["id"] for item in results}, {"INV-152", "INV-239"})
        self.assertNotEqual(results[0]["edition"], results[1]["edition"])

    def test_growlanser_ii_deluxe_candidate_keeps_unverified_edition_distinct(self):
        title = "グローランサーII"
        url = "https://www.gavas.jp/upload/save_image/11465.jpg"
        candidate = inventory_item(self.issue(
            244, f"- タイトル：{title}\n"
            "- 機種：PlayStation 2\n"
            "- エディション：デラックスパック（推定）\n"
            "- 製品型番（資料上）：SLPS-20105\n",
        ))
        self.assertEqual(candidate["cover_source"], "curated")
        self.assertEqual(candidate["cover"], url)
        self.assertEqual(candidate["edition"], "デラックスパック（推定）")
        self.assertEqual(candidate["serial"], "SLPS-20105")

        existing = inventory_item(self.issue(
            151, f"- タイトル：{title}\n"
            "- 機種：PlayStation 2\n"
            "- エディション：未確認\n",
        ))
        self.assertEqual(existing["cover_source"], "libretro")
        self.assertNotEqual(existing["cover"], url)
        self.assertEqual(existing["edition"], "未確認")
        self.assertEqual({i["id"] for i in build([
            self.issue(151, f"- タイトル：{title}\n"),
            self.issue(244, f"- タイトル：{title}\n"),
        ])["items"]}, {"INV-151", "INV-244"})

        explicit = inventory_item(self.issue(
            244, f"- タイトル：{title}\n"
            "- 機種：PlayStation 2\n"
            "- エディション：デラックスパック（推定）\n"
            f"- 画像URL：{url}\n",
        ))
        self.assertEqual(explicit["cover"], url)
        self.assertEqual(explicit["cover_source"], "issue")

    def test_new_switch2_fc_sfc_and_n64_owner_records_with_exact_japan_boxart(self):
        expected = (
            (246, "メタファー：リファンタジオ", "Nintendo Switch 2",
             "未確認（Nintendo Switch 2版）", "curated",
             "https://gamerszone.jp/images/upload/2026/06/c097092c5bcb33973e6b5ee738b524dd.jpg"),
            (247, "スペランカー", "ファミリーコンピュータ",
             "未確認（日本版）", "libretro", "Spelunker%20%28Japan%29.png"),
            (248, "ドラえもん ギガゾンビの逆襲", "ファミリーコンピュータ",
             "未確認（日本版）", "libretro",
             "Doraemon%20-%20Giga%20Zombie%20no%20Gyakushuu%20%28Japan%29.png"),
            (249, "じゃりン子チエ ばくだん娘の幸せさがし", "ファミリーコンピュータ",
             "未確認（日本版）", "libretro",
             "Jarinko%20Chie%20-%20Bakudan%20Musume%20no%20Shiawase%20Sagashi%20%28Japan%29.png"),
            (250, "たけしの挑戦状", "ファミリーコンピュータ",
             "未確認（日本版）", "libretro",
             "Takeshi%20no%20Chousenjou%20%28Japan%29.png"),
            (251, "天外魔境ZERO", "スーパーファミコン",
             "未確認（日本版）", "libretro",
             "Tengai%20Makyou%20Zero%20%28Japan%29.png"),
            (252, "スーパーマリオ64", "NINTENDO64",
             "未確認（初版／振動パック対応版の別未確認）", "libretro",
             "Super%20Mario%2064%20%28Japan%29.png"),
        )
        issues = []
        for issue_number, title, platform, edition, source, cover_end in expected:
            issue = self.issue(
                issue_number,
                f"- タイトル：{title}\n- 分類：ゲームソフト\n"
                f"- 機種：{platform}\n- エディション：{edition}\n"
                + ("- 箱：なし\n- 説明書：なし\n"
                   if platform in ("ファミリーコンピュータ", "スーパーファミコン", "NINTENDO64")
                   else "- 箱：未確認\n- 説明書：未確認\n"),
            )
            item = inventory_item(issue)
            self.assertEqual(item["platform"], platform)
            self.assertEqual(item["edition"], edition)
            self.assertEqual(item["cover_source"], source)
            self.assertTrue(item["cover"].endswith(cover_end), title)
            if platform in ("ファミリーコンピュータ", "スーパーファミコン", "NINTENDO64"):
                self.assertEqual(item["case"], "なし")
                self.assertEqual(item["manual"], "なし")
            else:
                self.assertEqual(item["case"], "未確認")
                self.assertEqual(item["manual"], "未確認")
            self.assertNotEqual(item["reading"], title if title.startswith("ドラえもん") else "")
            issues.append(issue)
        items = build(issues)["items"]
        self.assertEqual(len(items), 7)
        self.assertEqual({item["id"] for item in items}, {
            "INV-246", "INV-247", "INV-248", "INV-249",
            "INV-250", "INV-251", "INV-252",
        })
        self.assertEqual(len({item["cover"] for item in items}), 7)

    def test_existing_sfc_wonder_project_j_no_box_no_manual(self):
        # The existing #191 is updated in place; this is not a new copy.
        issue = self.issue(
            191,
            "- タイトル：ワンダープロジェクトJ 機械の少年ピーノ\n"
            "- 機種：スーパーファミコン\n"
            "- エディション：未確認\n"
            "- ケース・箱：なし（ユーザー申告）\n"
            "- 説明書：なし（ユーザー申告）\n",
        )
        item = inventory_item(issue)
        self.assertEqual(item["id"], "INV-191")
        self.assertEqual(item["case"], "なし（ユーザー申告）")
        self.assertEqual(item["manual"], "なし（ユーザー申告）")
        self.assertEqual(item["cover_source"], "libretro")
        self.assertIn("Wonder%20Project%20J", item["cover"])

    def test_wonder_project_j_boxed_and_loose_are_separate_owned_items(self):
        title = "ワンダープロジェクトJ 機械の少年ピーノ"
        copies = (
            (191, "なし（ユーザー申告）", "なし（ユーザー申告）"),
            (254, "あり（ユーザー申告）", "あり（ユーザー申告）"),
        )
        issues = []
        for number, box_state, manual_state in copies:
            issues.append(self.issue(
                number,
                f"- タイトル：{title}\n"
                "- 機種：スーパーファミコン\n"
                "- エディション：未確認\n"
                f"- ケース・箱：{box_state}\n"
                f"- 説明書：{manual_state}\n",
            ))
        items = build(issues)["items"]
        self.assertEqual({x["id"] for x in items}, {"INV-191", "INV-254"})
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["case"], "なし（ユーザー申告）")
        self.assertEqual(items[0]["manual"], "なし（ユーザー申告）")
        self.assertEqual(items[1]["case"], "あり（ユーザー申告）")
        self.assertEqual(items[1]["manual"], "あり（ユーザー申告）")
        self.assertEqual(items[0]["cover"], items[1]["cover"])
        self.assertEqual({x["cover_source"] for x in items}, {"libretro"})

    def test_mario64_owner_confirms_no_box_and_no_manual(self):
        item = inventory_item(self.issue(
            252,
            "- タイトル：スーパーマリオ64\n"
            "- 機種：NINTENDO64\n"
            "- エディション：未確認（初版／振動パック対応版の別未確認）\n"
            "- 箱：なし（ユーザー申告、2026-11-22）\n"
            "- 説明書：なし（ユーザー申告、2026-11-22）\n",
        ))
        self.assertEqual(item["case"], "なし（ユーザー申告、2026-11-22）")
        self.assertEqual(item["manual"], "なし（ユーザー申告、2026-11-22）")
        self.assertEqual(item["platform"], "NINTENDO64")
        self.assertEqual(item["cover_source"], "libretro")

    def test_nocturne_hd_loose_discs_are_added_to_ps4_special_editions(self):
        title = "真・女神転生III NOCTURNE HD REMASTER"
        ps4_url = "https://mediaworld.co.jp/cdn/shop/files/cg10442053_6aa84820-f8b3-4db8-aa9b-76878f6c69ab.jpg?v=1792771661&width=1000"
        ps4 = [
            self.issue(
                number,
                f"- タイトル：{title}\n"
                "- 機種：PlayStation 4\n"
                f"- エディション：{edition}\n"
                "- ケース・箱：なし\n- 説明書：なし\n"
                if number == 255 else
                f"- タイトル：{title}\n"
                "- 機種：PlayStation 4\n"
                f"- エディション：{edition}\n"
                + f"- 帯：{obi}\n",
            )
            for number, edition, obi in [
                (229, "現実魔界化BOX", "あり"),
                (230, "現実魔界化BOX", "なし"),
                (255, "未確認（箱説なし）", "未確認"),
            ]
        ]
        items = build(ps4)["items"]
        self.assertEqual({x["id"] for x in items}, {"INV-229", "INV-230", "INV-255"})
        self.assertEqual(len(items), 3)
        self.assertEqual([x["obi"] for x in items[:2]], ["yes", "no"])
        self.assertEqual(items[0]["cover"], items[1]["cover"])
        self.assertNotEqual(items[0]["cover"], items[2]["cover"])
        self.assertEqual(items[2]["cover"], ps4_url)
        self.assertEqual(items[2]["cover_source"], "curated")
        self.assertEqual(items[2]["case"], "なし")
        self.assertEqual(items[2]["manual"], "なし")
        # No false inference of limited edition from a bare PS4 game disc.
        self.assertEqual(items[2]["edition"], "未確認（箱説なし）")

    def test_nocturne_hd_two_switch_loose_carts_are_distinct(self):
        title = "真・女神転生III NOCTURNE HD REMASTER"
        switch_url = "https://item-shopping.c.yimg.jp/i/f/media9_4984995903996"
        issues = [
            self.issue(
                number,
                f"- タイトル：{title}\n"
                "- 機種：Nintendo Switch\n"
                "- エディション：未確認（箱説なし）\n"
                "- ケース・箱：なし（ユーザー申告）\n"
                "- 説明書：なし（ユーザー申告）\n",
            )
            for number in (256, 257)
        ]
        items = build(issues)["items"]
        self.assertEqual(len(items), 2)
        self.assertEqual({x["id"] for x in items}, {"INV-256", "INV-257"})
        self.assertEqual({x["platform"] for x in items}, {"Nintendo Switch"})
        self.assertEqual({x["case"] for x in items}, {"なし（ユーザー申告）"})
        self.assertEqual({x["manual"] for x in items}, {"なし（ユーザー申告）"})
        self.assertEqual({x["edition"] for x in items}, {"未確認（箱説なし）"})
        self.assertEqual({x["cover"] for x in items}, {switch_url})
        self.assertEqual({x["cover_source"] for x in items}, {"curated"})

    def test_ps4_and_switch_nocturne_hd_standard_copies_added_without_overwriting_limited_or_loose(self):
        title = "真・女神転生III NOCTURNE HD REMASTER"
        cases = [
            (259, "PlayStation 4", [229, 230, 255],
             "https://mediaworld.co.jp/cdn/shop/files/cg10442053_6aa84820-f8b3-4db8-aa9b-76878f6c69ab.jpg?v=1792771661&width=1000"),
            (260, "Nintendo Switch", [256, 257],
             "https://item-shopping.c.yimg.jp/i/f/media9_4984995903996"),
        ]
        new_items = []
        for number, platform, older, cover in cases:
            item = inventory_item(self.issue(
                number, f"- タイトル：{title}\n"
                f"- 機種：{platform}\n"
                "- エディション：通常版\n"
                "- ケース・箱：未確認\n"
                "- 説明書：未確認\n",
            ))
            self.assertEqual(item["id"], f"INV-{number:03d}")
            self.assertEqual(item["platform"], platform)
            self.assertEqual(item["edition"], "通常版")
            self.assertEqual(item["cover"], cover)
            self.assertEqual(item["cover_source"], "curated")
            self.assertEqual(item["case"], "未確認")
            self.assertEqual(item["manual"], "未確認")
            for old in older:
                self.assertNotEqual(item["id"], f"INV-{old:03d}")
            new_items.append(item)
        self.assertEqual(len(new_items), 2)

        # Verify counts by physical inventory issue, not by game/edition.
        issues = []
        for number, platform, edition in [
            (229, "PlayStation 4", "現実魔界化BOX"),
            (230, "PlayStation 4", "現実魔界化BOX"),
            (255, "PlayStation 4", "未確認（箱説なし）"),
            (259, "PlayStation 4", "通常版"),
            (256, "Nintendo Switch", "未確認（箱説なし）"),
            (257, "Nintendo Switch", "未確認（箱説なし）"),
            (260, "Nintendo Switch", "通常版"),
        ]:
            issues.append(self.issue(
                number, f"- タイトル：{title}\n"
                f"- 機種：{platform}\n- エディション：{edition}\n",
            ))
        items = build(issues)["items"]
        self.assertEqual(len(items), 7)
        self.assertEqual(len({x["id"] for x in items}), 7)
        self.assertEqual(sum(x["platform"] == "PlayStation 4" for x in items), 4)
        self.assertEqual(sum(x["platform"] == "Nintendo Switch" for x in items), 3)
        ps4_box = [x for x in items if x["platform"] == "PlayStation 4" and x["edition"] == "現実魔界化BOX"]
        self.assertEqual(len(ps4_box), 2)
        self.assertNotEqual(ps4_box[0]["cover"], new_items[0]["cover"])
        loose = [x for x in items if x["edition"] == "未確認（箱説なし）"]
        self.assertEqual(len(loose), 3)

    def test_steam_screenshot_game_only_manifest(self):
        # The Steam source is a library screenshot, not a Steam purchase/
        # entitlement API. Do not infer transaction status from the image.
        import json
        from pathlib import Path
        manifest = json.loads(
            (Path(__file__).resolve().parent.parent /
             "data/steam_screenshot_import_20261122.json").read_text(encoding="utf-8")
        )
        records = manifest["records"]
        self.assertEqual(len(records), 86)
        self.assertEqual(len([r for r in records if r["kind"] == "demo"]), 1)
        self.assertEqual(len([r for r in records if r["kind"] == "game"]), 85)
        self.assertEqual(len({r["title"] for r in records}), 86)
        self.assertEqual(len([r for r in records if r["title"].startswith("G-MODEアーカイブス+")]), 11)
        for item in records:
            self.assertIn(item["screenshot"], {"8577", "8578", "8579", "8580", "8583", "8584"})
            self.assertTrue(item["title"])
            self.assertNotIn(item["title"], {"Lossless Scaling", "KIKI", "RetroArch", "RPG Maker XP"})
        titles = {r["title"] for r in records}
        for title in (
            "G-MODEアーカイブス+ 真・女神転生-20XX",
            "G-MODEアーカイブス+ 魔神転生 blind thinker",
            "Persona 3 Reload",
            "Persona 5 Royal",
            "Metaphor: ReFantazio",
            "Metaphor: ReFantazio - Prologue Demo",
            "RAIDOU Remastered: 超力兵団奇譚",
        ):
            self.assertIn(title, titles)

        # Two sharper screenshots resolve 17 previously uncertain game tiles.
        followup = [r for r in records if r["screenshot"] in ("8583", "8584")]
        self.assertEqual(len(followup), 17)
        self.assertEqual(len([r for r in followup if r["screenshot"] == "8583"]), 9)
        self.assertEqual(len([r for r in followup if r["screenshot"] == "8584"]), 8)
        new_titles = {r["title"] for r in followup}
        self.assertEqual(len(new_titles), 17)
        for title in (
            "HITMAN World of Assassination", "Hitman: Absolution",
            "HITMAN (2016)", "HITMAN 2",
            "Shin Megami Tensei III Nocturne HD Remaster",
            "ブレス オブ ファイアIV うつろわざるもの",
            "The Life and Suffering of Sir Brante",
            "METAL GEAR SOLID V: GROUND ZEROES",
            "METAL GEAR SOLID V: THE PHANTOM PAIN",
            "Rat Quest", "シロナガス島への帰還 -Return to Shironagasu Island-",
            "Rise of Rebellion～地罰上らば竜の降る～",
            "STEINS;GATE", "Tell Me Why",
            "Ultimate Epic Battle Simulator",
            "Undercroft Warriors", "真・女神転生V Vengeance",
        ):
            self.assertIn(title, new_titles)
        for tool in ("Lossless Scaling", "RetroArch", "RPG Maker XP", "KIKI"):
            self.assertNotIn(tool, {r["title"] for r in records})
        # Four HITMAN entries are distinguishable applications and retained
        # separately; World of Assassination does not automatically replace
        # the older 2016, 2, or Absolution entries.
        self.assertEqual(
            len([r for r in followup if r["title"].lower().startswith("hitman")]), 4
        )
        self.assertTrue(manifest["unresolved"])
        self.assertFalse(any("8579" in item for item in manifest["unresolved"]))

        # Steam-only records are independent of prior console editions.
        steam_smt3 = inventory_item(self.issue(
            336,
            "- タイトル：Shin Megami Tensei III Nocturne HD Remaster\n"
            "- 分類：ゲームソフト\n- 機種：Steam\n"
            "- エディション：Steam版（デジタル）\n"
            "- ケース・箱：対象外（デジタル版）\n",
        ))
        self.assertEqual(steam_smt3["platform"], "Steam")
        self.assertEqual(steam_smt3["case"], "対象外（デジタル版）")
        self.assertIn(steam_smt3["cover_source"], ("", "steam"))
        physical_smt3 = self.issue(259,
            "- タイトル：真・女神転生III NOCTURNE HD REMASTER\n"
            "- 機種：PlayStation 4\n- エディション：通常版\n")
        self.assertEqual(
            {x["id"] for x in build([physical_smt3, self.issue(
                336, "- タイトル：Shin Megami Tensei III Nocturne HD Remaster\n"
                "- 機種：Steam\n- エディション：Steam版（デジタル）\n",
            )])["items"]},
            {"INV-259", "INV-336"},
        )

        # Each game is a distinct digital library entry, separate from an
        # existing console or physical copy of the same title.
        demo_title = "Metaphor: ReFantazio - Prologue Demo"
        demo = inventory_item(self.issue(
            330,
            f"- タイトル：{demo_title}\n"
            "- 分類：ゲームソフト\n"
            "- 機種：Steam\n"
            "- エディション：Steam版（体験版）\n"
            "- ケース・箱：対象外（デジタル版）\n"
            "- 説明書：紙媒体は対象外\n",
        ))
        self.assertEqual(demo["platform"], "Steam")
        self.assertEqual(demo["edition"], "Steam版（体験版）")
        self.assertEqual(demo["case"], "対象外（デジタル版）")
        self.assertEqual(demo["manual"], "紙媒体は対象外")
        self.assertIn(demo["cover_source"], ("", "steam"))

        physical = self.issue(217,
            "- タイトル：メタファー：リファンタジオ\n"
            "- 機種：PlayStation 5\n"
            "- エディション：アトラスブランド35thアニバーサリーエディション\n")
        steam = self.issue(329,
            "- タイトル：Metaphor: ReFantazio\n"
            "- 機種：Steam\n- エディション：Steam版（デジタル）\n")
        items = build([physical, steam])["items"]
        self.assertEqual(len(items), 2)
        self.assertEqual({x["id"] for x in items}, {"INV-217", "INV-329"})
        self.assertEqual({x["platform"] for x in items}, {"PlayStation 5", "Steam"})

    def test_every_steam_game_has_explicit_kana_reading(self):
        import json
        from pathlib import Path
        root = Path(__file__).resolve().parent.parent
        records = json.loads(
            (root / "data/steam_screenshot_import_20261122.json")
            .read_text(encoding="utf-8"))["records"]
        readings = json.loads(
            (root / "data/title_readings.json").read_text(encoding="utf-8")
        )["readings"]
        self.assertEqual(len(records), 86)
        pinned = json.loads(
            (root / "data/steam_verified_appids.json").read_text(encoding="utf-8")
        )["appids"]
        self.assertEqual(set(pinned), {record["title"] for record in records})
        self.assertEqual(len(set(pinned.values())), 86)
        for number, record in enumerate(records, start=262):
            title = record["title"]
            self.assertIn(title, readings)
            reading = readings[title]
            self.assertTrue(reading and reading != title, title)
            self.assertTrue(all(
                "\u30a0" <= c <= "\u30ff" or c == " " or c.isdigit()
                for c in reading
            ), title)
            item = inventory_item(self.issue(
                number,
                f"- タイトル：{title}\n- 分類：ゲームソフト\n"
                "- 機種：Steam\n- エディション：Steam版（デジタル）\n",
            ))
            self.assertEqual(item["reading"], reading)
            self.assertEqual(item["cover_source"], "steam", title)
            self.assertIn(f"/{pinned[title]}/library_600x900.jpg", item["cover"])
            self.assertIn(f"/{pinned[title]}/header.jpg", item["cover_fallback"])
        # Exact game IDs, not series IDs, must drive Steam image URLs.
        gmode = inventory_item(self.issue(
            294, "- タイトル：G-MODEアーカイブス+ 女神転生外伝 新約ラストバイブル\n"
            "- 機種：Steam\n- エディション：Steam版（デジタル）\n",
        ))
        self.assertEqual(gmode["cover_source"], "steam")
        self.assertIn("/2192670/library_600x900.jpg", gmode["cover"])
        self.assertIn("/2192670/header.jpg", gmode["cover_fallback"])
        # No Steam source image may override a user-authored Issue image.
        override = inventory_item(self.issue(
            294, "- タイトル：G-MODEアーカイブス+ 女神転生外伝 新約ラストバイブル\n"
            "- 機種：Steam\n"
            "- 画像URL：https://example.org/user-cover.jpg\n",
        ))
        self.assertEqual(override["cover"], "https://example.org/user-cover.jpg")
        self.assertEqual(override["cover_source"], "issue")

    def test_steam_cover_resolver_rejects_fuzzy_franchise_substitutes(self):
        from scripts.resolve_steam_covers import normalized, steam_images
        self.assertNotEqual(normalized("Persona 3 Reload"), normalized("Persona 4 Revival"))
        self.assertNotEqual(normalized("HITMAN 2"), normalized("HITMAN"))
        self.assertEqual(normalized("Persona® 5 Strikers"), normalized("Persona 5 Strikers"))
        self.assertEqual(
            normalized("G-MODEアーカイブス＋ 魔神転生 blind thinker"),
            normalized("G-MODEアーカイブス+ 魔神転生 blind thinker"),
        )
        result = steam_images(2192670)
        self.assertTrue(result["cover"].startswith("https://"))
        self.assertTrue(result["cover"].endswith("/library_600x900.jpg"))
        self.assertTrue(result["fallback"].endswith("/header.jpg"))
        for invalid in (0, -1, 100000000):
            with self.assertRaises(ValueError):
                steam_images(invalid)

    def test_cards_are_full_click_targets_with_keyboard_support(self):
        from pathlib import Path
        root = Path(__file__).resolve().parent.parent
        js = (root / "site/app.js").read_text(encoding="utf-8")
        css = (root / "site/styles.css").read_text(encoding="utf-8")
        start = js.index("function cardFor(item) {")
        end = js.index("\nfunction propertyRow(", start)
        card = js[start:end]
        self.assertIn('card.addEventListener("click"', card)
        self.assertIn('card.addEventListener("keydown"', card)
        self.assertIn('event.key === "Enter"', card)
        self.assertIn('event.key === " "', card)
        self.assertIn('card.setAttribute("role", "button")', card)
        self.assertIn('card.tabIndex = 0', card)
        self.assertNotIn('element("button", "detail-button"', card)
        self.assertIn('.item-card:focus-visible', css)
        self.assertIn('item.cover_fallback', js)

    def test_japanese_console_box_art_region_audit_and_north_american_exception(self):
        import json
        from pathlib import Path
        root = Path(__file__).resolve().parent.parent
        data = json.loads(
            (root / "data/japanese_console_cover_audit_20261122.json")
            .read_text(encoding="utf-8"))
        from scripts.build_catalog import REFERENCE_COVERS
        fixes = data["corrected_foreign_art"]
        additions = data["filled_missing_art"]
        self.assertEqual(len(fixes), 7)
        self.assertGreaterEqual(len(additions), 24)
        self.assertEqual({(entry["platform"], entry["title"]) for entry in fixes}.__len__(), 7)
        for platform, group in REFERENCE_COVERS.items():
            if platform in ("Steam", "Windows"):
                continue
            for title, filename in group.get("images", {}).items():
                self.assertNotIn("(USA)", filename, (platform, title))
                self.assertNotIn("(Europe)", filename, (platform, title))
        for fix in fixes:
            platform, title, url = fix["platform"], fix["title"], fix["new"]
            group = REFERENCE_COVERS[platform]
            self.assertNotIn(title, group.get("images", {}))
            self.assertEqual(group.get("urls", {}).get(title), url)
            item = inventory_item(self.issue(
                1200, f"- タイトル：{title}\n"
                f"- 機種：{platform}\n- エディション：未確認\n",
            ))
            # If an explicitly named collector edition takes priority,
            # never replace that edition with a standard Japan cover.
            if not group.get("edition_urls", {}).get(title):
                self.assertEqual(item["cover"], url, (platform, title))
                self.assertEqual(item["cover_source"], "curated")
        for addition in additions:
            platform, title, url = (
                addition["platform"], addition["title"], addition["url"]
            )
            group = REFERENCE_COVERS[platform]
            if "edition" in addition:
                edition = addition["edition"]
                self.assertEqual(group["edition_urls"][title][edition], url)
            else:
                edition = "未確認"
                self.assertEqual(group.get("urls", {}).get(title), url)
            item = inventory_item(self.issue(
                1201, f"- タイトル：{title}\n"
                f"- 機種：{platform}\n- エディション：{edition}\n",
            ))
            self.assertEqual(item["cover"], url, (platform, title, edition))
        # The ONLY explicitly North American physical collection issue is
        # PS2 Nocturne #235. The Japanese standard and deluxe still differ.
        na = data["north_america_preserved"]
        self.assertEqual([row["issue"] for row in na], [235])
        north_american = inventory_item(self.issue(
            235, "- タイトル：真・女神転生III NOCTURNE\n"
            "- 機種：PlayStation 2\n"
            "- エディション：北米版（Shin Megami Tensei: Nocturne）\n"
            f"- 画像URL：{na[0]['url']}\n",
        ))
        self.assertIn("/SLUS-20911.jpg", north_american["cover"])
        self.assertEqual(north_american["cover_source"], "issue")
        edition_covers = REFERENCE_COVERS["PlayStation 2"]["edition_urls"][
            "真・女神転生III NOCTURNE"
        ]
        self.assertIn("/SLPM-65242.jpg", edition_covers["通常版"])
        self.assertIn("/SLPM-65241.jpg", edition_covers["デラックスパック"])
        self.assertEqual(
            edition_covers["北米版（Shin Megami Tensei: Nocturne）"],
            na[0]["url"],
        )

    def test_japan_box_art_does_not_copy_mismatched_game_or_limited_box(self):
        from scripts.build_catalog import REFERENCE_COVERS
        ps2 = REFERENCE_COVERS["PlayStation 2"]
        self.assertIn("/SLPM-65443.jpg", ps2["urls"]["FRONT MISSION 4"])
        self.assertNotIn("SLPM-65450", ps2["urls"]["FRONT MISSION 4"])
        self.assertIn(
            "/SLPS-25829.jpg",
            ps2["edition_urls"]["アナザーセンチュリーズ エピソード2"][
                "スペシャルボーカルバージョン"],
        )
        self.assertIn(
            "/SLPM-65209.jpg",
            ps2["urls"]["スターオーシャン Till the End of Time"],
        )
        self.assertIn(
            "/SLPM-65438.jpg",
            ps2["urls"]["スターオーシャン Till the End of Time ディレクターズカット"],
        )
        self.assertNotEqual(
            ps2["urls"]["スターオーシャン Till the End of Time"],
            ps2["urls"]["スターオーシャン Till the End of Time ディレクターズカット"],
        )
        ps3 = REFERENCE_COVERS["PlayStation 3"]
        self.assertNotIn("BLJM67001.JPG", ps3["urls"]["METAL GEAR SOLID 4 GUNS OF THE PATRIOTS"])
        self.assertNotIn("BLJM60554.JPG", ps3["urls"]["METAL GEAR RISING REVENGEANCE"])
        self.assertNotIn("BLJM60442.JPG", ps3["urls"]["ペルソナ4 ジ・アルティメット イン マヨナカアリーナ"])
        self.assertIn("/BLJM61209.JPG", ps3["urls"]["ペルソナ4 ジ・アルティマックス ウルトラスープレックスホールド"])

    def test_unknown_game_is_not_given_wrong_artwork(self):
        item = inventory_item(self.issue(
            225, "- タイトル：架空のタイトル\n- 機種：PSP\n"
        ))
        self.assertEqual(item["cover"], "")
        self.assertEqual(item["cover_source"], "")


if __name__ == "__main__":
    unittest.main()
