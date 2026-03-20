// @ts-check
// Note: type annotations allow type checking and IDEs autocompletion

/** @type {import('@docusaurus/types').Config} */
const config = {
  title: 'Conduction Documentation',
  tagline: 'Documentation for Conduction\'s open source solutions',
  url: 'https://docs.conduction.nl',
  baseUrl: '/',

  // GitHub pages deployment config
  organizationName: 'conductionnl',
  projectName: '.github',
  trailingSlash: false,

  onBrokenLinks: 'throw',
  onBrokenMarkdownLinks: 'warn',

  // Even if you don't use internalization, you can use this field to set useful
  // metadata like html lang
  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  presets: [
    [
      'classic',
      /** @type {import('@docusaurus/preset-classic').Options} */
      ({
        docs: {
          sidebarPath: require.resolve('./sidebars.js'),
          editUrl:
            'https://github.com/conductionnl/docs/tree/main/website/',
        },
        blog: false,
        theme: {
          customCss: require.resolve('./src/css/custom.css'),
        },
      }),
    ],
  ],

  themeConfig:
    /** @type {import('@docusaurus/preset-classic').ThemeConfig} */
    ({
      colorMode: {
        disableSwitch: true,
        respectPrefersColorScheme: false,
        defaultMode: 'light',
      },
      navbar: {
        logo: {
          alt: 'Conduction Logo',
          src: 'img/logo.png',
        },
        items: [
          { to: '/over-ons', label: 'Over ons', position: 'right' },
          { to: '/beheer', label: 'Beheer', position: 'right' },
          { to: '/projecten', label: 'Projecten', position: 'right' },
          { to: '/common-ground', label: 'Common Ground', position: 'right' },
          { to: '/trainingen', label: 'Trainingen', position: 'right' },
          { to: '/contact', label: 'Contact', position: 'right' },
        ],
      },
      prism: {
        theme: require('prism-react-renderer/themes/github'),
        darkTheme: require('prism-react-renderer/themes/dracula'),
      },
    })
};

module.exports = config;