import { KeshifAdapter, Row, Field, Dashboard, esc } from "./keshif";
import { t, lang, setLanguage, Lang } from "./i18n";
const $ = <T extends HTMLElement = HTMLElement>(id: string) =>
  document.getElementById(id) as T;
let csrf = "",
  user: any = null,
  pid = "",
  project: any = null,
  meta: any = null,
  version: any = null,
  fields: Field[] = [],
  rows: Row[] = [],
  objects: any[] = [],
  dashboard: Dashboard = {},
  selected = new Set<string>(),
  adapter = new KeshifAdapter(),
  activeTab = "sources",
  page = 0,
  sort = "",
  reverse = false,
  review: any = null,
  publicPayload: any = null,
  publicSelected: string[] | undefined;
let chartGeneration = 0;
const val = (id: string) => $<HTMLInputElement>(id).value;
const json = (v: any) => JSON.stringify(v, null, 2);
function notice(message: string, error = false) {
  $("notice").textContent = message;
  $("notice").classList.toggle("error", error);
}
async function api(path: string, body?: any, method?: string): Promise<any> {
  const headers: Record<string, string> = { "X-CSRF-Token": csrf };
  if (body !== undefined && !(body instanceof FormData))
    headers["Content-Type"] = "application/json";
  const response = await fetch(path, {
    method: method || (body !== undefined ? "POST" : "GET"),
    headers,
    body:
      body === undefined
        ? undefined
        : body instanceof FormData
          ? body
          : JSON.stringify(body),
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || response.statusText);
  return result;
}
const run = (fn: () => any) => () =>
  Promise.resolve()
    .then(fn)
    .catch((e) => notice(t(e.message), true));
function download(name: string, data: any) {
  const blob = new Blob([json(data)], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}
const base = () => `/api/projects/${pid}`;
function options(values: string[], selected = "") {
  return values
    .map(
      (v) =>
        `<option value="${esc(v)}" ${v === selected ? "selected" : ""}>${esc(v)}</option>`,
    )
    .join("");
}
function syncLanguage() {
  setLanguage(lang);
  $<HTMLSelectElement>("language").value = lang;
}
function tab(name: string) {
  activeTab = name;
  document
    .querySelectorAll<HTMLElement>(".tab")
    .forEach((el) => (el.hidden = el.id !== name));
  document
    .querySelectorAll("[data-tab]")
    .forEach((el) =>
      el.classList.toggle("active", (el as HTMLElement).dataset.tab === name),
    );
  if (name === "explore" && version && !adapter.browser) run(mountChart)();
  else adapter.browser?.updateLayout();
}
async function loadProjects() {
  const list = await api("/api/projects");
  $("projects").innerHTML = list
    .map(
      (p: any) =>
        `<button data-project="${p.id}" class="${p.id === pid ? "active-project" : ""}">${esc(p.name)}<small> · ${esc(t(p.role[0].toUpperCase() + p.role.slice(1)))}</small></button>`,
    )
    .join("");
  document
    .querySelectorAll<HTMLElement>("[data-project]")
    .forEach(
      (el) => (el.onclick = run(() => openProject(el.dataset.project!))),
    );
  if (!pid && list.length) await openProject(list[0].id);
}
async function openProject(id: string, vid?: string) {
  chartGeneration++;
  adapter.destroy();
  adapter = new KeshifAdapter();
  pid = id;
  meta = await api(base());
  project = meta.project;
  objects = meta.objects;
  $("project-title").textContent = project.name;
  $("role").textContent = t(
    project.role[0].toUpperCase() + project.role.slice(1),
  );
  $("versions").innerHTML = meta.versions
    .map(
      (v: any, i: number) =>
        `<option value="${v.id}">${i === 0 ? "Latest · " : ""}${esc(v.created)} · ${v.id.slice(0, 8)}</option>`,
    )
    .join("");
  const current = vid || project.active;
  if (current) {
    version = await api(base() + `/versions/${current}`);
    $<HTMLSelectElement>("versions").value = current;
    rows = version.rows;
    fields = structuredClone(
      objects
        .filter(
          (o: any) => o.kind === "dictionary" && o.payload.version === current,
        )
        .at(-1)?.payload.fields || version.fields,
    );
    dashboard = objects
      .filter(
        (o: any) => o.kind === "dashboard" && o.payload.version === current,
      )
      .at(-1)?.payload || {
      name: "Overview",
      view: "list",
      facets: fields
        .filter((f) => f.type !== "object")
        .slice(0, 4)
        .map((f) => f.id),
    };
    selected = new Set(rows.map((r) => r.__id));
    $("recipe").textContent = "";
    $<HTMLTextAreaElement>("recipe").value = "[]";
  } else {
    version = null;
    rows = [];
    fields = [];
    dashboard = {};
    selected.clear();
  }
  review = null;
  $("publication-review").hidden = true;
  page = 0;
  $("constraint").textContent = "";
  renderFields();
  renderDashboard();
  renderTable();
  renderSaved();
  renderPublic();
  renderDiff();
  await jobs();
  await members();
  const disabled = project.role === "viewer";
  document
    .querySelectorAll<HTMLButtonElement>(
      "#upload button,#api-form button,#prepare button,#save-fields,#save-dashboard,#cohort,#question,#activate-version",
    )
    .forEach((el) => (el.disabled = disabled));
  $("member-form").hidden = project.role !== "owner";
  $("review").hidden = project.role !== "owner";
  document
    .querySelectorAll<HTMLElement>("[data-project]")
    .forEach((el) =>
      el.classList.toggle("active-project", el.dataset.project === pid),
    );
  tab(activeTab);
  syncLanguage();
}
function renderFields() {
  $("field-table").innerHTML =
    `<thead><tr>${["Field", "Label", "Type", "Role", "Panel", "Delimiter", "Collapse", "Missing", "Distinct"].map((k) => `<th>${t(k)}</th>`).join("")}</tr></thead><tbody>` +
    fields
      .map(
        (f, i) =>
          `<tr data-field="${i}"><td>${esc(f.id)} <button data-move="${i}:-1" aria-label="Move up">↑</button><button data-move="${i}:1" aria-label="Move down">↓</button></td><td><input aria-label="Label ${esc(f.id)}" data-key="label" value="${esc(f.label)}"></td><td><select data-key="type">${options(["string", "number", "boolean", "date", "multivalue", "object"], f.type)}</select></td><td><select data-key="role">${options(["", "id", "title", "description", "date", "category", "measure", "latitude", "longitude", "link", "image", "x", "y"], f.role)}</select></td><td><select data-key="panel">${options(["left", "right", "middle", "bottom", "none"], f.panel || "left")}</select></td><td><input data-key="delimiter" value="${esc(f.delimiter || "")}" size="2"></td><td><input type="checkbox" data-key="collapsed" ${f.collapsed ? "checked" : ""} aria-label="Collapse ${esc(f.id)}"></td><td>${version?.fields.find((x: Field) => x.id === f.id)?.missing ?? 0}</td><td>${version?.fields.find((x: Field) => x.id === f.id)?.unique ?? 0}</td></tr>`,
      )
      .join("") +
    "</tbody>";
  document
    .querySelectorAll<
      HTMLInputElement | HTMLSelectElement
    >("#field-table [data-key]")
    .forEach(
      (el) =>
        (el.onchange = () => {
          const i = Number(el.closest<HTMLElement>("tr")!.dataset.field);
          (fields[i] as any)[el.dataset.key!] =
            el instanceof HTMLInputElement && el.type === "checkbox"
              ? el.checked
              : el.value;
        }),
    );
  document.querySelectorAll<HTMLElement>("[data-move]").forEach(
    (el) =>
      (el.onclick = () => {
        const [i, delta] = el.dataset.move!.split(":").map(Number),
          j = i + delta;
        if (j >= 0 && j < fields.length) {
          [fields[i], fields[j]] = [fields[j], fields[i]];
          renderFields();
        }
      }),
  );
}
function readDashboard(): Dashboard {
  const result: Record<string, any> = { ...dashboard };
  document
    .querySelectorAll<HTMLInputElement | HTMLSelectElement>("[data-config]")
    .forEach((el) => (result[el.dataset.config!] = el.value));
  result.facets = Array.from(
    document.querySelectorAll<HTMLInputElement>("[data-facet]:checked"),
  ).map((el) => el.value);
  result.card = Array.from(
    document.querySelectorAll<HTMLInputElement>("[data-card]:checked"),
  ).map((el) => el.value);
  return result;
}
function renderDashboard() {
  const ids = fields.map((f) => f.id);
  const fieldSelect = (key: string, label: string) =>
    `<label>${t(label)}<select data-config="${key}">${options(["", ...ids], (dashboard as any)[key] || "")}</select></label>`;
  $("dashboard-controls").innerHTML =
    `<div class="dashboard-form"><label>${t("Name")}<input data-config="name" value="${esc(dashboard.name || "Overview")}"></label><label>View<select data-config="view">${options(["list", "scatter", "map"], dashboard.view || "list")}</select></label>${fieldSelect("title", "Title")}${fieldSelect("x", "X")}${fieldSelect("y", "Y")}${fieldSelect("latitude", "Latitude")}${fieldSelect("longitude", "Longitude")}${fieldSelect("color", "Color")}${fieldSelect("size", "Size")}</div><details><summary>Facets / variables</summary>${fields.map((f) => `<label><input type="checkbox" data-facet value="${esc(f.id)}" ${(dashboard.facets || ids.slice(0, 4)).includes(f.id) ? "checked" : ""}>${esc(f.label)}</label>`).join("")}</details><details><summary>Record card / Fiche</summary>${fields.map((f) => `<label><input type="checkbox" data-card value="${esc(f.id)}" ${(dashboard.card || [dashboard.title || fields[0]?.id]).includes(f.id) ? "checked" : ""}>${esc(f.label)}</label>`).join("")}</details>`;
  $("table-field").innerHTML =
    `<option value="">${t("All fields")}</option>` +
    ids
      .map(
        (id) =>
          `<option value="${esc(id)}">${esc(fields.find((f) => f.id === id)?.label)}</option>`,
      )
      .join("");
}
async function mountChart() {
  if (!version) return;
  const generation = ++chartGeneration;
  const keep = Array.from(selected);
  dashboard = readDashboard();
  if (keep.length !== rows.length)
    $("constraint").textContent =
      t("Selection constraint") + " · " + keep.length;
  adapter.destroy();
  adapter = new KeshifAdapter();
  const currentAdapter = adapter;
  notice("");
  await currentAdapter.mount(
    $("chart"),
    rows,
    fields,
    dashboard,
    (ids) => {
      if (generation !== chartGeneration) return;
      selected = new Set(ids);
      page = 0;
      renderTable();
    },
    keep,
  );
  if (generation !== chartGeneration) {
    currentAdapter.destroy();
    return;
  }
  renderCoverage();
}
function tableRows() {
  const q = val("search").toLocaleLowerCase(),
    field = val("table-field"),
    exact = val("table-value");
  let result = rows.filter(
    (r) =>
      selected.has(r.__id) &&
      (!q ||
        fields.some((f) =>
          String(r[f.id] ?? "")
            .toLocaleLowerCase()
            .includes(q),
        )) &&
      (!field ||
        exact === "" ||
        (Array.isArray(r[field])
          ? r[field].some((x: any) => String(x) === exact)
          : String(r[field]) === exact)),
  );
  if (sort)
    result = result.slice().sort((a, b) => {
      const x = a[sort],
        y = b[sort];
      const n =
        typeof x === "number" && typeof y === "number"
          ? x - y
          : String(x ?? "").localeCompare(String(y ?? ""));
      return reverse ? -n : n;
    });
  return result;
}
function renderTable() {
  const result = tableRows(),
    last = Math.max(0, Math.ceil(result.length / 50) - 1);
  page = Math.min(page, last);
  $("selection-count").textContent =
    `${t("Selected")}: ${result.length} / ${rows.length}`;
  $("records").innerHTML =
    `<thead><tr><th></th>${fields.map((f) => `<th><button data-sort="${esc(f.id)}">${esc(f.label)}</button></th>`).join("")}</tr></thead><tbody>` +
    result
      .slice(page * 50, page * 50 + 50)
      .map(
        (r) =>
          `<tr><td><button data-inspect="${esc(r.__id)}" aria-label="${t("Inspect record")}">↗</button></td>${fields.map((f) => `<td>${esc(typeof r[f.id] === "object" ? JSON.stringify(r[f.id]) : r[f.id])}</td>`).join("")}</tr>`,
      )
      .join("") +
    "</tbody>";
  if (!result.length) $("records").insertAdjacentHTML("afterend", "");
  document.querySelectorAll<HTMLElement>("[data-sort]").forEach(
    (el) =>
      (el.onclick = () => {
        if (sort === el.dataset.sort) reverse = !reverse;
        else {
          sort = el.dataset.sort!;
          reverse = false;
        }
        renderTable();
      }),
  );
  document.querySelectorAll<HTMLElement>("[data-inspect]").forEach(
    (el) =>
      (el.onclick = () => {
        $("inspector").querySelector("pre")!.textContent = json(
          rows.find((r) => r.__id === el.dataset.inspect),
        );
        $<HTMLDialogElement>("inspector").showModal();
      }),
  );
  $("pagination").innerHTML =
    `<button id="prev-page" ${page === 0 ? "disabled" : ""}>←</button> ${page + 1} / ${last + 1} · ${result.length ? `${page * 50 + 1}–${Math.min(result.length, page * 50 + 50)}` : t("No records match.")} <button id="next-page" ${page === last ? "disabled" : ""}>→</button>`;
  $("prev-page").onclick = () => {
    page--;
    renderTable();
  };
  $("next-page").onclick = () => {
    page++;
    renderTable();
  };
  renderCoverage();
}
function renderCoverage() {
  if (!version) {
    $("coverage").textContent = t("No dataset yet");
    return;
  }
  let eligible = 0;
  const overlap = new Map<string, number>();
  for (const r of rows) {
    let pair: any[] = [];
    if (dashboard.view === "map")
      pair = [r[dashboard.latitude || ""], r[dashboard.longitude || ""]];
    else if (dashboard.view === "scatter")
      pair = [r[dashboard.x || ""], r[dashboard.y || ""]];
    else {
      eligible++;
      continue;
    }
    const valid =
      pair.every(
        (v) =>
          v !== null &&
          v !== undefined &&
          v !== "" &&
          Number.isFinite(Number(v)),
      ) &&
      (dashboard.view !== "map" ||
        (Math.abs(Number(pair[0])) <= 90 && Math.abs(Number(pair[1])) <= 180));
    if (valid) {
      eligible++;
      const key = pair.join("|");
      overlap.set(key, (overlap.get(key) || 0) + 1);
    }
  }
  const quality: Record<string, string[]> = {};
  for (const f of fields) {
    const missing = rows
      .filter(
        (r) => r[f.id] === null || r[f.id] === undefined || r[f.id] === "",
      )
      .map((r) => r.__id);
    if (missing.length) quality[f.id + " · " + t("Missing")] = missing;
    const numeric = rows
      .map((r) => r[f.id])
      .filter((v) => typeof v === "number" && Number.isFinite(v))
      .sort((a, b) => a - b);
    if (numeric.length >= 4) {
      const q1 = numeric[Math.floor(numeric.length * 0.25)],
        q3 = numeric[Math.floor(numeric.length * 0.75)],
        iqr = q3 - q1;
      const outliers = rows
        .filter(
          (r) =>
            typeof r[f.id] === "number" &&
            (r[f.id] < q1 - 1.5 * iqr || r[f.id] > q3 + 1.5 * iqr),
        )
        .map((r) => r.__id);
      if (outliers.length) quality[f.id + " · IQR"] = outliers;
    }
  }
  $("quality").innerHTML = Object.entries(quality)
    .map(
      ([name, ids], i) =>
        `<button data-quality="${i}">${esc(name)} · ${ids.length}</button>`,
    )
    .join("");
  document.querySelectorAll<HTMLElement>("[data-quality]").forEach(
    (el) =>
      (el.onclick = () => {
        const [name, ids] = Object.entries(quality)[Number(el.dataset.quality)];
        adapter.clear();
        selected = new Set(ids);
        adapter.setIDs(ids);
        $("constraint").textContent = t("Selection constraint") + ": " + name;
        page = 0;
        renderTable();
      }),
  );
  const overlapCount = Array.from(overlap.values())
    .filter((n) => n > 1)
    .reduce((a, b) => a + b, 0);
  $("coverage").textContent =
    `${t("Coverage")} · ${t("Total")} ${rows.length} · ${t("Eligible")} ${eligible} · ${t("Excluded")} ${rows.length - eligible} · ${t("Overlaps")} ${overlapCount}`;
}
async function saveObject(kind: string, payload: any) {
  const result = await api(base() + "/objects", { kind, payload });
  meta = await api(base());
  objects = meta.objects;
  renderSaved();
  notice(t("Saved"));
  return result;
}
function renderSaved() {
  const same = objects.filter((o) => o.payload.version === version?.id);
  $("saved-states").innerHTML = same
    .filter((o) => ["cohort", "snapshot", "dashboard"].includes(o.kind))
    .map(
      (o) =>
        `<button data-state="${o.id}">${esc(o.payload.name || o.kind)} · ${o.kind}</button>`,
    )
    .join("");
  document.querySelectorAll<HTMLElement>("[data-state]").forEach(
    (el) =>
      (el.onclick = run(async () => {
        const o = objects.find((o) => o.id === el.dataset.state);
        if (o.kind === "dashboard") {
          dashboard = o.payload;
          renderDashboard();
          await mountChart();
        } else {
          if (o.payload.dashboard) {
            dashboard = o.payload.dashboard;
            renderDashboard();
          }
          if (o.payload.table) {
            $<HTMLInputElement>("search").value = o.payload.table.search || "";
            $<HTMLSelectElement>("table-field").value =
              o.payload.table.field || "";
            $<HTMLInputElement>("table-value").value =
              o.payload.table.value || "";
          }
          selected = new Set(o.payload.ids);
          $("constraint").textContent =
            t("Selection constraint") + ": " + o.payload.name;
          await mountChart();
          renderTable();
        }
      })),
  );
  $("recipes").innerHTML = objects
    .filter((o) => o.kind === "recipe")
    .map(
      (o) =>
        `<button data-recipe="${o.id}">${esc(o.payload.name || "Recipe")}</button>`,
    )
    .join("");
  document.querySelectorAll<HTMLElement>("[data-recipe]").forEach(
    (el) =>
      (el.onclick = () => {
        $<HTMLTextAreaElement>("recipe").value = json(
          objects.find((o) => o.id === el.dataset.recipe).payload.steps,
        );
      }),
  );
}
function renderPublic() {
  $("public-fields").innerHTML = fields
    .map(
      (f) =>
        `<label><input type="checkbox" value="${esc(f.id)}" data-public-field> ${esc(f.label)}</label>`,
    )
    .join("");
  $<HTMLInputElement>("release-title").value = project?.name || "";
  $("releases").innerHTML = (meta?.releases || [])
    .map(
      (r: any) =>
        `<p><a href="/public/${r.id}" target="_blank" rel="noopener">${esc(r.id.slice(0, 12))}</a> · ${esc(r.created)} ${r.revoked ? "revoked" : `<button data-revoke="${r.id}">${t("Revoke")}</button>`}</p>`,
    )
    .join("");
  document.querySelectorAll<HTMLElement>("[data-revoke]").forEach(
    (el) =>
      (el.onclick = run(async () => {
        await api(base() + `/releases/${el.dataset.revoke}/revoke`, {});
        await openProject(pid, version?.id);
      })),
  );
}
function publicRequest() {
  const allowed = Array.from(
    document.querySelectorAll<HTMLInputElement>("[data-public-field]:checked"),
  ).map((el) => el.value);
  const d: Dashboard = {
    name: dashboard.name,
    view: dashboard.view || "list",
    facets: (dashboard.facets || allowed).filter((k) => allowed.includes(k)),
    card: (dashboard.card || []).filter((k) => allowed.includes(k)),
  };
  for (const k of [
    "title",
    "x",
    "y",
    "latitude",
    "longitude",
    "color",
    "size",
  ] as const)
    if (dashboard[k] && allowed.includes(dashboard[k]!)) d[k] = dashboard[k];
  if (
    (d.view === "scatter" && (!d.x || !d.y)) ||
    (d.view === "map" && (!d.latitude || !d.longitude))
  )
    d.view = "list";
  return {
    version: version?.id,
    title: val("release-title"),
    fields: allowed,
    dashboard: d,
  };
}
async function members() {
  if (!pid) return;
  const m = await api(base() + "/members");
  $("members").textContent = m
    .map(
      (x: any) =>
        `${x.username} · ${t(x.role[0].toUpperCase() + x.role.slice(1))}`,
    )
    .join(" / ");
}
async function jobs() {
  if (!pid) return;
  const list = await api(base() + "/jobs");
  $("jobs").innerHTML = list
    .map(
      (j: any) =>
        `<p>${esc(j.id.slice(0, 8))} · ${esc(j.state)} · ${esc(j.checkpoint ? json(j.checkpoint) : "")} ${esc(j.result || "")} ${["queued", "running"].includes(j.state) ? `<button data-job="${j.id}" data-action="cancel">${t("Cancel")}</button>` : ["failed", "cancelled"].includes(j.state) ? `<button data-job="${j.id}" data-action="retry">${t("Retry")}</button>` : ""}</p>`,
    )
    .join("");
  document.querySelectorAll<HTMLElement>("[data-job]").forEach(
    (el) =>
      (el.onclick = run(async () => {
        await api(base() + `/jobs/${el.dataset.job}/${el.dataset.action}`, {});
        await jobs();
      })),
  );
}
function renderDiff() {
  $("diff-controls").innerHTML =
    `<select id="diff-a">${meta.versions.map((v: any) => `<option>${v.id}</option>`).join("")}</select><select id="diff-b">${meta.versions.map((v: any) => `<option>${v.id}</option>`).join("")}</select><button id="diff-run">${t("Compare versions")}</button>`;
  $("diff-run").onclick = run(async () => {
    $("diff").textContent = json(
      await api(base() + `/diff?a=${val("diff-a")}&b=${val("diff-b")}`),
    );
  });
}
function renderPublicTable(ids: string[]) {
  const wanted = new Set(ids);
  $("public-count").textContent =
    `${t("Selected")}: ${ids.length} / ${publicPayload.rows.length}` +
    (ids.length > 100
      ? ` · ${t("Showing first 100; export includes all selected records.")}`
      : "");
  $("public-table").innerHTML =
    "<thead><tr>" +
    publicPayload.fields
      .map((f: Field) => `<th>${esc(f.label)}</th>`)
      .join("") +
    "</tr></thead><tbody>" +
    publicPayload.rows
      .filter((r: Row) => wanted.has(r.__id))
      .slice(0, 100)
      .map(
        (r: Row) =>
          "<tr>" +
          publicPayload.fields
            .map(
              (f: Field) =>
                `<td>${esc(typeof r[f.id] === "object" ? json(r[f.id]) : r[f.id])}</td>`,
            )
            .join("") +
          "</tr>",
      )
      .join("") +
    "</tbody>";
}
async function mountPublic() {
  $("public-chart").dataset.studioReady = "false";
  const keep = publicSelected;
  adapter.destroy();
  adapter = new KeshifAdapter();
  await adapter.mount(
    $("public-chart"),
    publicPayload.rows,
    publicPayload.fields,
    publicPayload.dashboard,
    (ids: string[]) => {
      publicSelected = ids;
      renderPublicTable(ids);
    },
    keep,
  );
  $("public-chart").dataset.studioReady = "true";
}
async function boot() {
  syncLanguage();
  const rid = document.body.dataset.public;
  if (rid) {
    publicPayload = await api(`/public/${rid}/data`);
    $("public-reader").hidden = false;
    $("public-title").textContent = publicPayload.title;
    $("public-date").textContent =
      t("Publication date") + ": " + publicPayload.data_date;
    $("public-download").onclick = () => {
      const ids = new Set(
        publicSelected ?? publicPayload.rows.map((row: Row) => row.__id),
      );
      download(
        "public-data.json",
        publicPayload.rows.filter((r: Row) => ids.has(r.__id)),
      );
    };
    await mountPublic();
    return;
  }
  const s = await api("/api/session");
  csrf = s.csrf;
  user = s.user;
  $("login").hidden = !!user;
  $("private").hidden = !user;
  $("logout").hidden = !user;
  $("account").textContent = user?.username || "";
  if (user) await loadProjects();
}
$("language").onchange = run(async () => {
  if (version && adapter.browser) dashboard = readDashboard();
  setLanguage(val("language") as Lang);
  syncLanguage();
  if (publicPayload) {
    await mountPublic();
  } else if (version) {
    renderFields();
    renderTable();
    $("role").textContent = t(
      project.role[0].toUpperCase() + project.role.slice(1),
    );
    if (activeTab === "explore") await mountChart();
  }
});
$("login-form").onsubmit = (e) => {
  e.preventDefault();
  run(async () => {
    const f = new FormData(e.target as HTMLFormElement);
    const s = await api("/api/login", Object.fromEntries(f));
    csrf = s.csrf;
    await boot();
  })();
};
$("logout").onclick = run(async () => {
  await api("/api/logout", {});
  location.reload();
});
$("project-form").onsubmit = (e) => {
  e.preventDefault();
  run(async () => {
    const r = await api("/api/projects", { name: val("project-name") });
    await loadProjects();
    await openProject(r.id);
  })();
};
document
  .querySelectorAll<HTMLElement>("[data-tab]")
  .forEach((el) => (el.onclick = () => tab(el.dataset.tab!)));
$("activate-version").onclick = run(async () => {
  await api(base() + "/activate", { version: version.id });
  await openProject(pid, version.id);
  notice(t("Saved"));
});
$("versions").onchange = run(() => openProject(pid, val("versions")));
$("upload").onsubmit = (e) => {
  e.preventDefault();
  run(async () => {
    if (!pid) throw new Error("Create a project first");
    const f = new FormData(e.target as HTMLFormElement),
      opts: any = {};
    for (const k of ["identity", "records_path", "delimiter", "sheet"]) {
      const v = String(f.get(k) || "");
      if (v) opts[k] = k === "sheet" && /^\d+$/.test(v) ? Number(v) : v;
    }
    f.set("options", JSON.stringify(opts));
    const r = await api(base() + "/imports", f);
    await openProject(pid, r.id);
    tab("fields");
    notice(t("Saved"));
  })();
};
$("demo").onclick = run(async () => {
  if (!pid) throw new Error("Create a project first");
  const response = await fetch("/static/demo.csv");
  const blob = await response.blob();
  const form = new FormData();
  form.set("file", blob, "demo.csv");
  form.set("options", JSON.stringify({ identity: "id" }));
  const r = await api(base() + "/imports", form);
  await openProject(pid, r.id);
  tab("fields");
});
$("api-form").onsubmit = (e) => {
  e.preventDefault();
  run(async () => {
    await api(
      base() + "/jobs",
      Object.fromEntries(new FormData(e.target as HTMLFormElement)),
    );
    await jobs();
  })();
};
$("refresh-jobs").onclick = run(async () => {
  await openProject(pid, version?.id);
});
for (const [id, preview] of [
  ["preview-recipe", true],
  ["apply-recipe", false],
] as const)
  $(`${id}`).onclick = run(async () => {
    if (!version) throw new Error(t("No dataset yet"));
    const steps = JSON.parse(val("recipe"));
    const r = await api(base() + "/prepare", {
      version: version.id,
      steps,
      preview,
    });
    $("recipe-preview").textContent = json(r);
    if (!preview) await openProject(pid, r.id);
  });
$("undo").onclick = run(async () => {
  if (!version?.parent) throw new Error("No parent version");
  await api(base() + "/activate", { version: version.parent });
  await openProject(pid, version.parent);
});
$("save-recipe").onclick = run(() =>
  saveObject("recipe", {
    version: version.id,
    name: prompt(t("Name")) || "Recipe",
    steps: JSON.parse(val("recipe")),
  }),
);
$("save-fields").onclick = run(async () => {
  const labels = fields.map((f) => f.label);
  if (new Set(labels).size !== labels.length)
    throw new Error("Field labels must be unique");
  await saveObject("dictionary", { version: version.id, fields });
  notice(t("Saved"));
});
$("mount-chart").onclick = run(mountChart);
$("save-dashboard").onclick = run(async () => {
  dashboard = readDashboard();
  await saveObject("dashboard", { ...dashboard, version: version.id });
});
$("clear").onclick = () => {
  selected = new Set(rows.map((r) => r.__id));
  adapter.clear();
  $<HTMLInputElement>("search").value = "";
  $<HTMLInputElement>("table-value").value = "";
  $("constraint").textContent = "";
  renderTable();
};
for (const id of ["search", "table-field", "table-value"])
  $(id).addEventListener("input", () => {
    page = 0;
    renderTable();
  });
for (const [id, kind] of [
  ["cohort", "cohort"],
  ["question", "snapshot"],
])
  $(id).onclick = run(async () => {
    const name = prompt(t("Name"));
    if (!name) return;
    await saveObject(kind, {
      version: version.id,
      name,
      note: kind === "snapshot" ? prompt(t("Note")) || "" : "",
      ids: tableRows().map((r) => r.__id),
      dashboard: readDashboard(),
      table: {
        search: val("search"),
        field: val("table-field"),
        value: val("table-value"),
      },
    });
  });
$("export-selection").onclick = run(async () =>
  download(
    "selection.json",
    await api(base() + "/selection-export", {
      version: version.id,
      ids: tableRows().map((r) => r.__id),
    }),
  ),
);
$("export-project").onclick = run(async () =>
  download("project.json", await api(base() + "/export")),
);
$("import-project").onchange = run(async () => {
  const f = $<HTMLInputElement>("import-project").files?.[0];
  if (f) {
    const r = await api("/api/project-import", JSON.parse(await f.text()));
    await loadProjects();
    await openProject(r.id);
  }
});
$("review").onclick = run(async () => {
  const b = publicRequest();
  review = { request: b, ...(await api(base() + "/publication-preview", b)) };
  $("public-preview").textContent = json(review.preview);
  $("publication-review").hidden = false;
});
$("confirm-release").onclick = run(async () => {
  if (!review) throw new Error("Review required");
  if (JSON.stringify(review.request) !== JSON.stringify(publicRequest()))
    throw new Error("Review is stale");
  const r = await api(base() + "/releases", {
    ...review.request,
    digest: review.digest,
  });
  await openProject(pid, version.id);
  notice(t("Saved") + " · " + r.url);
});
$("member-form").onsubmit = (e) => {
  e.preventDefault();
  run(async () => {
    await api(
      base() + "/members",
      Object.fromEntries(new FormData(e.target as HTMLFormElement)),
    );
    await members();
  })();
};
$("close-inspector").onclick = () => $<HTMLDialogElement>("inspector").close();
run(boot)();
