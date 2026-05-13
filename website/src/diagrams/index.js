/**
 * Side-effect import that registers Conduction diagram custom elements
 * in the browser. Wired up via clientModules in docusaurus.config.js.
 *
 * Pulls cn-arch-flow (and friends) from @conduction/docusaurus-preset
 * directly now that 2.10.2 ships them as published subpath exports.
 * The local copy that previously lived next to this file was a stopgap
 * during the preset version bump and has been removed.
 */

import '@conduction/docusaurus-preset/diagrams/cn-arch-flow';
