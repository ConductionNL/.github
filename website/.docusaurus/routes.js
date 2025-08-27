import React from 'react';
import ComponentCreator from '@docusaurus/ComponentCreator';

export default [
  {
    path: '/__docusaurus/debug',
    component: ComponentCreator('/__docusaurus/debug', '7c5'),
    exact: true
  },
  {
    path: '/__docusaurus/debug/config',
    component: ComponentCreator('/__docusaurus/debug/config', '7d9'),
    exact: true
  },
  {
    path: '/__docusaurus/debug/content',
    component: ComponentCreator('/__docusaurus/debug/content', '163'),
    exact: true
  },
  {
    path: '/__docusaurus/debug/globalData',
    component: ComponentCreator('/__docusaurus/debug/globalData', '18c'),
    exact: true
  },
  {
    path: '/__docusaurus/debug/metadata',
    component: ComponentCreator('/__docusaurus/debug/metadata', '6f1'),
    exact: true
  },
  {
    path: '/__docusaurus/debug/registry',
    component: ComponentCreator('/__docusaurus/debug/registry', '9f4'),
    exact: true
  },
  {
    path: '/__docusaurus/debug/routes',
    component: ComponentCreator('/__docusaurus/debug/routes', 'ac1'),
    exact: true
  },
  {
    path: '/beheer',
    component: ComponentCreator('/beheer', '2b0'),
    exact: true
  },
  {
    path: '/common-ground',
    component: ComponentCreator('/common-ground', 'ef0'),
    exact: true
  },
  {
    path: '/contact',
    component: ComponentCreator('/contact', '0d1'),
    exact: true
  },
  {
    path: '/kwaliteitsbeleid',
    component: ComponentCreator('/kwaliteitsbeleid', '9d2'),
    exact: true
  },
  {
    path: '/over-ons',
    component: ComponentCreator('/over-ons', '310'),
    exact: true
  },
  {
    path: '/privacy',
    component: ComponentCreator('/privacy', 'be3'),
    exact: true
  },
  {
    path: '/projecten',
    component: ComponentCreator('/projecten', '9fe'),
    exact: true
  },
  {
    path: '/trainingen',
    component: ComponentCreator('/trainingen', '3a2'),
    exact: true
  },
  {
    path: '/docs',
    component: ComponentCreator('/docs', '143'),
    routes: [
      {
        path: '/docs/intro',
        component: ComponentCreator('/docs/intro', '7ec'),
        exact: true,
        sidebar: "tutorialSidebar"
      },
      {
        path: '/docs/ISO/iso',
        component: ComponentCreator('/docs/ISO/iso', '8b0'),
        exact: true,
        sidebar: "tutorialSidebar"
      },
      {
        path: '/docs/knowledge/intro',
        component: ComponentCreator('/docs/knowledge/intro', '2a2'),
        exact: true,
        sidebar: "tutorialSidebar"
      },
      {
        path: '/docs/Products/Components',
        component: ComponentCreator('/docs/Products/Components', '95f'),
        exact: true,
        sidebar: "tutorialSidebar"
      },
      {
        path: '/docs/Products/Consultancy',
        component: ComponentCreator('/docs/Products/Consultancy', '272'),
        exact: true,
        sidebar: "tutorialSidebar"
      },
      {
        path: '/docs/Products/Market',
        component: ComponentCreator('/docs/Products/Market', '3ae'),
        exact: true,
        sidebar: "tutorialSidebar"
      },
      {
        path: '/docs/Products/Partners',
        component: ComponentCreator('/docs/Products/Partners', 'ece'),
        exact: true,
        sidebar: "tutorialSidebar"
      },
      {
        path: '/docs/Products/Pricing',
        component: ComponentCreator('/docs/Products/Pricing', 'aee'),
        exact: true,
        sidebar: "tutorialSidebar"
      },
      {
        path: '/docs/Products/products',
        component: ComponentCreator('/docs/Products/products', 'e6d'),
        exact: true,
        sidebar: "tutorialSidebar"
      },
      {
        path: '/docs/Products/Projects/InnovatieProjecten',
        component: ComponentCreator('/docs/Products/Projects/InnovatieProjecten', 'add'),
        exact: true,
        sidebar: "tutorialSidebar"
      },
      {
        path: '/docs/Products/Projects/Nextcon',
        component: ComponentCreator('/docs/Products/Projects/Nextcon', '5a9'),
        exact: true,
        sidebar: "tutorialSidebar"
      },
      {
        path: '/docs/Products/Services',
        component: ComponentCreator('/docs/Products/Services', 'dba'),
        exact: true,
        sidebar: "tutorialSidebar"
      },
      {
        path: '/docs/Products/Training',
        component: ComponentCreator('/docs/Products/Training', '3d1'),
        exact: true,
        sidebar: "tutorialSidebar"
      },
      {
        path: '/docs/WayOfWork/competences',
        component: ComponentCreator('/docs/WayOfWork/competences', 'c4c'),
        exact: true,
        sidebar: "tutorialSidebar"
      },
      {
        path: '/docs/WayOfWork/Issue_flow',
        component: ComponentCreator('/docs/WayOfWork/Issue_flow', '4e7'),
        exact: true,
        sidebar: "tutorialSidebar"
      },
      {
        path: '/docs/WayOfWork/join',
        component: ComponentCreator('/docs/WayOfWork/join', '874'),
        exact: true,
        sidebar: "tutorialSidebar"
      },
      {
        path: '/docs/WayOfWork/organisation',
        component: ComponentCreator('/docs/WayOfWork/organisation', '9ef'),
        exact: true,
        sidebar: "tutorialSidebar"
      },
      {
        path: '/docs/WayOfWork/Vacancies',
        component: ComponentCreator('/docs/WayOfWork/Vacancies', '373'),
        exact: true,
        sidebar: "tutorialSidebar"
      },
      {
        path: '/docs/WayOfWork/way-of-work',
        component: ComponentCreator('/docs/WayOfWork/way-of-work', 'ec2'),
        exact: true,
        sidebar: "tutorialSidebar"
      }
    ]
  },
  {
    path: '/',
    component: ComponentCreator('/', '002'),
    exact: true
  },
  {
    path: '*',
    component: ComponentCreator('*'),
  },
];
