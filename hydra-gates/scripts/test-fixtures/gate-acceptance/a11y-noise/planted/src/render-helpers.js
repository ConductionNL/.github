// `.js` stays in scope: focus order is a property of the rendered DOM, not of
// the language that emitted it. Blanking script regions would have removed the
// gate-36 noise by removing detection, which is not a repair — this file is the
// assertion that it was not done that way.
export function render(el) {
	el.innerHTML = '<button tabindex="4">emitted from script</button>'
}
