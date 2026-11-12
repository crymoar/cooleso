// @ts-check
const { defineConfig, devices } = require('@playwright/test');

// BASE_URL — проверить уже опубликованный сайт (post-release).
// Без него тесты поднимают локальный сервер на папке map/.
const BASE_URL = process.env.BASE_URL;
// PW_CHROMIUM — путь к уже установленному Chromium (в облачной песочнице).
const launchOptions = process.env.PW_CHROMIUM
  ? { executablePath: process.env.PW_CHROMIUM, args: ['--no-sandbox'] }
  : {};

module.exports = defineConfig({
  testDir: './tests',
  timeout: 45_000,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : 'list',
  use: {
    baseURL: BASE_URL || 'http://localhost:4173/',
    launchOptions,
    trace: 'off',
  },
  webServer: BASE_URL ? undefined : {
    command: 'python3 -m http.server 4173 --directory map',
    url: 'http://localhost:4173/',
    reuseExistingServer: !process.env.CI,
  },
  projects: [
    { name: 'desktop', use: { viewport: { width: 1300, height: 900 } } },
    { name: 'mobile', use: { ...devices['Pixel 5'], browserName: 'chromium' } },
  ],
});
