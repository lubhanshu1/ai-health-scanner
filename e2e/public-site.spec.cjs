const { test, expect } = require('@playwright/test');

test('public app: register, login, run three screening modes, and reload history after re-login', async ({ page }) => {
  test.setTimeout(180000);
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));

  const email = `e2e-${Date.now()}-${Math.random().toString(16).slice(2, 8)}@example.com`;
  const password = `E2e-Test-${Date.now()}!`;
  const apiHealth = await page.request.get('https://ai-health-backend-g329.onrender.com/health', { timeout: 60000 });
  expect(apiHealth.status()).toBe(200);
  const health = await apiHealth.json();
  expect(health.status).toBe('ok');
  expect(health).toHaveProperty('persistent_storage');
  expect(typeof health.storage_backend).toBe('string');
  console.log('PUBLIC API STORAGE CHECK:', JSON.stringify({ backend: health.storage_backend, persistent: health.persistent_storage }));

  await page.goto(process.env.E2E_BASE_URL || 'https://ai-health-scanner-web.onrender.com', { waitUntil: 'domcontentloaded', timeout: 90000 });
  await expect(page).toHaveTitle(/AI Health Scanner/i);
  await expect(page.locator('#loginPage')).toBeVisible();

  await page.locator('#authEmail').fill(email);
  await page.locator('#authPassword').fill(password);
  await page.locator('#registerBtn').click();
  await expect(page.locator('#loginStatus')).toContainText(/account created/i, { timeout: 30000 });
  await page.locator('#loginBtn').click();
  await expect(page.locator('#dashboard')).toBeVisible({ timeout: 60000 });
  await expect(page.locator('#profileBox')).toContainText(email, { timeout: 30000 });

  // Overview screen
  await page.locator('#age').fill('35');
  await page.locator('#glucose').fill('100');
  await page.locator('#bp').fill('120');
  await page.locator('#bmi').fill('24');
  await page.locator('#scanBtn').click();
  await expect(page.locator('#result .risk-big')).toContainText(/risk/i, { timeout: 60000 });
  await expect(page.locator('#history .history-card')).toHaveCount(1, { timeout: 30000 });

  // Heart screen
  await page.locator('[data-mode="heart"]').click();
  await page.locator('#h_age').fill('45');
  await page.locator('#sex').selectOption('1');
  await page.locator('#trestbps').fill('125');
  await page.locator('#chol').fill('210');
  await page.locator('#thalach').fill('150');
  await page.locator('#oldpeak').fill('1');
  await page.locator('#scanBtn').click();
  await expect(page.locator('#result .risk-big')).toContainText(/risk/i, { timeout: 60000 });
  await expect(page.locator('#history .history-card')).toHaveCount(2, { timeout: 30000 });

  // Diabetes screen
  await page.locator('[data-mode="diabetes"]').click();
  for (const [id, value] of Object.entries({
    pregnancies: '1', d_glucose: '110', blood_pressure: '75', skin_thickness: '20',
    insulin: '80', d_bmi: '25', diabetes_pedigree: '0.4', d_age: '35'
  })) await page.locator('#' + id).fill(value);
  await page.locator('#scanBtn').click();
  await expect(page.locator('#result .risk-big')).toContainText(/risk/i, { timeout: 60000 });
  await expect(page.locator('#history .history-card')).toHaveCount(3, { timeout: 30000 });

  // Sign out and back in to verify server-side history retrieval.
  await page.locator('#logoutBtn').click();
  await expect(page.locator('#loginPage')).toBeVisible();
  await page.locator('#authEmail').fill(email);
  await page.locator('#authPassword').fill(password);
  await page.locator('#loginBtn').click();
  await expect(page.locator('#dashboard')).toBeVisible({ timeout: 60000 });
  await expect(page.locator('#history .history-card')).toHaveCount(3, { timeout: 30000 });

  expect(errors, 'uncaught browser JavaScript errors').toEqual([]);
});
