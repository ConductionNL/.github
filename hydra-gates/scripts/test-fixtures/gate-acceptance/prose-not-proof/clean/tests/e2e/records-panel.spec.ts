import { test, expect } from '@playwright/test'

// @e2e records-panel::the-panel-lists-stored-records
test('records panel lists every stored record', async ({ page }) => {
	await page.goto('/index.php/apps/prosefixture/#/records')
	await expect(page.locator('.records-panel li')).toHaveCount(3)
	await expect(page.locator('.records-panel li').first()).toHaveText('First record')
})
