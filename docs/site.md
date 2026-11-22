# GitHub Pages collection browser

GitHub Issues remains the source of truth: one Issue per physical item. Duplicate
copies and alternate editions are separate Issues. The original README is retained.

## Publishing

In the repository's **Settings → Pages**, select **GitHub Actions** as the source.
The workflow at .github/workflows/pages.yml runs on pushes to main and on Issue
create/edit/label/status events. It can also be started using "Run workflow".

The workflow reads Issues using the built-in GITHUB_TOKEN, exports allowlisted
fields to site/data/collection.json, tests the parser and deploys site/ via Pages.
The exported JSON is a build artifact, not a file committed to main.

## Local preview

Run from the repository root:

    python3 -m unittest discover -s tests -v
    python3 scripts/build_catalog.py
    python3 -m http.server 8000 --directory site

Then visit http://localhost:8000/. For offline tests you can pass
--input path/to/issues-api-response.json instead of fetching live Issues.

## Fields and public information

- Existing "- 管理番号：..." Issues and newer Issue Forms are supported.
- The site exports only title, category, platform, edition, serial, ownership,
  accessory summaries, a reference cover URL and the Issue link.
- It deliberately excludes free-form notes, purchase prices, storage locations,
  and entire Issue bodies **from the generated JSON**.
- The repository and its Issues are public; omitted fields are **not private**
  if written in public Issues. Do not record confidential data in them.
- Images are external references and may be incorrect or unavailable.
- An Issue's Open/Closed state does not indicate whether the item is owned.
- Inventory numbers should be unique. New Issue Form entries default to
  "INV-<issue number>" if no explicit number is present.
- This site uses no database, external JavaScript library or backend runtime.

## Cover art for imported Issues

- New photo-based Issues initially had no cover URLs; the old interface showed "NO IMAGE".
- `data/cover_references.json` now maps exact Japanese titles and platforms to
  existing Libretro `Named_Boxarts` filenames. These **reference images** do
  not prove the edition or condition of the physically owned item.
- An explicit `画像URL` or Markdown image in the Issue always takes precedence.
- Unmapped games display a clearly labeled title/platform placeholder;
  the site does not guess at artwork from another release or platform.
- The generated catalog includes `cover_source` (`issue`, `libretro`, or
  empty) for an on-card reference badge. No image files are copied.
- Some PS3 and PS Vita titles with no Libretro artwork are mapped to verified
  serial/title-ID images in [SvenGDK/PSMT-Covers](https://github.com/SvenGDK/PSMT-Covers)
  through explicit `urls` entries. They have `cover_source=curated` and display
  the same 参考画像 badge. IDs describe the reference image, **not a verified
  serial number or physical edition of the owned game**.
- Other verified exact-title mappings use [x360db](https://github.com/xenia-manager/x360db)
  (Xbox 360 title ID, `boxart.jpg`) and
  [HexFlow-Covers](https://github.com/andiweli/hexflow-covers)
  (PSP game serial, `Covers/PSP/*.png`).
- Reference images are always selected by exact platform and exact title;
  they are never chosen from a different console or inferred edition.
- Libretro artwork is linked from `raw.githubusercontent.com/libretro-thumbnails`;
  external hosting and original image rights remain with the respective providers.

## Edition-specific artwork

- `edition_urls` overrides generic per-title cover references when the Issue's edition is known.
- For Persona 3 FES, the standard, append, and PlayStation 2 the Best cover references
  use their individual serials. The source is reference artwork, not a verified physical scan.
- For Persona 3 Portable and Persona 4, an empty URL for an edition (such as an
  unavailable Best cover) intentionally displays the placeholder instead of a
  misleading standard-edition cover.
- Explicit `画像URL` values entered in Issues always have the highest priority.
- The mapping of individual Issue numbers to physical copies is provisional
  until the owner confirms which actual case matches each entry.

## 魔剣爻 edition references (PS2)

- Three separate owned copies are tracked: first limited edition (`SLPS-25042`, Issue #34),
  standard edition (`SLPS-25043`, Issue #129), and Atlus Best Collection
  (`SLPM-65144`, Issue #139).
- **Atlus Best Collection is not PlayStation 2 the Best.**
- Reference images for each edition map explicitly to the corresponding serial in
  `xlenore/ps2-covers`; they do not establish that the owner's physical discs have
  those serial numbers. Issue-to-physical-copy matching remains to be verified.

## SFC inventory corrections and manufacturing lots (2026-11-22)

- `魔神転生II` was incorrectly inferred from a shelf photo. The owner confirmed
  it is **not owned**; Issue #102 is closed without the `所有` label, preserving
  the correction in the issue history.
- The correct owned SFC title is `ラストバイブルIII` (Issue #143). Its
  verified external Libretro reference cover is `Last Bible III (Japan).png`.
- SFC `真・女神転生II` consists of **three physical copies**: initial
  production lot (Issue #98), second lot (Issue #141), and third lot (Issue
  #142). The issue's `ロット` field records the claimed lot, and
  `エディション` mirrors it for current website display; manufacturing lot
  is not equivalent to a retail edition. PCB/label verification is not recorded.
- The two separately inventoried PlayStation copies (#15 and #16) must not be
  mixed into the SFC three-copy count.
- All three SFC lots currently use the same *reference jacket image*, which
  does not prove the cartridge lot or the item's physical condition.

## 50音順（標準表示、2026-11-22）

- GitHub Pages の標準並びを管理番号順から **50音順** に変更。
- `data/title_readings.json` には漢字タイトルや英語・ローマ字タイトルの
  読みを明示する。その他はタイトル表記で並べる。
- 各 Issue に `- 読み：カナヨミ` または `- よみ：カナヨミ` を追加した場合は
  タイトル共通辞書よりそちらを優先。新しい漢字タイトルを追加した際は
  辞書か Issue へ読みを追加すること。
- `scripts/build_catalog.py` が公開 JSON に `reading`（公開用のみ）を追加。
  `site/app.js` は日本語の `Intl.Collator` でこれを並び替える。
- 機種別表示は機種名→50音順。検索では読み仮名も入力できる。
- 管理番号は各個体の識別子として維持するが、並び替えの選択肢からは除外。
  同名同版の別個体は安定して ID 順のタイブレークで表示する。

## 2026-11-22 の棚写真からの追加登録

- 以前 PS2 の登録がメガテン・ペルソナ系に偏っており、写真中段の PS2 ケース
  27個体と PS3 ケース7個体が抜けていた。Issue #145～#178 を新規作成。
- 新規タイトルは実際の棚写真で判読できる背表紙から登録し、
  製品型番・帯・説明書・エディション・箱の完全性は確認済みとしない。
  同一タイトルの物理的に複数見えるケースは個別Issueにしている。
- 例：グローランサーII～VI、幻想水滸伝III～V、アナザーセンチュリーズ
  エピソード、シーマン、スターオーシャン、FRONT MISSION 4、
  アバタール・チューナー、ペルソナ5、メタルギアなど。
- 写真だけでは確定できない細い背表紙や版は推測登録しない。
- PS2 の14タイトルには実在が確認できた Libretro の参考ジャケットを追加。
  アナザーセンチュリーズエピソード2のスペシャルボーカルバージョンや
  確定できない版の画像は別版の画像を流用しない。

## PS3 / PlayStation Vita title and edition corrections (2026-11-22)

- PS3 `トゥームレイダー` is owned (Issue #180). For now the catalog uses
  the Japan 2013 title (`BLJM-60557`) as a **reference** only, pending
  physical edition/serial verification. The reference image is an externally
  hosted exact-code PS3 jacket.
- PS Vita `ペルソナ4 ザ・ゴールデン` consists of two owned retail
  packages: standard (Issue #79; reference `VLJM-35001`, game ID
  `PCSG-00004`) and PlayStation Vita the Best (Issue #181; reference
  `VLJM-65004`, game ID `PCSG-00563`). Their reference cover images are
  different, keyed by edition. Physical case codes remain unchecked.
- The actual owned PS Vita Muramasa is the **`朧村正＋元禄怪奇譚
  DLC全四篇プロダクトコード入りパッケージ`** (Issue #78; reference
  `VLJM-30122`), *not* the base 2013 PS Vita retail version. Its external
  cover image is the matching image from the developer/publisher Marvelous.
  The package includes DLC download **codes**, not guaranteed game-card
  content. The publisher's package image states a code expiration of
  2025-03-18; neither code presence nor redemption is asserted.
- `data/title_readings.json` also tracks the kana reading of the updated
  full Muramasa package title, Tomb Raider and P4G to retain proper 50-on sort.
- The Wii version `朧村正` (#120) remains an independent owned physical
  copy and keeps its separate reference image.

## Four additional shelf-inventory titles (2026-11-22)

- Issue #183 — PS2 `ブレス オブ ファイアV ドラゴンクォーター`;
  reference regular-edition code `SLPM-65196`. The owner's exact edition
  is **unverified**; do not infer this is the standard rather than a Best copy.
- Issue #184 — PS3 **`ICO/ワンダと巨像 Limited Box`** (`BCJS-30073`).
  **One physical boxed set is one inventory item**. The set's published
  contents include the PS3 HD remasters of ICO and Shadow of the Colossus
  and a special booklet/digital-code benefits. Contents and code state
  of the owner's copy are *not verified*.
- Issue #185 — PSP `Another Century's Episode Portable`, reference
  product code `ULJS-00322`.
- Issue #186 — PSP `機動戦士ガンダム ギレンの野望 アクシズの脅威V`,
  reference product code `ULJS-00178`. Do not confuse the PSP edition
  with the PlayStation 2 edition.
- Images are separately verified as existing reference-cover resources,
  not photographs of the owner's actual packaging. Edition details and
  physical contents remain to be audited.
- Corresponding kana title readings have been added to preserve
  the site's default Japanese gojuon sort.

## Original Xbox SMT NINE editions and Xbox 360 Blue Dragon (2026-11-22)

- Xbox \`真・女神転生 NINE\`: two owned retail variants, **standard
  stand-alone edition** (Issue #81, reference product code M90-1) and
  **limited Deluxe Pack** (Issue #188, reference product code M90-3).
  Keep one Issue per physical product. Edition-specific reference images
  use different art (standard case vs. outer deluxe box).
- Deluxe Pack bonus items such as the Maria figure, binder, and ID card
  are **product specifications**, not verified completeness of the
  owner's physical set. Do not infer these extras were included in the
  user's copy or are still present.
- Xbox 360 \`ブルードラゴン\` (Issue #189) is one separately owned
  game; the Japanese regular-edition product reference is A7J-00001,
  while its reference image uses Xbox 360 Title ID 4D5307DF from
  x360db. The user's actual package edition remains unverified.
- \`ブルードラゴン\` gets a kana sort key and the Xbox NINE title
  retains its existing kana key. The exact console and edition are
  matched before displaying a cover.
- Reference cover photographs belong to their external publishers /
  original hosts; none are a photograph of the owner's actual items.

## Two additional SFC items (2026-11-22)

- Issue #191: `ワンダープロジェクトJ 機械の少年ピーノ` (Super Famicom).
- Issue #192: `新桃太郎伝説` (Super Famicom).
- Both are separately owned copies reported by the owner, with edition,
  physical packaging, cartridge, and extras currently unverified.
- Verified-by-existence Libretro `Named_Boxarts` reference images for both
  titles were added; these are not photographs of the owner's physical games.
- Both titles have kana readings in `data/title_readings.json` so the
  site's Japanese 50-on sorting is preserved.

## Saturn Soul Hackers inventory and 3DS SMT IV FINAL artwork (2026-11-22)

- Sega Saturn Devil Summoner Soul Hackers is owned as **two separate physical copies**,
  Issue #87 and Issue #194, both with **no obi** as reported by the owner.
  The exact retail editions and other physical contents have not been checked.
- Sega Saturn "デビルサマナー ソウルハッカーズ 悪魔全書 第二集" is a separate
  owned item, Issue #195 (reference product code T-14421G), not a third copy
  of the main game. Its obi status is unknown. It uses its **own** verified
  Libretro reference boxart file, "Devil Summoner - Soul Hackers -
  Akuma Zensho Daini-shuu (Japan).png".
- Nintendo 3DS "真・女神転生IV FINAL" (Issue #49) is explicitly pinned by
  \`edition_urls\` to the Japanese FINAL reference jacket
  "Shin Megami Tensei IV - Final (Japan).png", independently from original
  "真・女神転生IV" (Issue #48) and its Japanese base-game jacket.
- All artwork is external *reference artwork*, not photographed owned items.
  Image file existence and platform/title matching were verified.

## DS Caduceus Best and Famicom Sanma no Meitantei (2026-11-22)

- Nintendo DS `超執刀 カドゥケウス` (Issue #44) is the **アトラス ベスト コレクション** release, not the original retail cover.
  Its 2007-04-26 Best reissue has the same `NTR-P-AKDJ` identifier as the regular edition; edition identification cannot rely on this product code alone.
  The dedicated Best cover reference uses the photographed box image from the corresponding Best retail listing. The image includes the Best logo and is not a photograph of the owner's own package.
  An unknown/standard edition must not silently reuse this Best cover or vice versa.
- Family Computer `さんまの名探偵` (Issue #197) is a newly declared owned item.
  The spoken request was interpreted as this title; the issue notes that the transcription-based title can be corrected if the user intended a different game.
  A title-exact Japan boxart reference from Libretro is used; package contents and version remain unverified.
- The new Famicom title is included in `data/title_readings.json` for default gojuon sorting.

## PC Engine category repair, GBA titles, and NINTENDO64 (2026-11-22)

- The original PC Engine \`真・女神転生\` (Issue #35) and \`天外魔境II 卍MARU\`
  (Issue #36) were classified by the static site as "未分類" because the
  original Issue bodies omitted the \`- 分類: ゲームソフト\` field. Both
  source-of-truth Issues have now been repaired; the exact catalog parser
  accepts either ASCII \`:\` or full-width \`：\` in the field.
- Added one PC Engine **CD-ROM²** title, \`イースI・II\` (Issue #199,
  reference product code HCD9009). Although it contains both Ys I and II,
  it is a single physical CD package and counts as one inventory item.
- Added four separate owned Game Boy Advance titles: \`真・女神転生\`
  (#200), \`真・女神転生II\` (#201), \`ブレス オブ ファイア\` (#202),
  and \`MOTHER 1+2\` (#203). The latter is a single physical
  compilation package (reference code AGB-P-A2UJ), not two owned games.
  The GBA Shin Megami Tensei titles are separate physical editions from
  the user's already-registered SFC / PlayStation copies.
- Added \`ワンダープロジェクトJ2 コルロの森のジョゼット\` on
  NINTENDO64 (#204; reference cartridge ID NUS-P-NJ2J). Its original
  retail package may have bundled a Controller Pak, but the presence
  of that accessory in the owner's copy is unverified. Keep the N64 sequel
  separate from the SFC original \`ワンダープロジェクトJ\` (#191).
- Verified all six exact-name, exact-platform Japanese Libretro reference
  boxarts through existing GitHub files and registered them in
  \`data/cover_references.json\`. Reference art is not a photo of the
  owner's physical copy. Packaging, booklet, actual serial and edition
  remain unverified.
- Added missing kana readings for proper Japanese 50-on sorting.
  Tests now check both repaired PC Engine categories and the six new
  item/platform/cover mappings.
