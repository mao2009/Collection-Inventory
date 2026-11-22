#!/usr/bin/env python3
"""Export public-facing collection fields from GitHub Issues for GitHub Pages.

Issues are the source of truth; never export raw bodies or arbitrary Issue fields.
Works with the original "- 項目：値" Issues and GitHub Issue Form "### 項目" bodies.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import unicodedata
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

REPO = "mao2009/Collection-Inventory"
BULLET = re.compile(r"^\s*[-*]\s+([^：:\n]+)[：:]\s*(.*?)\s*$", re.M)
IMAGE = re.compile(r"!\[[^\]]*\]\((https://[^)\s]+)\)")
INV = re.compile(r"\bINV-\d+\b", re.I)
REFERENCE_COVERS = json.loads(
    (Path(__file__).resolve().parent.parent / "data/cover_references.json").read_text(encoding="utf-8")
)["platforms"]


def plain(value):
    return re.sub(r"\*\*|__", "", str(value or "")).strip()


def fields_from_body(body):
    fields = {plain(key): plain(value) for key, value in BULLET.findall(body)}
    parts = re.split(r"(?m)^###\s+(.+?)\s*$", body)
    for index in range(1, len(parts) - 1, 2):
        name = plain(parts[index])
        lines = [plain(line) for line in parts[index + 1].splitlines() if line.strip()]
        if lines and lines[0] not in ("_No response_", "No response"):
            fields[name] = lines[0]
    return fields


def first(fields, *names):
    for name in names:
        if fields.get(name):
            return fields[name]
    return ""


def field_prefix(fields, prefix):
    for key, value in fields.items():
        if key.startswith(prefix) and value:
            return value
    return ""


def platform_name(raw):
    value = unicodedata.normalize("NFKC", raw).casefold().replace(" ", "")
    if "playstation2" in value or "ps2" in value:
        return "PlayStation 2"
    if value in ("ps", "ps1", "playstation") or "playstation(ps1)" in value:
        return "PlayStation"
    if "pcエンジン" in value or "pcengine" in value or "pc-engine" in value:
        return "PCエンジン"
    return raw or "未分類"


def obi_status(raw):
    value = plain(raw)
    if not value or "未確認" in value or "不明" in value or "未記録" in value:
        return "unknown"
    if any(word in value for word in ("なし", "無し", "欠品", "付属せず")):
        return "no"
    if any(word in value for word in ("あり", "有り", "付き", "付属")):
        return "yes"
    return "unknown"


def safe_https(url):
    try:
        parsed = urlparse(url)
        if parsed.scheme == "https" and parsed.hostname and not parsed.username and not parsed.password:
            return url
    except ValueError:
        pass
    return ""


def reference_cover(platform, title):
    """Look up only explicitly mapped titles; never infer a cover for a different game."""
    group = REFERENCE_COVERS.get(platform, {})
    filename = group.get("images", {}).get(title)
    repo = group.get("repo")
    if not filename or not repo:
        return ""
    return (
        "https://raw.githubusercontent.com/libretro-thumbnails/"
        + quote(repo, safe="")
        + "/master/Named_Boxarts/"
        + quote(filename, safe="")
    )


def supplemental_cover(platform, title):
    """Use an exact-title, exact-platform URL verified in our curated data."""
    url = REFERENCE_COVERS.get(platform, {}).get("urls", {}).get(title, "")
    return safe_https(url)


def inventory_item(issue):
    if "pull_request" in issue:
        return None
    body = issue.get("body") or ""
    fields = fields_from_body(body)
    labels = {
        label.get("name", "") if isinstance(label, dict) else str(label)
        for label in issue.get("labels", [])
    }
    is_inventory = bool(
        first(fields, "管理番号")
        or "所有" in labels
        or (first(fields, "タイトル") and first(fields, "所持状態"))
    )
    if not is_inventory:
        return None

    number = int(issue["number"])
    raw_id = first(fields, "管理番号")
    match = INV.search(raw_id)
    inventory_id = match.group().upper() if match else "INV-" + str(number).zfill(3)
    title = first(fields, "タイトル")
    if not title:
        title = re.sub(r"^(?:\[[^\]]+\]\s*|INV-\d+\s*)+", "", issue.get("title") or "").strip()
    if not title:
        return None

    serial = field_prefix(fields, "製品型番") or first(fields, "品番・型番", "現物型番")
    if not serial or serial.startswith("未確認"):
        serial = first(fields, "参考候補（現物との一致未確認）") or serial

    images = IMAGE.findall(body)
    cover = first(fields, "画像URL（任意）", "画像URL")
    if not safe_https(cover):
        cover = images[0] if images else ""
    cover = safe_https(cover)
    cover_source = "issue" if cover else ""
    if not cover:
        cover = reference_cover(platform_name(first(fields, "機種", "プラットフォーム・対応機種")), title)
        if cover:
            cover_source = "libretro"
    if not cover:
        cover = supplemental_cover(platform_name(first(fields, "機種", "プラットフォーム・対応機種")), title)
        if cover:
            cover_source = "psmt"

    ownership = first(fields, "所持状態", "所有", "所持")
    if "譲渡・売却済み" in ownership:
        ownership = "譲渡・売却済み"
    elif "所有" in labels or "所有" in ownership or "確認済み" in ownership:
        ownership = "所有"
    else:
        ownership = "未確認"

    return {
        "id": inventory_id,
        "title": title,
        "category": first(fields, "分類", "カテゴリ") or "未分類",
        "platform": platform_name(first(fields, "機種", "プラットフォーム・対応機種")),
        "edition": first(fields, "エディション") or "未確認",
        "serial": serial or "未確認",
        "ownership": ownership,
        "obi": obi_status(first(fields, "帯")),
        "case": first(fields, "ケース") or "未確認",
        "manual": first(fields, "説明書") or "未確認",
        "disc": first(fields, "ディスク", "ディスク状態") or "未確認",
        "tested": first(fields, "動作確認") or "未確認",
        "cover": cover,
        "cover_source": cover_source,
        "issue_url": "https://github.com/" + REPO + "/issues/" + str(number),
    }


def build(issues):
    items = [item for issue in issues if (item := inventory_item(issue)) is not None]
    items.sort(key=lambda item: (int(item["id"][4:]), item["issue_url"]))
    ids = [item["id"] for item in items]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate inventory IDs in Issues; correct them before publishing")
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "GitHub Issues",
        "items": items,
    }


def fetch_issues(repo):
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    items = []
    page = 1
    while True:
        url = "https://api.github.com/repos/" + repo + "/issues?state=all&per_page=100&page=" + str(page)
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "collection-inventory-pages",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if token:
            headers["Authorization"] = "Bearer " + token
        request = Request(url, headers=headers)
        with urlopen(request, timeout=30) as response:
            batch = json.load(response)
        if not isinstance(batch, list):
            raise ValueError("GitHub API did not return an Issue list")
        items.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return items


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", help="Local Issue API JSON fixture, instead of GitHub API")
    parser.add_argument("--output", default="site/data/collection.json")
    args = parser.parse_args()

    if args.input:
        with open(args.input, encoding="utf-8") as source:
            issues = json.load(source)
    else:
        issues = fetch_issues(REPO)
    catalog = build(issues)
    if not catalog["items"]:
        raise ValueError("No inventory items found; refusing to publish an empty catalog")

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Exported " + str(len(catalog["items"])) + " inventory entries to " + str(output))


if __name__ == "__main__":
    main()
