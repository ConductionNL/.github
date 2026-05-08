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

  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
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

  themes: [BRAND_THEME],

  navbar: {
    items: [
      { to: '/ROADMAP', label: 'Roadmap', position: 'left' },
      { to: '/claude/', label: 'Claude workflow', position: 'left' },
      { to: '/iso/', label: 'ISO', position: 'left' },
      { to: '/Services/CodebaseStewardship', label: 'Services', position: 'left' },
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

  footer: {
    links: [
      {
        title: 'Documentation',
        items: [
          { label: 'Roadmap', to: '/ROADMAP' },
          { label: 'Claude workflow', to: '/claude/' },
          { label: 'ISO compliance', to: '/iso/' },
          { label: 'Catalog', to: '/Catalogi' },
        ],
      },
      ...baseFooterLinks().filter((c) => c.title === 'Conduction' || c.title === 'Documentatie'),
    ],
  },
});

/* docs/ is hand-written CommonMark with bare `<24h`, `<500`, `{sha}`,
   `{app}` substrings that Docusaurus 3's default MDX parser misreads
   as JSX. `format: 'md'` forces every doc to render as plain CommonMark,
   so curly braces and angle brackets are literal text. createConfig()
   doesn't pass the top-level `markdown` option through, so we set it
   here. There are no .mdx files in docs/, so 'md' (vs 'detect') is
   safe and the simplest fix. */
config.markdown = { format: 'md' };

module.exports = config;
