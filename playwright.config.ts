import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "tests/browser",
  workers: 1,
  use: {
    baseURL: "http://127.0.0.1:5101",
    launchOptions: {
      executablePath: process.env.CHROMIUM_PATH || "/usr/bin/chromium",
      args: ["--no-sandbox", "--disable-dev-shm-usage"],
    },
    headless: true,
  },
  webServer: {
    command: ".venv/bin/python -m scripts.browser-server",
    url: "http://127.0.0.1:5101/health",
    reuseExistingServer: false,
    stdout: "ignore",
    stderr: "ignore",
  },
  reporter: "list",
  timeout: 60000,
});
