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
