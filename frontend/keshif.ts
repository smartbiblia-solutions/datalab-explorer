// The renderer is retained as an independent, checksum-inventoried distribution.
// @ts-ignore Runtime module is built and checksum-verified separately.
const Runtime = await import("/static/dist/keshif.js");
const { Browser, Base, Filter_Base, LoadLanguage, i18n_EN } = Runtime;
import { lang, keshifFrench } from "./i18n";
export type Row = Record<string, any> & { __id: string };
export type Field = {
  id: string;
  label: string;
  type: string;
  role: string;
  visible?: boolean;
  panel?: string;
  collapsed?: boolean;
  delimiter?: string;
  missing?: number;
  unique?: number;
};
export type Dashboard = {
  name?: string;
  facets?: string[];
  view?: string;
  title?: string;
  x?: string;
  y?: string;
  latitude?: string;
  longitude?: string;
  color?: string;
  size?: string;
  card?: string[];
};
export const esc = (v: unknown) =>
  String(v ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ]!,
  );
export function safeLink(value: unknown): string | null {
  try {
    const u = new URL(String(value));
    return ["http:", "https:"].includes(u.protocol) ? u.href : null;
  } catch {
    return null;
  }
}
export class KeshifAdapter {
  browser: any;
  observer?: ResizeObserver;
  name = "";
  disposed = false;
  constraint: any;
  ids: string[] = [];
  async mount(
    el: HTMLElement,
    rows: Row[],
    fields: Field[],
    config: Dashboard,
    change: (ids: string[]) => void,
    restore?: string[],
  ) {
    this.disposed = false;
    this.name = "data_" + crypto.randomUUID();
    LoadLanguage(
      Object.assign(new i18n_EN(), lang === "fr" ? keshifFrench : {}),
    );
    if (!rows.length) {
      el.textContent = lang === "fr" ? "Aucune donnée" : "No records";
      change([]);
      return;
    }
    const names = new Map(fields.map((f) => [f.id, esc(f.label || f.id)]));
    const pick = (id?: string) => (id ? names.get(id) : undefined);
    const accessor = (f: Field) =>
      function (this: Row) {
        let v = this[f.id];
        if (v === null || v === undefined || v === "") return null;
        if (f.type === "date") {
          const d = new Date(v);
          return Number.isFinite(d.getTime()) ? d : null;
        }
        if (f.type === "boolean") return String(v);
        if (f.delimiter && typeof v === "string") return v.split(f.delimiter);
        if (typeof v === "object" && !Array.isArray(v))
          return JSON.stringify(v);
        return v;
      };
    const summaries: any[] = fields.map((f) => ({
      name: names.get(f.id),
      value: accessor(f),
      panel: (
        config.facets ??
        fields
          .filter((f) => f.visible !== false)
          .slice(0, 5)
          .map((f) => f.id)
      ).includes(f.id)
        ? f.panel || "left"
        : "none",
      collapsed: f.collapsed ?? false,
    }));
    const order = new Map(rows.map((r, i) => [r.__id, i]));
    summaries.push({
      name: "_StudioOrder",
      panel: "none",
      type: "numeric",
      value: function (this: Row) {
        return order.get(this.__id);
      },
    });
    const title =
      config.title ||
      fields.find((f) => f.role === "title")?.id ||
      fields[0]?.id;
    const card = config.card?.length
      ? config.card
      : ([title].filter(Boolean) as string[]);
    summaries.push({
      name: "_StudioCard",
      panel: "none",
      value: function (this: Row) {
        return card
          .map((id) => {
            const field = fields.find((f) => f.id === id);
            const link = field?.role === "link" ? safeLink(this[id]) : null;
            return `<div><strong>${esc(field?.label || id)}</strong> ${link ? `<a target="_blank" rel="noopener noreferrer" href="${esc(link)}">${esc(this[id])}</a>` : esc(Array.isArray(this[id]) ? this[id].join(" · ") : this[id])}</div>`;
          })
          .join("");
      },
    });
    if (config.latitude && config.longitude)
      summaries.push({
        name: "_StudioGeo",
        type: "recordGeo",
        panel: "none",
        value: function (this: Row) {
          const a = this[config.latitude!],
            b = this[config.longitude!];
          if (a === null || b === null || a === "" || b === "") return null;
          const lat = Number(a),
            lon = Number(b);
          return Number.isFinite(lat) &&
            Number.isFinite(lon) &&
            Math.abs(lat) <= 90 &&
            Math.abs(lon) <= 180
            ? { type: "Point", coordinates: [lon, lat] }
            : null;
        },
      });
    const rd: any = {
      viewAs: config.view || "list",
      textBy: "_StudioCard",
      sortBy:
        pick(fields.find((f) => f.type === "number")?.id) || "_StudioOrder",
      scatterXBy: pick(config.x),
      scatterYBy: pick(config.y),
      geoBy: config.latitude && config.longitude ? "_StudioGeo" : undefined,
      mapConfig: {
        tileConfig: { disabled: true },
        leafConfig: { maxZoom: 18, minZoom: 1 },
      },
      colorBy: pick(config.color),
      sizeBy: pick(config.size),
    };
    if (rd.viewAs === "scatter" && (!rd.scatterXBy || !rd.scatterYBy))
      rd.viewAs = "list";
    if (rd.viewAs === "map" && !rd.geoBy) rd.viewAs = "list";
    // Only trusted closures enter Keshif. Project JSON never supplies JavaScript.
    await new Promise<void>((resolve, reject) => {
      const timeout = window.setTimeout(
        () => reject(new Error("Keshif initialization timed out")),
        20000,
      );
      this.browser = new Browser({
        domID: "#" + el.id,
        recordName: "Records",
        enableAuthoring: false,
        recordViewMinHeight: 360,
        source: {
          name: this.name,
          id: "__id",
          onLoad: function (this: any) {
            rows.forEach((r) => this.createRecord({ ...r }));
            return true;
          },
        },
        summaries,
        recordDisplay: rd,
        onSelectionChange: (ids: string[]) => {
          if (!this.disposed) {
            this.ids = ids;
            change(ids);
          }
        },
        onReady: () => {
          window.clearTimeout(timeout);
          queueMicrotask(() => {
            if (this.disposed) {
              resolve();
              return;
            }
            if (restore !== undefined) this.setIDs(restore);
            else {
              this.ids = rows.map((r) => r.__id);
              change(this.ids);
            }
            resolve();
          });
        },
      });
    });
    this.observer = new ResizeObserver(() => {
      if (!this.disposed && el.offsetWidth) this.browser?.updateLayout();
    });
    this.observer.observe(el);
  }
  setIDs(ids: string[]) {
    if (!this.browser?.finalized) return;
    const wanted = new Set(ids);
    if (!this.constraint) {
      const b = this.browser;
      this.constraint = new (class extends Filter_Base {
        constructor(browser: any) {
          super(browser);
        }
        get title() {
          return lang === "fr" ? "Cohorte épinglée" : "Pinned cohort";
        }
        filterView_Detail() {
          return String(wanted.size);
        }
        onFilter() {}
        onClear() {}
      })(b);
    }
    this.browser.records.forEach((r: any) =>
      r.setFilterCache(this.constraint.filterID, wanted.has(String(r.id))),
    );
    this.constraint.how = "All";
    this.constraint.setFiltered();
  }
  clear() {
    this.browser?.clearFilters_All();
  }
  nativeState() {
    try {
      return this.browser?.exportConfig();
    } catch {
      return null;
    }
  }
  destroy() {
    this.disposed = true;
    this.observer?.disconnect();
    if (this.browser) {
      delete Base.browsers[this.browser.getDashboardID()];
      this.browser.finalized = false;
      Base.tables.delete(this.name);
      const root = this.browser.DOM?.root?.node();
      root?.querySelectorAll("*").forEach((el: any) => {
        el._tippy?.destroy();
        if (el.tippy && el.tippy !== el._tippy) el.tippy.destroy?.();
      });
      this.browser.DOM?.root?.selectAll("*").interrupt();
      this.browser.DOM?.root?.selectAll("*").remove();
      this.browser = null;
    }
  }
}
