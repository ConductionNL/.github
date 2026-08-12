import { test, expect } from '@playwright/test'

// TODO: the records-panel scenario is still unwritten. Its anchor is @e2e records-panel::the-panel-lists-stored-records and its screen is RecordsPanel; add the assertion and the baseline once the fixture lands.
test('records panel — placeholder, asserts only that the app mounted', async ({ page }) => {
	await page.goto('/index.php/apps/prosefixture/')
	await expect(page.locator('#app')).toBeVisible()
})
