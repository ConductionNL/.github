import React from 'react';
import clsx from 'clsx';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';
import HomepageFeatures from '@site/src/components/HomepageFeatures';

import styles from './index.module.css';

/**
 * Component to display the main vision statement
 * @returns {JSX.Element} VisionStatement component
 */
function VisionStatement() {
  return (
    <div className={clsx(styles.vision, 'margin-vert--xl')}>
      <div className="container">
        <div className="text--center">
          <h2 className={styles.visionText}>
            "By 2035, Conduction ensures that all residents of the Netherlands 
            automatically receive the government services they are entitled to."
          </h2>
        </div>
      </div>
    </div>
  );
}

function HomepageHeader() {
  const {siteConfig} = useDocusaurusContext();
  return (
    <header className={clsx('hero hero--primary', styles.heroBanner)}>
      <div className="container">
        <h1 className="hero__title">{siteConfig.title}</h1>
        <p className="hero__subtitle">{siteConfig.tagline}</p>
        <div className={styles.buttons}>
          <Link
            className="button button--secondary button--lg"
            to="/docs/intro">
            Explore Our Documentation →
          </Link>
        </div>
      </div>
    </header>
  );
}

export default function Home() {
  const {siteConfig} = useDocusaurusContext();
  return (
    <Layout
      title={`${siteConfig.title}`}
      description="Flexible object management for Nextcloud">
      <HomepageHeader />
      <VisionStatement />
      <main>
        <HomepageFeatures />
      </main>
    </Layout>
  );
} 