// gate-36 keeps `.js`/`.ts` in scope: a positive tabindex is a property of the
// rendered DOM whoever emitted it. This comment mentions tabindex="3" and must
// not fire; the planted arm proves the executable form still does.
export function attrs() {
	return { tabindex: '0' }
}
