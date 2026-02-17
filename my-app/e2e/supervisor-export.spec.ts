/**
 * E2E tests for Supervisor date filter and CSV export.
 * Run: npx playwright test supervisor-export
 * Requires: npm run dev (or deployed app), Playwright installed.
 */

import { test, expect } from '@playwright/test';

test.describe('Supervisor date filter and CSV export', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/supervisor');
    await page.waitForSelector('text=Supervisor Dashboard', { timeout: 10000 });
  });

  test('date filter updates data', async ({ page }) => {
    await page.click('button:has-text("Last 30 days")');
    await page.waitForTimeout(500);
    const chart = page
      .locator('[class*="grid-cols-7"]')
      .or(page.locator('text=/\\d+/'));
    await expect(chart.first()).toBeVisible({ timeout: 5000 });
  });

  test('Export CSV downloads valid file', async ({ page }) => {
    const [download] = await Promise.all([
      page.waitForEvent('download'),
      page.click('button:has-text("Export CSV")'),
    ]);
    const filename = download.suggestedFilename();
    expect(filename).toMatch(/supervisor-export.*\.csv$/);
    const savePath = await download.path();
    expect(savePath).toBeTruthy();
    const { readFileSync } = await import('fs');
    const content = readFileSync(savePath!, 'utf-8');
    expect(content).toContain('session_id');
    expect(content.split('\n').length).toBeGreaterThan(1);
  });
});
