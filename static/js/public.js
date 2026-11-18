// Public dashboard page: load the published copy, show it, export the current selection.
import { Dashboard, downloadCSV } from "./dashboard.js";

const T = window.DATALAB_T || {};
const root = document.getElementById("dashboard");
const dashboard = new Dashboard(root);
const { config, rows } = await (await fetch(root.dataset.source)).json();
const count = document.getElementById("selection-count");
const refresh = () => {
  count.textContent = T["js.selection"]
    .replace("{n}", dashboard.selectedRows().length.toLocaleString())
    .replace("{total}", rows.length.toLocaleString());
};
await dashboard.show(rows, config, { onSelectionChange: refresh });
refresh();

document.getElementById("export-csv").addEventListener("click", () => {
  downloadCSV(dashboard.selectedRows(), config, root.dataset.filename + ".csv");
});
