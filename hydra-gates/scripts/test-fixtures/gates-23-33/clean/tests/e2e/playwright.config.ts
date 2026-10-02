// SPDX-License-Identifier: EUPL-1.2
// gate-26 credits tests/e2e/visual/** only when the CI config runs it
// (keepiq#198), so this clean fixture declares a project that does.
import { defineConfig } from '@playwright/test'

export default defineConfig({
	testDir: __dirname,
	projects: [
		{ name: 'chromium', testIgnore: ['**/visual/**'] },
		{ name: 'visual', testMatch: /visual\/.*\.spec\.(ts|js)/ },
	],
})
