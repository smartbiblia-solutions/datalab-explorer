// Builds a Keshif dashboard from a stored view (plain JSON). Shared by the editor and public pages.
import * as kshf from "../keshif/keshif.min.js";

const T = window.DATALAB_T || {};
kshf.Base.loadWebFonts = false;
kshf.Base.defaultBarHeight = 15;

const keshifTexts = Object.fromEntries(
  Object.entries(T).filter(([k]) => k.startsWith("keshif.")).map(([k, v]) => [k.slice(7), v]),
);
if (Object.keys(keshifTexts).length) {
  kshf.LoadLanguage(Object.assign(new kshf.i18n_EN(), keshifTexts));
}

export const escapeHTML = (value) =>
  String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

function safeURL(value) {
  try {
    const url = new URL(String(value));
    return ["http:", "https:"].includes(url.protocol) ? url.href : null;
  } catch {
    return null;
  }
}

function empty(v) {
  return v === undefined || v === null || v === "" || (Array.isArray(v) && v.length === 0);
}

function parseDate(v) {
  const s = String(v);
  const fr = s.match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
  const d = fr ? new Date(Date.UTC(+fr[3], +fr[2] - 1, +fr[1])) : new Date(s);
  return Number.isFinite(d.getTime()) ? d : null;
}

function toNumber(v) {
  const n = typeof v === "number" ? v : Number(String(v).replace(",", "."));
  return Number.isFinite(n) ? n : null;
}

// One accessor per column type. Keshif calls it with the record as `this`.
function accessor(c) {
  const { column, type, separator } = c;
  return function () {
    const v = this[column];
    if (empty(v)) return null;
    if (Array.isArray(v)) return v.map(String);
    if (type === "number") return toNumber(v);
    if (type === "year") {
      const y = parseInt(v, 10);
      return Number.isFinite(y) ? new Date(Date.UTC(y, 0, 1)) : null;
    }
    if (type === "date") return parseDate(v);
    if (separator) {
      const parts = String(v).split(separator).map((s) => s.trim()).filter(Boolean);
      return parts.length ? parts : null;
    }
    return String(v);
  };
}

function display(v, separator) {
  if (Array.isArray(v)) return v.join(" · ");
  if (separator && typeof v === "string") return v.split(separator).map((x) => x.trim()).filter(Boolean).join(" · ");
  return v;
}

function recordCard(config) {
  const d = config.display;
  const byName = Object.fromEntries(config.columns.map((c) => [c.column, c]));
  return function () {
    const title = escapeHTML(display(this[d.title]) || "—");
    const href = d.link ? safeURL(this[d.link]) : null;
    const head = href
      ? `<a href="${escapeHTML(href)}" target="_blank" rel="noopener noreferrer">${title}</a>`
      : title;
    const details = d.details
      .filter((col) => col !== d.title && !empty(this[col]))
      .map((col) => {
        const c = byName[col] || { label: col };
        return `<span><b>${escapeHTML(c.label)}</b> ${escapeHTML(display(this[col], c.type === "text" ? c.separator : ""))}</span>`;
      })
      .join("");
    return `<div class="dl-card"><div class="dl-card-title">${head}</div><div class="dl-card-details">${details}</div></div>`;
  };
}

export function keshifOptions(config) {
  const shown = config.columns.filter((c) => c.include);
  const summaries = shown.map((c) => ({
    name: c.label,
    panel: c.panel,
    collapsed: c.collapsed,
    value: accessor(c),
  }));
  const d = config.display;
  const names = new Set(summaries.map((s) => s.name));
  const unique = (name) => {
    while (names.has(name)) name += " ";
    names.add(name);
    return name;
  };
  // Hidden summaries: one carries the record card (and the text search), one the sort order.
  const searchName = unique(T["js.search"] || "Search");
  summaries.push({ name: searchName, panel: "none", value: recordCard(config) });
  const sortColumn = config.columns.find((c) => c.column === d.sort);
  let sortName;
  if (sortColumn?.include) {
    sortName = sortColumn.label;
  } else if (sortColumn) {
    sortName = unique(sortColumn.label);
    summaries.push({ name: sortName, panel: "none", value: accessor({ ...sortColumn, separator: "" }) });
  } else {
    sortName = unique(T["js.file_order"] || "File order");
    summaries.push({ name: sortName, panel: "none", value: function () { return Number(this._row); } });
  }
  return {
    summaries,
    recordDisplay: {
      viewAs: "list",
      list_ViewType: d.layout === "grid" ? "Grid" : "List",
      textBy: searchName,
      sortBy: sortName,
      list_sortInverse: sortColumn ? !d.sort_desc : true,
      list_sortVizWidth: 0,
      list_sortColWidth: 45,
    },
  };
}

export class Dashboard {
  constructor(element) {
    this.element = element;
    this.browser = null;
  }

  async show(rows, config, extra = {}) {
    this.destroy();
    const { summaries, recordDisplay } = keshifOptions(config);
    await new Promise((resolve) => {
      this.browser = new kshf.Browser({
        domID: "#" + this.element.id,
        recordName: T["js.records"] || "Records",
        enableAuthoring: false,
        confirmLargeRecordView: false,
        minRecordViewHeight: 420,
        barChartWidth: 100,
        leftPanelLabelWidth: 160,
        rightPanelLabelWidth: 160,
        middlePanelLabelWidth: 160,
        source: {
          name: "data_" + Math.random().toString(36).slice(2),
          id: "_row",
          onLoad: function () {
            rows.forEach((r) => this.createRecord({ ...r }));
            return true;
          },
        },
        summaries,
        recordDisplay,
        onReady: () => resolve(),
        ...extra,
      });
    });
    // Keshif ignores list settings passed at creation; apply them through its own setters.
    const list = this.browser.recordDisplay?.View;
    if (list?.list_ViewType) {
      await list.list_ViewType.set(recordDisplay.list_ViewType);
      await list.list_sortInverse.set(recordDisplay.list_sortInverse);
    }
  }

  selectedRows() {
    return (this.browser?.records || []).filter((r) => r.isIncluded).map((r) => r.data);
  }

  destroy() {
    this.browser?.destroy();
    this.browser = null;
    this.element.innerHTML = "";
  }
}

// CSV for spreadsheet software: semicolon separated, UTF-8 with a byte-order mark.
export function downloadCSV(rows, config, filename) {
  const d = config.display;
  const wanted = new Set([d.title, ...config.columns.filter((c) => c.include).map((c) => c.column), ...d.details, d.link]);
  const columns = config.columns.filter((c) => wanted.has(c.column));
  const cell = (v) => {
    const s = String(display(v) ?? "");
    return /[";\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const lines = [columns.map((c) => cell(c.label)).join(";")];
  for (const r of rows) lines.push(columns.map((c) => cell(r[c.column])).join(";"));
  const blob = new Blob(["﻿" + lines.join("\r\n")], { type: "text/csv;charset=utf-8" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  link.click();
  setTimeout(() => URL.revokeObjectURL(link.href), 1000);
}
