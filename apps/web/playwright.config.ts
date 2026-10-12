import { defineConfig } from "@playwright/test";

const root = process.env.MEDAI_ROOT ?? "../..";
const fixture = process.env.MEDAI_FIXTURE ?? "/tmp/medai-fixture";
const empty = process.env.MEDAI_EMPTY ?? "/tmp/medai-empty";
const py = process.env.MEDAI_PYTHON ?? "uv run --quiet python -m uvicorn";

const api = (port: number, dir: string) => ({
  command: `${py} app.main:app --app-dir services/api --port ${port}`,
  cwd: root,
  url: `http://127.0.0.1:${port}/health`,
  env: { MEDAI_REPORTS_DIR: `${dir}/reports`, MEDAI_ARTIFACTS_DIR: `${dir}/artifacts`, MEDAI_GALLERY_DIR: `${dir}/gallery`, MEDAI_CORS_ORIGINS: "" },
  reuseExistingServer: !process.env.CI,
  timeout: 120_000,
});

const web = (port: number, apiPort: number) => ({
  command: `node .next/standalone/server.js`,
  cwd: ".",
  url: `http://127.0.0.1:${port}/limites`,
  env: { PORT: String(port), HOSTNAME: "127.0.0.1", API_URL: `http://127.0.0.1:${apiPort}` },
  reuseExistingServer: !process.env.CI,
  timeout: 120_000,
});

export default defineConfig({
  testDir: "e2e",
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  reporter: [["list"]],
  use: {
    browserName: "chromium",
    launchOptions: process.env.PLAYWRIGHT_CHROMIUM_PATH ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM_PATH } : {},
  },
  webServer: [api(8100, fixture), api(8101, empty), web(3100, 8100), web(3101, 8101)],
});
