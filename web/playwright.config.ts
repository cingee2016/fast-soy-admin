import { defineConfig, devices } from '@playwright/test';

const BACKEND_PORT = Number(process.env.E2E_BACKEND_PORT ?? 9999);
const FRONTEND_PORT = Number(process.env.E2E_FRONTEND_PORT ?? 9527);
const BASE_URL = `http://127.0.0.1:${FRONTEND_PORT}`;
const PNPM = process.platform === 'win32' ? 'pnpm.cmd' : 'pnpm';
const LOCAL_NO_PROXY = ['127.0.0.1', 'localhost', '::1'];

for (const key of ['NO_PROXY', 'no_proxy']) {
  const current = process.env[key];
  const entries = current ? current.split(',').filter(Boolean) : [];
  process.env[key] = [...new Set([...entries, ...LOCAL_NO_PROXY])].join(',');
}

const E2E_DB = process.env.E2E_DB_URL ?? 'sqlite://app_system_e2e.sqlite3?busy_timeout=5000';
const REDIS_URL = process.env.REDIS_URL ?? 'fakeredis://e2e';

const backendEnv = {
  DB_URL: E2E_DB,
  REDIS_URL,
  APP_DEBUG: 'false',
  WORKERS: '1',
  GUARD_ENABLED: 'false'
};

export default defineConfig({
  testDir: './e2e/tests',
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [['html', { open: 'never' }], ['github']] : [['list']],
  use: {
    baseURL: BASE_URL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure'
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: [
    {
      command: `uv run python scripts/e2e_init_db.py && uv run python -m granian --interface asgi --host 127.0.0.1 --port ${BACKEND_PORT} --workers 1 app:app`,
      cwd: '..',
      url: `http://127.0.0.1:${BACKEND_PORT}/health`,
      reuseExistingServer: false,
      timeout: 120_000,
      stdout: 'pipe',
      stderr: 'pipe',
      env: backendEnv
    },
    {
      command: `${PNPM} dev --host 127.0.0.1 --port ${FRONTEND_PORT}`,
      url: BASE_URL,
      reuseExistingServer: false,
      timeout: 120_000,
      stdout: 'pipe',
      stderr: 'pipe',
      env: {
        VITE_SERVICE_BASE_URL: `http://127.0.0.1:${BACKEND_PORT}/api/v1`
      }
    }
  ]
});
