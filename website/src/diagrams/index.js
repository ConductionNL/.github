/**
 * Side-effect import that registers Conduction diagram custom elements
 * in the browser. Wired up via clientModules in docusaurus.config.js.
 *
 * Pulls cn-arch-flow (and friends) from @conduction/docusaurus-preset
 * directly now that 2.10.2 ships them as published subpath exports.
 * The local copy that previously lived next to this file was a stopgap
 * during the preset version bump and has been removed.
 *
 * SSR guard: clientModules are imported on both server and client by
 * Docusaurus; cn-arch-flow uses `class extends HTMLElement` at module
 * top-level which is undefined in Node. Gate on canUseDOM so the import
 * only fires in the browser.
 */

import ExecutionEnvironment from '@docusaurus/ExecutionEnvironment';

if (ExecutionEnvironment.canUseDOM) {
  // eslint-disable-next-line global-require
  require('@conduction/docusaurus-preset/diagrams/cn-arch-flow');
}
