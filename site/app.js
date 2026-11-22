"use strict";

const $ = (id) => document.getElementById(id);
const controls = ["search", "platform", "category", "obi", "sort"];
let collection = [];

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

function populateFilters() {
  for (const key of ["platform", "category"]) {
    const options = [...new Set(collection.map((item) => item[key]))].sort((a, b) => a.localeCompare(b, "ja"));
    for (const value of options) $(key).append(option(value, value));
  }
}

function matches(item) {
  const words = normalized($("search").value).split(/\s+/).filter(Boolean);
  const searchable = normalized([item.id, item.title, item.category, item.platform, item.edition, item.serial].join(" "));
  return words.every((word) => searchable.includes(word))
    && (!$("platform").value || item.platform === $("platform").value)
    && (!$("category").value || item.category === $("category").value)
    && (!$("obi").value || item.obi === $("obi").value);
}

function sortable(items) {
  const key = $("sort").value;
  if (key === "id") return items.sort((a, b) => Number(a.id.slice(4)) - Number(b.id.slice(4)));
  return items.sort((a, b) => a[key].localeCompare(b[key], "ja") || a.id.localeCompare(b.id));
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
  img.addEventListener("error", placeholder, { once: true });
  wrap.append(img);
  if (item.cover_source === "libretro" || item.cover_source === "psmt") {
    wrap.append(element("span", "reference-label", "参考画像"));
  }
  return wrap;
}

function cardFor(item) {
  const card = element("article", "item-card");
  card.append(imageFor(item));
  const body = element("div", "card-body");
  const top = element("div", "card-top");
  top.append(element("span", "platform-pill", item.platform));
  top.append(element("span", "inventory-id", item.id));
  body.append(top);
  const title = element("h3", "card-title", item.title);
  body.append(title);
  body.append(element("p", "edition", item.edition));
  const foot = element("div", "card-foot");
  foot.append(element("span", "ownership", item.ownership));
  const detail = element("button", "detail-button", "詳細を見る ↗");
  detail.type = "button";
  detail.setAttribute("aria-label", item.title + " の詳細を見る");
  detail.addEventListener("click", () => showDetail(item));
  foot.append(detail);
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
  details.append(element("p", "detail-id", item.id + " · " + item.platform));
  const heading = element("h2", "", item.title);
  heading.id = "detail-title";
  details.append(heading);
  const props = element("dl", "properties");
  const obi = { yes: "あり", no: "なし", unknown: "未確認" }[item.obi] || "未確認";
  for (const [label, value] of [
    ["カテゴリ", item.category], ["エディション", item.edition],
    ["型番（参考含む）", item.serial], ["所有状態", item.ownership],
    ["帯", obi], ["ケース", item.case], ["説明書", item.manual],
    ["ディスク", item.disc], ["動作確認", item.tested],
  ]) props.append(propertyRow(label, value));
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
  $("sort").value = "id";
  render();
}

async function init() {
  try {
    const response = await fetch("./data/collection.json", { cache: "no-cache" });
    if (!response.ok) throw new Error("HTTP " + response.status);
    const data = await response.json();
    if (!Array.isArray(data.items)) throw new Error("Invalid catalog");
    collection = data.items;
    $("total-count").textContent = collection.length.toLocaleString("ja-JP");
    $("platform-count").textContent = new Set(collection.map((item) => item.platform)).size;
    populateFilters();
    for (const id of controls) $(id).addEventListener(id === "search" ? "input" : "change", render);
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
