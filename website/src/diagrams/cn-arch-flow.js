/**
 * <cn-arch-flow> — a single row of an architecture diagram.
 *
 * The "Request flow" pattern from preview/product-pages/technical-docs.html.
 * One row of boxes connected by arrows, where one box is solid cobalt
 * (the "owned by us" node) and at most one is an orange pointy-top hex
 * (the validator or attention node). Stack multiple <cn-arch-flow>s for
 * a multi-layer system diagram.
 *
 *   <cn-arch-flow arrow="right">
 *     <span>Client</span>
 *     <span accent>API layer</span>
 *     <span hex>Validator</span>
 *   </cn-arch-flow>
 *   <cn-arch-flow arrow="down">
 *     <span>Schema registry</span>
 *     <span accent>Storage adapter</span>
 *     <span>Audit log</span>
 *   </cn-arch-flow>
 *   <cn-arch-flow arrow="none">
 *     <span>Nextcloud DB</span>
 *     <span>MySQL</span>
 *     <span>PostgreSQL</span>
 *     <span>MongoDB</span>
 *     <span muted>…</span>
 *   </cn-arch-flow>
 *
 * Arrows are auto-inserted between consecutive children (skip with
 * arrow="none"). Each child is styled by its attributes — no class
 * names needed.
 *
 * Slots
 *   default  — row members, in order. Auto-numbered to interleave
 *              arrows between them in the shadow DOM.
 *
 * Attributes
 *   arrow    — right | down | none   (default: right)
 *
 * Child attributes (set on the slotted elements, not on cn-arch-flow)
 *   accent   — solid cobalt fill, white text. The "system" node.
 *   hex      — orange pointy-top hex. Use once per scene; this is the
 *              one-orange-per-scene knob for the diagram.
 *   muted    — opacity 0.5; for "and more" / out-of-scope placeholders.
 */

class CnArchFlow extends HTMLElement {
  static get observedAttributes() { return ['arrow']; }

  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
  }

  connectedCallback() {
    this.render();
    this._observer = new MutationObserver(() => this.render());
    this._observer.observe(this, { childList: true, attributes: true, subtree: true });
  }

  disconnectedCallback() {
    if (this._observer) this._observer.disconnect();
  }

  attributeChangedCallback() { if (this.shadowRoot) this.render(); }

  render() {
    const arrow = this.getAttribute('arrow') || 'right';
    const nodes = [...this.children];
    nodes.forEach((el, i) => { el.setAttribute('slot', `node-${i}`); });

    const arrowGlyph = arrow === 'down' ? '↓' : '→';
    const showArrows = arrow !== 'none';

    let rowMarkup = '';
    for (let i = 0; i < nodes.length; i++) {
      rowMarkup += `<slot name="node-${i}"></slot>`;
      if (showArrows && i < nodes.length - 1) {
        rowMarkup += `<span class="arrow" aria-hidden="true">${arrowGlyph}</span>`;
      }
    }

    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          font-family: var(--conduction-typography-font-family-code, ui-monospace, monospace);
        }

        .panel {
          background: var(--c-cobalt-50);
          border: 1px solid var(--c-cobalt-100);
          border-radius: var(--radius-md);
          padding: var(--space-6);
          display: flex;
          align-items: center;
          justify-content: center;
          gap: var(--space-3);
          flex-wrap: wrap;
          font-size: 11px;
          text-align: center;
        }

        .arrow {
          color: var(--c-cobalt-400);
          font-size: 16px;
          flex-shrink: 0;
        }

        /* Default node: white rounded box with cobalt-200 border. */
        ::slotted(*) {
          flex: 1 1 0;
          min-width: 80px;
          padding: var(--space-3) var(--space-2);
          background: white;
          border: 1px solid var(--c-cobalt-200);
          border-radius: var(--radius-sm);
          color: var(--c-cobalt-800);
          font-family: var(--conduction-typography-font-family-code, ui-monospace, monospace);
          font-size: 11px;
          text-align: center;
          display: flex;
          align-items: center;
          justify-content: center;
          box-sizing: border-box;
          min-height: 38px;
        }

        /* accent: the "system" node — solid cobalt brand fill. */
        ::slotted([accent]) {
          background: var(--c-blue-cobalt);
          color: white;
          border-color: var(--c-blue-cobalt);
        }

        /* hex: the orange pointy-top hex. The one-orange-per-scene knob.
         * Replaces the rectangle entirely with a clip-pathed shape so the
         * brand rule (hexes never rotate, always pointy-top) holds. */
        ::slotted([hex]) {
          flex: 0 0 auto;
          width: 64px;
          min-width: 0;
          height: 74px;
          padding: 0;
          background: var(--c-orange-knvb);
          color: white;
          border: 0;
          border-radius: 0;
          clip-path: var(--hex-pointy-top);
          font-weight: 600;
          font-size: 12px;
        }

        /* muted: out-of-scope / "and more" placeholder. */
        ::slotted([muted]) {
          opacity: 0.5;
        }
      </style>

      <div class="panel">${rowMarkup}</div>
    `;
  }
}

if (!customElements.get('cn-arch-flow')) {
  customElements.define('cn-arch-flow', CnArchFlow);
}

export { CnArchFlow };
