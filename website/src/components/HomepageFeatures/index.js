import React from 'react';
import clsx from 'clsx';
import styles from './styles.module.css';

/**
 * List of features displayed on the homepage
 * Each feature represents a main section of Conduction's documentation
 */
const FeatureList = [
  {
    title: 'How We Work',
    description: (
      <>
        Comprehensive user manuals and organizational information to understand our processes, 
        methodologies, and company culture. Learn how we operate and collaborate effectively.
      </>
    ),
  },
  {
    title: 'ISO Certification',
    description: (
      <>
        Our commitment to quality and security standards through ISO certification. 
        Detailed information about our quality management system and security practices.
      </>
    ),
  },
  {
    title: 'Products & Services',
    description: (
      <>
        Explore our suite of components and services. Detailed documentation about our 
        solutions, technical specifications, and implementation guides.
      </>
    ),
  },
];

/**
 * Component to render a single feature
 * @param {string} title - The title of the feature
 * @param {JSX.Element} description - The description of the feature
 * @returns {JSX.Element} Feature component
 */
function Feature({title, description}) {
  return (
    <div className={clsx('col col--4')}>
      <div className="text--center padding-horiz--md">
        <h3>{title}</h3>
        <p>{description}</p>
      </div>
    </div>
  );
}

/**
 * Main component that displays all features on the homepage
 * @returns {JSX.Element} HomepageFeatures component
 */
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