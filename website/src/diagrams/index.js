/**
 * Side-effect import that registers Conduction diagram custom elements
 * in the browser. Wired up via clientModules in docusaurus.config.js.
 *
 * Local copy of the @conduction/docusaurus-preset/diagrams subpath
 * pending the preset version bump that ships cn-pair + cn-arch-flow.
 * Once the next preset release lands, this file collapses to:
 *
 *   import '@conduction/docusaurus-preset/diagrams/cn-arch-flow';
 *
 * For now, the source lives next to it for build simplicity.
 */

import './cn-arch-flow.js';
