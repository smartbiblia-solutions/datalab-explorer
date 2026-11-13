import { readFileSync } from "node:fs";
import { test, expect } from "@playwright/test";
test("import, prepare, native facets, exact empty cohort, bilingual publication and revoke", async ({
  page,
  context,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.stack || e.message));
  await page.goto("/");
  await page.locator("[name=username]").first().fill("browser-test");
  await page.locator("[name=password]").fill("browser-test-password");
  await page.locator("#login-form button").click();
  await expect(page.locator("#private")).toBeVisible();
  await page.locator("#project-name").fill("Browser " + Date.now());
  await page.locator("#project-form button").click();
  await expect(page.locator("#project-title")).toContainText("Browser");
  await page.locator("#demo").click();
  await expect(page.locator("#field-table tbody tr")).toHaveCount(10);
  await page.locator("[data-tab=prepare]").click();
  await page.locator("#recipe").fill(
    JSON.stringify(
      ["year", "amount", "latitude", "longitude"].map((field) => ({
        op: "number",
        field,
      })),
    ),
  );
  await page.locator("#apply-recipe").click();
  await expect(page.locator("#versions option")).toHaveCount(2);
  await page.locator("[data-tab=explore]").click();
  await expect(page.locator("#chart")).toHaveClass(/kshf/, { timeout: 25000 });
  await expect(page.locator("#chart .overlay_wrapper")).toHaveAttribute(
    "show",
    "none",
    { timeout: 25000 },
  );
  await expect(page.locator("#selection-count")).toContainText("5 / 5");
  await page.locator("#search").fill("does-not-exist");
  await expect(page.locator("#selection-count")).toContainText("0 / 5");
  page.once("dialog", (d) => d.accept("Empty cohort"));
  await page.locator("#cohort").click();
  await expect(
    page.locator("[data-state]").filter({ hasText: "Empty cohort" }),
  ).toBeVisible();
  await page.locator("#clear").click();
  await expect(page.locator("#selection-count")).toContainText("5 / 5");
  await page
    .locator("[data-state]")
    .filter({ hasText: "Empty cohort" })
    .click();
  await expect(page.locator("#selection-count")).toContainText("0 / 5");
  await page.locator("#language").selectOption("fr");
  await expect(page.locator("[data-tab=explore]")).toHaveText("Explorer");
  await expect(page.locator("#selection-count")).toContainText("0 / 5");
  await page.locator("#clear").click();
  await expect(page.locator("#selection-count")).toContainText("5 / 5");
  // Native facet interaction must update the linked record table.
  const category = page
    .locator("#chart .aggrGlyph")
    .filter({ hasText: "Environment" })
    .first();
  await expect(category).toBeVisible();
  await category.click();
  await expect(page.locator("#selection-count")).toContainText("2 / 5");
  await page.locator("#clear").click();
  await page.screenshot({
    path: "test-results/explore-fr.png",
    fullPage: true,
  });
  await page.locator("[data-tab=publish]").click();
  await page.locator("[data-public-field][value=title]").check();
  await page.locator("[data-public-field][value=category]").check();
  await page.locator("#review").click();
  await expect(page.locator("#public-preview")).toBeVisible();
  await expect(page.locator("#public-preview")).not.toContainText(
    "private_note",
  );
  await page.locator("#confirm-release").click();
  await expect(page.locator("#releases a")).toHaveCount(1);
  const href = await page.locator("#releases a").getAttribute("href");
  const anon = await context.browser()!.newContext();
  const reader = await anon.newPage();
  reader.on("pageerror", (e) => errors.push(e.stack || e.message));
  await reader.goto(href!);
  await expect(reader.locator("#public-title")).toContainText("Browser");
  await expect(reader.locator("#public-chart")).toHaveAttribute(
    "data-studio-ready",
    "true",
    { timeout: 25000 },
  );
  await expect(reader.locator("#public-chart .overlay_wrapper")).toBeHidden();
  await expect(reader.locator("#public-table tbody tr")).toHaveCount(5);
  await expect(reader.locator("#public-chart")).toHaveAttribute(
    "recordcharttype",
    "list",
  );
  await expect(
    reader.locator("#public-chart .kshfRecord").first(),
  ).toBeVisible();
  const data = await reader.request.get(href + "/data");
  expect(JSON.stringify(await data.json())).not.toContain("private_note");
  await reader.locator("#language").selectOption("fr");
  await expect(reader.locator("#public-reader")).toContainText(
    "Lecteur public",
  );
  await reader
    .locator("#public-chart .aggrGlyph")
    .filter({ hasText: "Environment" })
    .first()
    .click();
  await expect(reader.locator("#public-table tbody tr")).toHaveCount(2);
  await reader.locator("#language").selectOption("en");
  await expect(reader.locator("#public-chart")).toHaveAttribute(
    "data-studio-ready",
    "true",
  );
  await expect(reader.locator("#public-table tbody tr")).toHaveCount(2);
  await expect(
    reader.locator("#public-chart .overlay_wrapper"),
  ).toHaveAttribute("show", "none");
  const [exported] = await Promise.all([
    reader.waitForEvent("download"),
    reader.locator("#public-download").click(),
  ]);
  expect(
    JSON.parse(readFileSync((await exported.path())!, "utf8")),
  ).toHaveLength(2);
  await reader.screenshot({
    path: "test-results/public-reader.png",
    fullPage: true,
  });
  await page.locator("[data-revoke]").click();
  await expect
    .poll(async () => (await reader.request.get(href + "/data")).status())
    .toBe(404);
  await anon.close();
  expect(errors).toEqual([]);
  await page.screenshot({ path: "test-results/studio-fr.png", fullPage: true });
});

test("Keshif regression contracts: zero, false, missing geometry and complete large clusters", async ({
  page,
}) => {
  await page.goto("/");
  const result = await page.evaluate(async () => {
    // @ts-ignore Browser runtime module
    const K = await import("/static/dist/keshif.js");
    const infer = (value: any) =>
      K.Browser.prototype.getAttribTypeFromFunc.call(
        { records: [{ data: { v: value } }] },
        function (this: any) {
          return this.v;
        },
      );
    const geo = Object.create(K.Attrib_RecordGeo.prototype);
    geo._pointClusterRadius = 30;
    geo.browser = {
      records: [null, ...Array.from({ length: 1201 }, (_, i) => ({ id: i }))],
    };
    geo.getRecordValue = (r: any) =>
      r ? { geoFeat: { type: "Point", coordinates: [0, 0] } } : null;
    await geo.prepPointCluster({ getMaxZoom: () => 18, getMinZoom: () => 0 });
    const clusters = geo.PointCluster.getClusters([-180, -90, 180, 90], 0);
    const cluster = clusters.find((c: any) => c.properties.cluster);
    const members = geo.PointCluster.getLeaves(cluster.id, Infinity).length;
    return { zero: infer(0), bool: infer(false), members };
  });
  expect(result).toEqual({
    zero: "numeric",
    bool: "categorical",
    members: 1201,
  });
});

test("native list / scatter / map lifecycle and narrow-screen table", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.stack || e.message));
  await page.goto("/");
  await page.locator("[name=username]").first().fill("browser-test");
  await page.locator("[name=password]").fill("browser-test-password");
  await page.locator("#login-form button").click();
  await expect(page.locator("#private")).toBeVisible();
  await page.locator("#project-name").fill("Lifecycle " + Date.now());
  await page.locator("#project-form button").click();
  await expect(page.locator("#project-title")).toContainText("Lifecycle");
  await page.locator("#demo").click();
  await expect(page.locator("#field-table tbody tr")).toHaveCount(10);
  await page.locator("[data-tab=prepare]").click();
  await page.locator("#recipe").fill(
    JSON.stringify(
      ["year", "amount", "latitude", "longitude"].map((field) => ({
        op: "number",
        field,
      })),
    ),
  );
  await page.locator("#apply-recipe").click();
  await expect(page.locator("#versions option")).toHaveCount(2);
  await page.locator("[data-tab=explore]").click();
  await expect(page.locator("#chart .overlay_wrapper")).toHaveAttribute(
    "show",
    "none",
    { timeout: 25000 },
  );
  await page.locator("[data-config=x]").selectOption("year");
  await page.locator("[data-config=y]").selectOption("amount");
  await page.locator("[data-config=latitude]").selectOption("latitude");
  await page.locator("[data-config=longitude]").selectOption("longitude");
  for (const view of ["scatter", "map", "list", "scatter", "map", "list"]) {
    await page.locator("[data-config=view]").selectOption(view);
    await page.locator("#mount-chart").click();
    await expect(page.locator("#chart")).toHaveAttribute(
      "recordcharttype",
      view,
      { timeout: 25000 },
    );
    await expect(page.locator("#selection-count")).toContainText("5 / 5");
    await page.locator("[data-tab=sources]").click();
    await page.setViewportSize({ width: 768, height: 900 });
    await page.locator("[data-tab=explore]").click();
    await page.setViewportSize({ width: 1280, height: 900 });
  }
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.locator("#records")).toBeVisible();
  await page.screenshot({
    path: "test-results/studio-mobile.png",
    fullPage: true,
  });
  expect(errors).toEqual([]);
});

test("a dataset without usable coordinates renders an empty map without losing records", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.stack || e.message));
  await page.goto("/");
  await page.locator("[name=username]").first().fill("browser-test");
  await page.locator("[name=password]").fill("browser-test-password");
  await page.locator("#login-form button").click();
  await expect(page.locator("#private")).toBeVisible();
  await page.locator("#project-name").fill("Empty geography " + Date.now());
  await page.locator("#project-form button").click();
  await expect(page.locator("#project-title")).toContainText("Empty geography");
  await page.locator("#upload input[type=file]").setInputFiles({
    name: "missing.json",
    mimeType: "application/json",
    buffer: Buffer.from(
      JSON.stringify(
        Array.from({ length: 5 }, (_, i) => ({
          id: String(i),
          title: "Record " + i,
          latitude: null,
          longitude: null,
        })),
      ),
    ),
  });
  await page.locator("#upload button").click();
  await expect(page.locator("#field-table tbody tr")).toHaveCount(4);
  await page.locator("[data-tab=explore]").click();
  await expect(page.locator("#chart .overlay_wrapper")).toHaveAttribute(
    "show",
    "none",
    { timeout: 25000 },
  );
  await page.locator("[data-config=latitude]").selectOption("latitude");
  await page.locator("[data-config=longitude]").selectOption("longitude");
  await page.locator("[data-config=view]").selectOption("map");
  await page.locator("#mount-chart").click();
  await expect(page.locator("#chart")).toHaveAttribute(
    "recordcharttype",
    "map",
  );
  await expect(page.locator("#coverage")).toContainText("Excluded 5");
  await expect(page.locator("#selection-count")).toContainText("5 / 5");
  expect(errors).toEqual([]);
});
