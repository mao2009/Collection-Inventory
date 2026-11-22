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
  through explicit `urls` entries. They have `cover_source=psmt` and display
  the same 参考画像 badge. IDs describe the reference image, **not a verified
  serial number or physical edition of the owned game**.
- Reference images are always selected by exact platform and exact title;
  they are never chosen from a different console or inferred edition.
- Libretro artwork is linked from `raw.githubusercontent.com/libretro-thumbnails`;
  external hosting and original image rights remain with the respective providers.
