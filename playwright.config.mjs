import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./tests",
  timeout: 60000,
  workers: 1,
  use: {
    baseURL: "http://127.0.0.1:1420",
    viewport: { width: 1380, height: 900 },
    launchOptions: {
      executablePath:
        process.env.PETRUS_CHROME ||
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    },
  },
});
