// @ts-check

/** @type {import('@docusaurus/plugin-content-docs').SidebarsConfig} */
const sidebars = {
  tutorialSidebar: [
    'intro',
    {
      type: 'category',
      label: 'How We Work',
      items: [
        'WayOfWork/way-of-work',
        'WayOfWork/organisation',
        'WayOfWork/way-of-working',
        'WayOfWork/release-process',
        'WayOfWork/vacancies',
        'WayOfWork/contributing',
      ],
    },
    {
      type: 'category',
      label: 'ISO & Quality',
      items: [
        'ISO/iso-intro',
        // quality-policy and security-policy are draft — visible after management approval
        'ISO/incident-reporting',
        'ISO/security',
      ],
    },
    {
      type: 'category',
      label: 'Products & Services',
      items: [
        'Products/products-overview',
      ],
    },
  ],
};

module.exports = sidebars;
