// @ts-check
const path = require('path');
const { createConfig, baseFooterLinks } = require('@conduction/docusaurus-preset');
const BRAND_THEME = require.resolve('@conduction/docusaurus-preset/theme');

/* docs.conduction.nl serves the engineering + product knowledge base from
   the repo-root /docs folder (one level up from this website/ build root).
   Source markdown stays where contributors expect it; this build only
   provides the Docusaurus shell + brand chrome via @conduction/docusaurus-preset. */

const config = createConfig({
  title: 'Conduction Docs',
  tagline: 'Engineering, product, and ISO knowledge base.',
  url: 'https://docs.conduction.nl',
  baseUrl: '/',

  organizationName: 'ConductionNL',
  projectName: '.github',

  /* Two locales, English default. Dutch translations live under
     i18n/nl/ and are seeded as a skeleton — Docusaurus falls back to
     EN for any string that isn't yet translated, so /nl/ routes are
     safe to expose even before a full translation pass. URL shape:
       /         → English (canonical)
       /nl/      → Nederlands */
  i18n: {
    defaultLocale: 'en',
    locales: ['en', 'nl'],
    localeConfigs: {
      en: { label: 'English',    htmlLang: 'en-GB', direction: 'ltr' },
      nl: { label: 'Nederlands', htmlLang: 'nl-NL', direction: 'ltr' },
    },
  },

  presets: [
    [
      'classic',
      {
        docs: {
          path: path.resolve(__dirname, '..', 'docs'),
          routeBasePath: '/',
          sidebarPath: require.resolve('./sidebars.js'),
          editUrl: 'https://github.com/ConductionNL/.github/tree/main/',
          /* Generated artefact lives in docs/claude/examples/ and isn't
             intended to render. Skip non-markdown files (.example, .json). */
          exclude: ['**/examples/**', '**/img/**'],
        },
        blog: false,
        theme: {
          customCss: require.resolve('./src/css/custom.css'),
        },
      },
    ],
  ],

  themes: [BRAND_THEME, '@docusaurus/theme-mermaid'],

  navbar: {
    items: [
      { to: '/WayOfWork/way-of-work', label: 'Way of Work', position: 'left' },
      { href: 'https://github.com/orgs/ConductionNL/projects/4', label: 'Roadmap', position: 'left' },
      { to: '/hydra/', label: 'Hydra', position: 'left' },
      { to: '/claude/', label: 'Using Hydra', position: 'left' },
      { to: '/iso/', label: 'ISO', position: 'left' },
      { href: 'https://www.conduction.nl/support/', label: 'Support', position: 'left' },
      { href: 'https://www.conduction.nl/apps/', label: 'Products', position: 'left' },
      { type: 'localeDropdown', position: 'right' },
      {
        href: 'https://github.com/ConductionNL/.github',
        label: 'GitHub',
        position: 'right',
      },
    ],
  },

  /* Product-page convention: drop the canal-footer mini-games on docs
     surfaces. Static skyline + canal decoration still render. */
  minigames: false,

  /* Single Conduction wordmark block on the left of the canal-footer
     (no partner pairing on the docs site). */
  footerBrand: { wordmark: 'Conduction' },

  /* Mermaid: Conduction brand theme applied site-wide so authors write
     plain ```mermaid blocks. Colours track the design-system tokens in
     tokens.css; the `accent` classDef is the one-orange-per-scene knob
     (use `:::accent` on a single node per diagram).
     Goes into themeConfig (not top-level) — the preset's createConfig
     only forwards themeConfig.mermaid to @docusaurus/theme-mermaid. */
  themeConfig: {
    mermaid: {
      /* Theme must live here (not inside options) — the theme-mermaid
         client spreads options first and then overlays
         themeConfig.mermaid.theme[colorMode] last, so options.theme is
         always overridden. */
      theme: { light: 'base', dark: 'base' },
      options: {
        themeVariables: {
          background:        '#ffffff',
          primaryColor:      '#21468B', // cobalt-blue — solid node fill
          primaryTextColor:  '#ffffff', // white — readable on cobalt
          primaryBorderColor:'#21468B', // = fill, so no visible border
          secondaryColor:    '#152D5C', // cobalt-700
          tertiaryColor:     '#ffffff',
          lineColor:         '#4D69A4', // cobalt-400 — edges
          textColor:         '#152D5C', // cobalt-700 — labels outside nodes
          fontFamily:        "'Figtree', system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif",
          fontSize:          '14px',
        },
      },
    },
  },

  footer: {
    links: [
      {
        title: 'Documentation',
        items: [
          { label: 'Roadmap', href: 'https://github.com/orgs/ConductionNL/projects/4' },
          { label: 'Hydra', to: '/hydra/' },
          { label: 'Using Hydra', to: '/claude/' },
          { label: 'ISO compliance', to: '/iso/' },
        ],
      },
      ...baseFooterLinks().filter((c) => c.title === 'Conduction' || c.title === 'Documentatie'),
    ],
  },
});

/* docs/*.md files are hand-written CommonMark with bare `<24h`, `<500`,
   `{sha}`, `{app}` substrings that Docusaurus 3's default MDX parser
   misreads as JSX. `format: 'detect'` resolves per-extension: `.md`
   stays CommonMark (curly braces and angle brackets are literal text)
   while `.mdx` files in docs/WayOfWork/ (onboarding, organisation,
   about-this-manual) opt in to MDX so they can use <Tabs>, <ToolList>,
   etc. createConfig() doesn't pass the top-level `markdown` option
   through, so we set it here. */
/* Mermaid: enable on both .md and .mdx. The theme registers a remark
   plugin that picks up ```mermaid fenced blocks regardless of extension.
   The brand theme is set inside each diagram via an %%{init}%% block so
   nodes inherit Conduction cobalt/orange tokens; see
   src/css/conduction-mermaid.css for the rendered-SVG overrides. */
config.markdown = { format: 'detect', mermaid: true };

/* Site-wide client-side modules. src/diagrams/index.js is a
   side-effect import that registers Conduction diagram custom
   elements (<cn-arch-flow>, …) on every page so authors can use
   them directly in MDX/Markdown without per-page imports.
   Set here (not inside createConfig) because the preset's
   createConfig wrapper doesn't forward clientModules through. */
config.clientModules = [require.resolve('./src/diagrams/index.js')];

module.exports = config;
