#!/usr/bin/env python3
"""Resolve exact Steam application IDs for screenshot-verified library games.

Run at GitHub Pages build time, without Steam user credentials or API keys.
The resulting data is a *public catalogue of cover references*, not proof
of purchases, entitlements, or license duration.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
import re
import sys
import unicodedata
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "data/steam_screenshot_import_20261122.json"
VERIFIED = ROOT / "data/steam_verified_appids.json"
OUTPUT = ROOT / "site/data/steam_cover_index.json"

ALIASES = {
    "RAIDOU Remastered: 超力兵団奇譚": ["RAIDOU Remastered: The Mystery of the Soulless Army"],
    "ブレス オブ ファイアIV うつろわざるもの": ["Breath of Fire IV", "Breath of Fire IV: The Unfading Ones"],
    "真・女神転生V Vengeance": ["Shin Megami Tensei V: Vengeance"],
    "シロナガス島への帰還 -Return to Shironagasu Island-": ["Return to Shironagasu Island"],
    "Persona 5 Strikers": ["Persona® 5 Strikers"],
    "The Elder Scrolls V: Skyrim": ["The Elder Scrolls V: Skyrim"],
    "The Caligula Effect: Overdose": ["The Caligula Effect: Overdose"],
    "The Caligula Effect 2": ["The Caligula Effect 2"],
    "HITMAN (2016)": ["HITMAN", "HITMAN™"],
    "G-MODEアーカイブス+ 真・女神転生-20XX": ["G-MODEアーカイブス+ 真・女神転生-20XX"],
}


def normalized(value):
    value = unicodedata.normalize("NFKC", str(value)).casefold()
    return "".join(ch for ch in value if ch.isalnum())


def steam_images(appid):
    appid = int(appid)
    if not 1 <= appid <= 99999999:
        raise ValueError("Steam AppID is out of range")
    root = f"https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/{appid}/"
    return {
        "appid": appid,
        "cover": root + "library_600x900.jpg",
        "fallback": root + "header.jpg",
    }


def search_steam(title):
    targets = {normalized(x) for x in [title] + ALIASES.get(title, [])}
    query_terms = [title]
    for alias in ALIASES.get(title, []):
        if alias != title:
            query_terms.append(alias)
    for term in query_terms[:3]:
        for language, country in (("english", "US"), ("japanese", "JP")):
            query = urlencode({"term": term, "l": language, "cc": country})
            url = "https://store.steampowered.com/api/storesearch/?" + query
            req = Request(url, headers={
                "User-Agent": "Mozilla/5.0 (compatible; CollectionInventory/1.0)",
                "Accept": "application/json",
            })
            try:
                with urlopen(req, timeout=13) as response:
                    data = json.load(response)
            except (OSError, ValueError):
                continue
            matches = [
                int(item["id"]) for item in data.get("items", [])
                if item.get("type", "app") == "app"
                and isinstance(item.get("id"), int)
                and normalized(item.get("name", "")) in targets
            ]
            # Never silently assign the wrong franchise installment, remaster,
            # DLC, edition, or an unrelated title with a similar spelling.
            if len(set(matches)) == 1:
                return matches[0]
    return None


def resolve(offline=False):
    records = json.loads(MANIFEST.read_text(encoding="utf-8"))["records"]
    pinned = json.loads(VERIFIED.read_text(encoding="utf-8"))["appids"]
    titles = [r["title"] for r in records]
    if len(set(titles)) != len(titles):
        raise ValueError("Steam screenshot manifest contains duplicate titles")
    if set(pinned) - set(titles):
        raise ValueError("Pinned Steam app id has no matching game title")
    appids = {name: int(value) for name, value in pinned.items()}
    unresolved = [title for title in titles if title not in appids]
    if not offline:
        with ThreadPoolExecutor(max_workers=4) as executor:
            tasks = {executor.submit(search_steam, title): title for title in unresolved}
            for task in as_completed(tasks):
                title = tasks[task]
                try:
                    appid = task.result()
                except Exception as error:
                    print(f"Steam search skipped {title}: {type(error).__name__}", file=sys.stderr)
                    continue
                if appid:
                    appids[title] = appid
    result = {
        "source": "Verified Steam AppIDs plus exact-title Steam Store searches",
        "apps": {title: steam_images(appids[title]) for title in titles if title in appids},
        "unresolved": [title for title in titles if title not in appids],
    }
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--report", action="store_true")
    args = parser.parse_args()
    result = resolve(offline=args.offline)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"STEAM_COVERS_RESOLVED={len(result['apps'])}/86")
    if result["unresolved"]:
        print("STEAM_COVERS_UNRESOLVED=" + json.dumps(result["unresolved"], ensure_ascii=False))
    if args.report:
        print("STEAM_APPIDS_JSON=" + json.dumps({
            title: item["appid"] for title, item in result["apps"].items()
        }, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
