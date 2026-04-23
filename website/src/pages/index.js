import React from 'react';
import clsx from 'clsx';
import Link from '@docusaurus/Link';
import Translate from '@docusaurus/Translate';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';
import HomepageFeatures from '@site/src/components/HomepageFeatures';

import styles from './index.module.css';

function VisionStatement() {
  return (
    <div className={clsx(styles.vision, 'margin-vert--xl')}>
      <div className="container">
        <div className="text--center">
          <h2 className={styles.visionText}>
            <Translate id="homepage.vision">
              By 2035, Conduction ensures that all residents of the Netherlands
              automatically receive the government services they are entitled to.
            </Translate>
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
            <Translate id="homepage.cta">Explore Our Documentation</Translate> →
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
