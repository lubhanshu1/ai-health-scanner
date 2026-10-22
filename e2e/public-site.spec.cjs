const { test, expect } = require('@playwright/test');

test('public dashboard loads and validates empty login', async ({ page }) => {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto(process.env.E2E_BASE_URL || 'https://ai-health-scanner-web.onrender.com', { waitUntil: 'domcontentloaded', timeout: 90000 });
  await expect(page).toHaveTitle(/AI Health Scanner/i);
  await expect(page.locator('#loginPage')).toBeVisible();
  const apiHealth = await page.evaluate(async () => { const response = await fetch('https://ai-health-backend-g329.onrender.com/health'); return { status: response.status, body: await response.json() }; });
  expect(apiHealth.status).toBe(200);
  expect(apiHealth.body.status).toBe('ok');
  console.log('PUBLIC API STORAGE CHECK:', JSON.stringify({ backend: apiHealth.body.storage_backend, persistent: apiHealth.body.persistent_storage }));
  await page.locator('#loginBtn').click();
  await expect(page.locator('#loginStatus')).toContainText(/enter your email and password/i);
  await page.locator('#registerBtn').click();
  await expect(page.locator('#loginStatus')).toContainText(/enter your email and password/i);
  expect(errors).toEqual([]);
});
