import React from 'react';
import clsx from 'clsx';
import styles from './styles.module.css';
import Link from '@docusaurus/Link';
import Translate from '@docusaurus/Translate';

const FeatureList = [
  {
    titleId: 'homepage.feature.howWeWork.title',
    titleDefault: 'How We Work',
    descriptionId: 'homepage.feature.howWeWork.description',
    descriptionDefault: 'Our employee handbook: processes, culture, and how we collaborate. Everything you need to get started and stay aligned.',
    link: '/docs/WayOfWork/way-of-work',
    buttonId: 'homepage.feature.howWeWork.button',
    buttonDefault: 'Learn How We Work',
  },
  {
    titleId: 'homepage.feature.iso.title',
    titleDefault: 'ISO & Quality',
    descriptionId: 'homepage.feature.iso.description',
    descriptionDefault: 'Our commitment to quality and security through ISO 9001 and 27001 certification. Incident reporting, security policy, and quality management.',
    link: '/docs/ISO/iso-intro',
    buttonId: 'homepage.feature.iso.button',
    buttonDefault: 'View ISO Documentation',
  },
  {
    titleId: 'homepage.feature.products.title',
    titleDefault: 'Products & Services',
    descriptionId: 'homepage.feature.products.description',
    descriptionDefault: 'Our open-source components and services for digital government infrastructure. Technical documentation and implementation guides.',
    link: '/docs/Products/products-overview',
    buttonId: 'homepage.feature.products.button',
    buttonDefault: 'Explore Products',
  },
];

function Feature({titleId, titleDefault, descriptionId, descriptionDefault, link, buttonId, buttonDefault}) {
  return (
    <div className={clsx('col col--4')}>
      <div className="text--center padding-horiz--md">
        <h3><Translate id={titleId}>{titleDefault}</Translate></h3>
        <p><Translate id={descriptionId}>{descriptionDefault}</Translate></p>
        <Link
          className="button button--secondary button--lg"
          to={link}>
          <Translate id={buttonId}>{buttonDefault}</Translate>
        </Link>
      </div>
    </div>
  );
}

export default function HomepageFeatures() {
  return (
    <section className={styles.features}>
      <div className="container">
        <div className="row">
          {FeatureList.map((props, idx) => (
            <Feature key={idx} {...props} />
          ))}
        </div>
      </div>
    </section>
  );
}
