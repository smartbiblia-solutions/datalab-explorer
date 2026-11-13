// Bundle the studio frontend. Keshif itself is a prebuilt static module in static/keshif.
import { build } from "esbuild";
await build({
  entryPoints: ["frontend/app.ts"],
  outfile: "static/dist/app.js",
  bundle: true,
  external: ["/static/keshif/keshif.min.js"],
  format: "esm",
  target: "es2022",
  sourcemap: true,
  minify: true,
});
