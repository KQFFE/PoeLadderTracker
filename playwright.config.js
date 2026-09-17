const { defineConfig, devices } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './tests/e2e',
  timeout: 30000,
  expect: {
    timeout: 5000,
  },
  fullyParallel: true,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: 'http://127.0.0.1:5000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    browserName: 'chromium',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: {
    command: 'python proxy_server.py',
    url: 'http://127.0.0.1:5000',
    reuseExistingServer: !process.env.CI,
    timeout: 120000,
    env: {
      PORT: '5000',
      GGG_CLIENT_ID: 'test-client-id',
      GGG_CLIENT_SECRET: 'test-client-secret',
      GGG_CONTACT_EMAIL: 'test@example.com',
    },
  },
});
