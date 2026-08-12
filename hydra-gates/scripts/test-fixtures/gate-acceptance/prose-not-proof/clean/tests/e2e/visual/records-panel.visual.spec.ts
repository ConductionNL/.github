import { test, expect } from '@playwright/test'

test('RecordsPanel renders as baselined', async ({ page }) => {
	await page.goto('/index.php/apps/prosefixture/#/records')
	await expect(page.locator('.records-panel')).toBeVisible()
	await expect(page).toHaveScreenshot('RecordsPanel.png')
})
