import { defineConfig, devices } from '@playwright/test'
import { existsSync } from 'node:fs'
import { resolve } from 'node:path'

const raiz = resolve(import.meta.dirname, '../..')
const pythonWin = resolve(raiz, '.venv/Scripts/python.exe')
export const PYTHON = existsSync(pythonWin) ? pythonWin : resolve(raiz, '.venv/bin/python')
const canal = process.env.E2E_BROWSER_CHANNEL ?? (process.platform === 'win32' ? 'msedge' : undefined)
const PORTA = 8010

export default defineConfig({
  testDir: './e2e',
  workers: 1,
  fullyParallel: false,
  timeout: 45_000,
  reporter: [['list']],
  use: { baseURL: `http://127.0.0.1:${PORTA}`, channel: canal, locale: 'pt-BR' },
  projects: [
    { name: 'desktop', use: { ...devices['Desktop Chrome'], channel: canal, viewport: { width: 1280, height: 900 } } },
    { name: 'mobile', use: { ...devices['Pixel 7'], channel: canal, viewport: { width: 375, height: 800 } } },
  ],
  webServer: {
    // FastAPI real servindo o build de produção e a Dense64 congelada.
    command: `"${PYTHON}" -m uvicorn app.main:app --app-dir "${resolve(raiz, 'web/backend')}" --host 127.0.0.1 --port ${PORTA}`,
    url: `http://127.0.0.1:${PORTA}/api/health`,
    timeout: 120_000,
    reuseExistingServer: false,
    env: { APP_ENV: 'production', RATE_LIMIT_PER_MINUTE: '100000', FRONTEND_DIST: resolve(raiz, 'web/frontend/dist') },
  },
})
