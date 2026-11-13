import { build } from "esbuild";
import { execFileSync } from "node:child_process";
execFileSync("python3", ["scripts/verify-vendor.py"], { stdio: "inherit" });
import { mkdir, writeFile, readFile, cp, rm, readdir } from "node:fs/promises";
import { createHash } from "node:crypto";
await rm("static/dist", { recursive: true, force: true });
await mkdir("static/dist", { recursive: true });
await build({
  entryPoints: ["frontend/app.ts"],
  outfile: "static/dist/app.js",
  bundle: true,
  external: ["/static/dist/keshif.js"],
  format: "esm",
  target: "es2022",
  sourcemap: true,
  minify: true,
});
await build({
  entryPoints: ["vendor/keshif/keshif.js"],
  outfile: "static/dist/keshif.js",
  bundle: false,
  format: "esm",
  target: "es2022",
  sourcemap: true,
  minify: true,
});
for (const name of [
  "vendor.js",
  "vendor_mapping.js",
  "vendor.js.map",
  "vendor_mapping.js.map",
])
  await cp("vendor/keshif/" + name, "static/dist/" + name);
await cp("vendor/keshif/assets", "static/dist/assets", { recursive: true });
let css = await readFile("vendor/keshif/keshif.css", "utf8");
// Replace the inherited Font Awesome Pro faces with the licensed Free build.
css = css.replace(/@font-face\s*\{[^}]*font-family:[^}]*\}/g, "");
await writeFile("static/dist/keshif.css", css);
await cp(
  "node_modules/@fortawesome/fontawesome-free/css/all.min.css",
  "static/dist/icons.css",
);
await cp(
  "node_modules/@fortawesome/fontawesome-free/webfonts",
  "static/webfonts",
  { recursive: true },
);
await cp(
  "node_modules/@fortawesome/fontawesome-free/LICENSE.txt",
  "vendor/FONT-AWESOME-LICENSE.txt",
);
const manifest = { schema: 1, files: {} };
async function inventory(dir) {
  for (const entry of await readdir(dir, { withFileTypes: true })) {
    const path = dir + "/" + entry.name;
    if (entry.isDirectory()) await inventory(path);
    else if (entry.name !== "manifest.json")
      manifest.files[path.replace(/^static\//, "")] = createHash("sha256")
        .update(await readFile(path))
        .digest("hex");
  }
}
await inventory("static/dist");
await inventory("static/webfonts");
for (const f of ["studio.css", "demo.csv"])
  manifest.files[f] = createHash("sha256")
    .update(await readFile("static/" + f))
    .digest("hex");
await writeFile(
  "static/dist/manifest.json",
  JSON.stringify(manifest, null, 2) + "\n",
);
