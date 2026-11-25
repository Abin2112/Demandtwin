import { defineConfig } from "@playwright/test";
import path from "node:path";

const root = path.resolve(__dirname, "..");
const backendPort = 8009;
const frontendPort = 3009;
const windows = process.platform === "win32";
const python = process.env.DEMANDTWIN_PYTHON || (windows ? ".venv\\Scripts\\python.exe" : ".venv/bin/python");
const database = path.join(root, `data/runtime/browser-test-${process.pid}.db`).replaceAll("\\", "/");

export default defineConfig({
  testDir: "./tests",
  timeout: 180000,
  expect: { timeout: 15000 },
  workers: 1,
  use: {
    baseURL: "http://127.0.0.1:" + frontendPort,
    headless: true,
    launchOptions: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE } : {},
  },
  webServer: [
    {
      command: `"${python}" -m alembic -c backend/alembic.ini upgrade head && "${python}" -m uvicorn app.main:app --host 127.0.0.1 --port ${backendPort}`,
      cwd: root,
      env: { PYTHONPATH: ["backend", "ml-engine"].join(path.delimiter), DATABASE_URL: "sqlite:///" + database,
        JWT_SECRET: "isolated-browser-test-secret-at-least-32-characters", ETHICS_PROTOCOL_ID: "", CELERY_BROKER_URL: "", SECURE_COOKIES: "0" },
      url: `http://127.0.0.1:${backendPort}/api/v1/health`,
      timeout: 120000,
    },
    {
      command: `npm run dev -- --hostname 127.0.0.1 --port ${frontendPort}`,
      cwd: __dirname,
      env: { API_ORIGIN: "http://127.0.0.1:" + backendPort, NEXT_TELEMETRY_DISABLED: "1" },
      url: "http://127.0.0.1:" + frontendPort,
      timeout: 90000,
    },
  ],
});
