const { test, expect } = require('@playwright/test');

test('public dashboard loads and validates empty login', async ({ page }) => {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto(process.env.E2E_BASE_URL || 'https://ai-health-scanner-web.onrender.com', { waitUntil: 'domcontentloaded', timeout: 90000 });
  await expect(page).toHaveTitle(/AI Health Scanner/i);
  await expect(page.locator('#loginPage')).toBeVisible();
  await page.locator('#loginBtn').click();
  await expect(page.locator('#loginStatus')).toContainText(/enter your email and password/i);
  await page.locator('#registerBtn').click();
  await expect(page.locator('#loginStatus')).toContainText(/enter your email and password/i);
  expect(errors).toEqual([]);
});
