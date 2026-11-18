// View editor: column settings on the left, the live Keshif dashboard on the right.
import { Dashboard, escapeHTML } from "./dashboard.js";

const T = window.DATALAB_T || {};
const page = JSON.parse(document.getElementById("view-data").textContent);
const config = page.config;
const described = Object.fromEntries(page.described.map((c) => [c.name, c]));
const csrf = document.querySelector("meta[name=csrf-token]").content;

const $ = (id) => document.getElementById(id);
const dashboard = new Dashboard($("dashboard"));
let rows = [];
let dirty = false;
let timer = null;
let stale = false; // settings changed since the dashboard was last drawn
let drawing = false;
const LIVE_KEY = "datalab.liveRefresh";
const LIVE_LIMIT = 5000; // larger datasets start with manual refresh

function storedLive() {
  try {
    const v = localStorage.getItem(LIVE_KEY);
    return v === null ? null : v === "1";
  } catch {
    return null;
  }
}

function storeLive(value) {
  try {
    localStorage.setItem(LIVE_KEY, value ? "1" : "0");
  } catch {
    /* private browsing: the choice lasts for this page only */
  }
}

function updateRefreshButton() {
  const live = $("live-refresh").checked;
  const button = $("refresh-dashboard");
  button.hidden = live;
  button.disabled = drawing || !stale;
  button.classList.toggle("btn-primary", stale);
  button.classList.toggle("btn-outline-primary", !stale);
  button.textContent = drawing ? T["js.refreshing"] : T["js.refresh"];
}

const PANELS = ["left", "middle", "right", "bottom"];
const TYPES = ["text", "number", "year", "date"];

function options(values, selected, label = (v) => T["js." + v] || v) {
  return values
    .map((v) => `<option value="${escapeHTML(v)}"${v === selected ? " selected" : ""}>${escapeHTML(label(v))}</option>`)
    .join("");
}

function renderColumns() {
  $("columns-body").innerHTML = config.columns
    .map((c, i) => {
      const info = described[c.column] || {};
      const hint = `${T["js.distinct"]}: ${info.distinct ?? "?"} · ${T["js.missing"]}: ${info.missing ?? "?"}` +
        (info.samples?.length ? ` · ${info.samples.join(" | ")}` : "");
      return `<tr data-i="${i}" class="${c.include ? "" : "text-muted"}">
        <td><input class="form-check-input" type="checkbox" data-k="include" ${c.include ? "checked" : ""} aria-label="${escapeHTML(T["js.show"])} ${escapeHTML(c.column)}"></td>
        <td class="dl-colname" title="${escapeHTML(hint)}">${escapeHTML(c.column)}</td>
        <td><input class="form-control form-control-sm" data-k="label" value="${escapeHTML(c.label)}"></td>
        <td><select class="form-select form-select-sm" data-k="type">${options(TYPES, c.type)}</select></td>
        <td><input class="form-control form-control-sm dl-sep" data-k="separator" value="${escapeHTML(c.separator)}" maxlength="3" ${c.type === "text" ? "" : "disabled"}></td>
        <td><select class="form-select form-select-sm" data-k="panel">${options(PANELS, c.panel)}</select></td>
        <td><input class="form-check-input" type="checkbox" data-k="collapsed" ${c.collapsed ? "checked" : ""} aria-label="${escapeHTML(T["js.collapsed"])}"></td>
      </tr>`;
    })
    .join("");
}

function renderDisplay() {
  const d = config.display;
  const all = config.columns.map((c) => c.column);
  const label = (v) => (v ? config.columns.find((c) => c.column === v)?.label || v : T["js.none"]);
  $("display-layout").innerHTML = options(["list", "grid"], d.layout);
  $("display-title").innerHTML = options(all, d.title, label);
  $("display-link").innerHTML = options(["", ...all], d.link, label);
  const sortable = config.columns.filter((c) => c.type !== "text").map((c) => c.column);
  $("display-sort").innerHTML = options(["", ...sortable], d.sort, label);
  $("display-order").value = d.sort_desc ? "desc" : "asc";
  $("display-details").innerHTML = config.columns
    .map((c) => `<label class="form-check"><input class="form-check-input" type="checkbox" value="${escapeHTML(c.column)}" ${d.details.includes(c.column) ? "checked" : ""}> ${escapeHTML(c.label)}</label>`)
    .join("");
}

function setDirty(value) {
  dirty = value;
  $("save-state").textContent = value ? T["js.unsaved"] : T["js.saved"];
  $("save-state").classList.toggle("text-warning", value);
}

function changed() {
  setDirty(true);
  stale = true;
  clearTimeout(timer);
  if ($("live-refresh").checked) timer = setTimeout(redraw, 500);
  else updateRefreshButton();
}

async function redraw() {
  clearTimeout(timer);
  const labels = config.columns.filter((c) => c.include).map((c) => c.label.trim());
  const duplicate = labels.find((l, i) => labels.indexOf(l) !== i);
  if (duplicate) {
    showMessage(T["js.duplicate_label"].replace("{label}", duplicate), "danger");
    return;
  }
  if (!labels.length) {
    showMessage(T["js.no_facet"], "warning");
  } else {
    showMessage("");
  }
  stale = false;
  drawing = true;
  updateRefreshButton();
  try {
    await dashboard.show(rows, config);
  } finally {
    drawing = false;
    updateRefreshButton();
  }
}

$("live-refresh").addEventListener("change", (e) => {
  storeLive(e.target.checked);
  if (e.target.checked && stale) redraw();
  else updateRefreshButton();
});

$("refresh-dashboard").addEventListener("click", redraw);

function showMessage(text, kind = "info") {
  $("editor-message").innerHTML = text ? `<div class="alert alert-${kind} py-2 mb-2">${escapeHTML(text)}</div>` : "";
}

$("columns-body").addEventListener("change", (e) => {
  const tr = e.target.closest("tr");
  const c = config.columns[Number(tr.dataset.i)];
  const key = e.target.dataset.k;
  c[key] = e.target.type === "checkbox" ? e.target.checked : e.target.value;
  if (key === "include" || key === "type") renderColumns();
  if (key === "label" || key === "type") renderDisplay();
  changed();
});

$("display-form").addEventListener("change", () => {
  const d = config.display;
  d.layout = $("display-layout").value;
  d.title = $("display-title").value;
  d.link = $("display-link").value;
  d.sort = $("display-sort").value;
  d.sort_desc = $("display-order").value === "desc";
  d.details = [...$("display-details").querySelectorAll("input:checked")].map((el) => el.value);
  changed();
});

$("view-name").addEventListener("input", () => setDirty(true));

async function save() {
  const response = await fetch(page.saveUrl, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
    body: JSON.stringify({ name: $("view-name").value, config }),
  });
  const result = await response.json().catch(() => ({}));
  if (!response.ok) {
    showMessage(result.error || T["js.save_failed"], "danger");
    return false;
  }
  setDirty(false);
  showMessage(result.message, "success");
  return true;
}

$("save-view").addEventListener("click", save);

// Publishing uses the saved configuration: save pending changes first.
$("publish-form").addEventListener("submit", async (e) => {
  if (!dirty) return;
  e.preventDefault();
  if (await save()) e.target.submit();
});

$("toggle-settings").addEventListener("click", () => {
  document.querySelector(".dl-editor").classList.toggle("dl-settings-hidden");
  dashboard.browser?.updateLayout();
});

window.addEventListener("beforeunload", (e) => {
  if (dirty) e.preventDefault();
});

renderColumns();
renderDisplay();
setDirty(false);
rows = await (await fetch(page.dataUrl)).json();
$("live-refresh").checked = storedLive() ?? rows.length <= LIVE_LIMIT;
await redraw();
