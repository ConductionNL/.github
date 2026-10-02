// SPDX-License-Identifier: EUPL-1.2
// gate-26 credits tests/e2e/visual/** only when the CI config runs it
// (keepiq#198), so the clean arm declares a project that does. Without it the
// visual spec beside this file would be a baseline CI never opens.
import { defineConfig } from '@playwright/test'

export default defineConfig({
	testDir: __dirname,
	projects: [
		{ name: 'chromium', testIgnore: ['**/visual/**'] },
		{ name: 'visual', testMatch: /visual\/.*\.spec\.ts/ },
	],
})
