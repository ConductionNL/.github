// SPDX-FileCopyrightText: 2026 Conduction <info@conduction.nl>
// SPDX-License-Identifier: EUPL-1.2
export const proxy = {
	get() {
		return 1
	},
	set(v) {
		if (v) {
			this.v = v
		}
	},
	after(a) {
		return a
	},
}
