"use strict";

const $ = (id) => document.getElementById(id);
const controls = ["search", "platform", "obi", "sort"];
const GAME_CATEGORY = "ゲームソフト";
let collection = [];
const japaneseTitleCollator = new Intl.Collator("ja-JP", { usage: "sort", numeric: true, sensitivity: "base" });

const SHARE_URL = "https://mao2009.github.io/Collection-Inventory/";
const SHARE_TITLE = "Collection Inventory｜ゲーム・書籍・音楽・映像のコレクション";

function initShareButtons() {
  const status = $("share-status");
  $("share-copy").addEventListener("click", async () => {
    try {
      if (!navigator.clipboard || !navigator.clipboard.writeText) throw new Error("Clipboard unavailable");
      await navigator.clipboard.writeText(SHARE_URL);
      status.textContent = "URLをコピーしました";
    } catch {
      status.textContent = "コピーできませんでした。ブラウザのアドレスバーからURLをコピーしてください。";
    }
  });
  const nativeButton = $("share-native");
  if (typeof navigator.share === "function") {
    nativeButton.hidden = false;
    nativeButton.addEventListener("click", async () => {
      try {
        await navigator.share({
          title: SHARE_TITLE,
          text: "所有ゲームや書籍などのコレクション記録",
          url: SHARE_URL,
        });
      } catch (error) {
        if (error?.name !== "AbortError") {
          status.textContent = "端末の共有メニューを開けませんでした。共有先のボタンかURLコピーを使ってください。";
        }
      }
    });
  }
}

function normalized(value) {
  return String(value ?? "").normalize("NFKC").toLocaleLowerCase("ja-JP");
}

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = String(text);
  return node;
}

function option(value, label) {
  const node = document.createElement("option");
  node.value = value;
  node.textContent = label;
  return node;
}

function gameFiltersActive() {
  return $("category").value === GAME_CATEGORY;
}

function syncCategoryFilters() {
  const active = gameFiltersActive();
  for (const id of ["platform", "obi"]) {
    $(id + "-filter").hidden = !active;
    $(id).disabled = !active;
    if (!active) $(id).value = "";
  }
  $("sort-platform-option").hidden = !active;
  $("sort-platform-option").disabled = !active;
  if (!active && $("sort").value === "platform") $("sort").value = "reading";
}

function populateFilters() {
  const categories = [...new Set(collection.map((item) => item.category).filter(Boolean))]
    .sort((a, b) => a.localeCompare(b, "ja"));
  for (const category of categories) $("category").append(option(category, category));
  const platforms = [...new Set(collection
    .filter((item) => item.category === GAME_CATEGORY)
    .map((item) => item.platform).filter(Boolean))]
    .sort((a, b) => a.localeCompare(b, "ja"));
  for (const platform of platforms) $("platform").append(option(platform, platform));
}

function matches(item) {
  const words = normalized($("search").value).split(/\s+/).filter(Boolean);
  const searchable = normalized([item.id, item.title, item.reading, item.category, item.platform, item.edition, item.serial].join(" "));
  return words.every((word) => searchable.includes(word))
    && (!$("category").value || item.category === $("category").value)
    && (!gameFiltersActive() || (!$("platform").value || item.platform === $("platform").value))
    && (!gameFiltersActive() || (!$("obi").value || item.obi === $("obi").value));
}

function sortable(items) {
  const key = $("sort").value;
  const compareReading = (a, b) => japaneseTitleCollator.compare(a.reading || a.title, b.reading || b.title)
    || japaneseTitleCollator.compare(a.title, b.title)
    || japaneseTitleCollator.compare(a.edition, b.edition)
    || a.id.localeCompare(b.id);
  if (key === "platform") {
    return items.sort((a, b) => japaneseTitleCollator.compare(a.platform, b.platform) || compareReading(a, b));
  }
  return items.sort(compareReading);
}

function imageFor(item, detail = false) {
  const wrap = element("div", detail ? "detail-cover" : "cover");
  const placeholder = () => {
    const empty = element("div", "cover-placeholder");
    empty.append(element("span", "placeholder-platform", item.platform || "COLLECTION"));
    empty.append(element("span", "placeholder-title", item.title));
    empty.append(element("span", "placeholder-status", "ジャケット画像未登録"));
    wrap.replaceChildren(empty);
  };
  if (!item.cover) {
    placeholder();
    return wrap;
  }
  const img = element("img", "", "");
  img.alt = item.title + " の参考ジャケット";
  img.loading = detail ? "eager" : "lazy";
  img.decoding = "async";
  img.referrerPolicy = "no-referrer";
  img.src = item.cover;
  // Steam library artwork is preferred; some apps have only store headers.
  img.addEventListener("error", () => {
    if (item.cover_source === "steam" && item.cover_fallback && img.src !== item.cover_fallback) {
      img.src = item.cover_fallback;
    } else {
      placeholder();
    }
  });
  wrap.append(img);
  if (item.cover_source === "steam") {
    wrap.append(element("span", "reference-label", "Steam画像"));
  } else if (item.cover_source === "libretro" || item.cover_source === "curated") {
    wrap.append(element("span", "reference-label", "参考画像"));
  }
  return wrap;
}

function cardFor(item) {
  const card = element("article", "item-card");
  // The whole card is one accessible action; avoid nested clickable controls.
  card.tabIndex = 0;
  card.setAttribute("role", "button");
  card.setAttribute("aria-haspopup", "dialog");
  card.setAttribute("aria-label", item.title + " の詳細を見る");
  card.addEventListener("click", () => showDetail(item));
  card.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      showDetail(item);
    }
  });
  card.append(imageFor(item));
  const body = element("div", "card-body");
  const top = element("div", "card-top");
  top.append(element("span", "platform-pill", item.category === GAME_CATEGORY ? item.platform : item.category));
  top.append(element("span", "inventory-id", item.id));
  body.append(top);
  const title = element("h3", "card-title", item.title);
  body.append(title);
  body.append(element("p", "edition", item.edition));
  const foot = element("div", "card-foot");
  foot.append(element("span", "ownership", item.ownership));
  // Visual hint only: the surrounding card is the actual click target.
  foot.append(element("span", "detail-button", "詳細を見る ↗"));
  body.append(foot);
  card.append(body);
  return card;
}

function propertyRow(label, value) {
  const row = element("div", "property");
  row.append(element("dt", "", label), element("dd", "", value || "未確認"));
  return row;
}

function showDetail(item) {
  const content = $("detail-content");
  const container = element("div", "detail-layout");
  container.append(imageFor(item, true));
  const details = element("div", "detail-info");
  details.append(element("p", "detail-id", item.id + (item.category === GAME_CATEGORY ? " · " + item.platform : "")));
  const heading = element("h2", "", item.title);
  heading.id = "detail-title";
  details.append(heading);
  const props = element("dl", "properties");
  const obi = { yes: "あり", no: "なし", unknown: "未確認" }[item.obi] || "未確認";
  const properties = [
    ["カテゴリ", item.category], ["エディション", item.edition],
    ["型番（参考含む）", item.serial], ["所有状態", item.ownership],
  ];
  if (item.category === GAME_CATEGORY) properties.push(["機種", item.platform], ["帯", obi]);
  properties.push(
    ["ケース", item.case], ["説明書", item.manual],
    ["ディスク", item.disc], ["動作確認", item.tested],
  );
  for (const [label, value] of properties) props.append(propertyRow(label, value));
  details.append(props);
  const link = element("a", "source-button", "GitHub Issueで原本を見る ↗");
  link.href = item.issue_url;
  link.target = "_blank";
  link.rel = "noopener noreferrer";
  details.append(link);
  container.append(details);
  content.replaceChildren(container);
  $("detail-dialog").showModal();
}

function render() {
  const visible = sortable(collection.filter(matches));
  $("result-count").textContent = visible.length + " / " + collection.length + " 点を表示";
  const fragment = document.createDocumentFragment();
  for (const item of visible) fragment.append(cardFor(item));
  $("items").replaceChildren(fragment);
  $("empty").hidden = visible.length !== 0;
}

function clearFilters() {
  for (const key of ["search", "platform", "category", "obi"]) $(key).value = "";
  $("sort").value = "reading";
  syncCategoryFilters();
  render();
}

async function init() {
  initShareButtons();
  try {
    const response = await fetch("./data/collection.json", { cache: "no-cache" });
    if (!response.ok) throw new Error("HTTP " + response.status);
    const data = await response.json();
    if (!Array.isArray(data.items)) throw new Error("Invalid catalog");
    collection = data.items;
    $("total-count").textContent = collection.length.toLocaleString("ja-JP");
    $("platform-count").textContent = new Set(collection
      .filter((item) => item.category === GAME_CATEGORY)
      .map((item) => item.platform).filter(Boolean)).size;
    populateFilters();
    syncCategoryFilters();
    for (const id of controls) $(id).addEventListener(id === "search" ? "input" : "change", render);
    $("category").addEventListener("change", () => {
      syncCategoryFilters();
      render();
    });
    $("reset").addEventListener("click", clearFilters);
    $("empty-reset").addEventListener("click", clearFilters);
    $("close-dialog").addEventListener("click", () => $("detail-dialog").close());
    $("detail-dialog").addEventListener("click", (event) => {
      if (event.target === $("detail-dialog")) $("detail-dialog").close();
    });
    render();
  } catch (error) {
    console.error("Could not load collection data:", error);
    $("result-count").textContent = "読み込みエラー";
    $("error").hidden = false;
  }
}

init();
