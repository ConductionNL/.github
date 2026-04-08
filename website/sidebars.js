// @ts-check

/** @type {import('@docusaurus/plugin-content-docs').SidebarsConfig} */
const sidebars = {
  tutorialSidebar: [
    'intro',
    {
      type: 'category',
      label: 'Working at Conduction',
      items: [
        'WayOfWork/onboarding',
        'WayOfWork/organisation',
        'WayOfWork/code-of-conduct',
        'WayOfWork/way-of-work',
        'WayOfWork/vacancies',
      ],
    },
    {
      type: 'category',
      label: 'Building Software',
      items: [
        'WayOfWork/spec-driven-development',
        'WayOfWork/development-pipeline',
        'WayOfWork/way-of-working',
        'WayOfWork/contributing',
        'WayOfWork/release-process',
      ],
    },
    {
      type: 'category',
      label: 'Support & Safety',
      items: [
        'WayOfWork/customer-support',
        'ISO/iso-intro',
        'ISO/incident-reporting',
        'ISO/security',
        'ISO/quality-policy',
        'ISO/security-policy',
        'ISO/privacy-policy',
      ],
    },
    'Products/products-overview',
    'WayOfWork/about-this-manual',
  ],
};

module.exports = sidebars;
