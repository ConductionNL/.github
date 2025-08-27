import React, { useState } from 'react';
import clsx from 'clsx';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';
import Footer from '../components/Footer';
import Socials from '../components/Socials';
import ContactTeaser from '../components/Contact';
import Hero from '../components/Hero';
import CardsSection from '../components/CardsSection';
import styles from './index.module.css';

function WithWhom() {
  return (
    <section className={styles.sectionNeutral}>
      <div className="container">
        <h2 className={styles.sectionTitle}>Met wie doen we dat</h2>
        <div className="row">
          <div className={styles.withWhomImage + ' col'}>
            <img src="/img/partners/vng.png" alt="VNG" />
          </div>
          <div className={styles.withWhomImage + ' col'}>
            <img src="/img/partners/almere.png" alt="GemeenteAlmere" />
          </div>
          <div className={styles.withWhomImage + ' col'}>
            <img src="/img/partners/denbosch.png" alt="Gemeente Den Bosch" />
          </div>
          <div className={styles.withWhomImage + ' col'}>
            <img src="/img/partners/eindhoven.png" alt="Gemeente Eindhoven" />
          </div>
        </div>
        <div className="row">
          <div className={styles.withWhomImage + ' col'}>
            <img src="/img/partners/io.webp" alt="IO" />
          </div>
          <div className={styles.withWhomImage + ' col'}>
            <img src="/img/partners/rotterdam.png" alt="Gemeente Rotterdam" />
          </div>
          <div className={styles.withWhomImage + ' col'}>
            <img src="/img/partners/tilburg.png" alt="Gemeente Tilburg" />
          </div>
          <div className={styles.withWhomImage + ' col'}>
            <img src="/img/partners/utrecht.png" alt="Gemeente Utrecht" />
          </div>
        </div>
        <div className="row">
          <div className={styles.withWhomImage + ' col'}>
            <img src="/img/partners/nextcloud.png" alt="Nextcloud" />
          </div>
          <div className={styles.withWhomImage + ' col'}>
            <img src="/img/partners/yard.png" alt="YARD" />
          </div>
          <div className={styles.withWhomImage + ' col'}>
            <img src="/img/partners/ritense.png" alt="RITENSE" />
          </div>
          <div className={styles.withWhomImage + ' col'}>
            <img src="/img/partners/Shift2.png" alt="Shift2" />
          </div>
        </div>
        <div className="row">
          <div className={styles.withWhomImage + ' col'}>
            <img src="/img/partners/open_webconcept.png" alt="Open Webconcept" />
          </div>
          <div className={styles.withWhomImage + ' col'}>
            <img src="/img/partners/SIDN.png" alt="SIDN" />
          </div>
          <div className={styles.withWhomImage + ' col'}>
            <img src="/img/partners/bct.png" alt="BCT" />
          </div>
          <div className={styles.withWhomImage + ' col'}>
            <img src="/img/partners/hoorn.png" alt="Gemeente Hoorn" />
          </div>
        </div>
      </div>
    </section>
  );
}
export default function Home() {
  const { siteConfig } = useDocusaurusContext();

  const cards = [
    {
      title: 'Beheer',
      description: 'Conduction beschikt over een brede kennis van Kubernetes en Haven. Wij helpen met het faciliteren en beheren van omgevingen en bieden ook ondersteuning bij implementaties. <Link to="/beheer">Lees meer</Link>',
    },
    {
      title: 'Common Ground',
      description: 'Conduction levert een actieve bijdrage aan het succes van Common Ground. Dit doen we door al onze techniek volgens de Common Ground principes te ontwikkelen. Wij adviseren overheden en leveranciers hoe zij succesvol kunnen zijn binnen Common Ground. <Link to="/common-ground">Lees meer</Link>'
    },
    {
      title: 'Ontwikkelen',
      description: 'Conduction ontwikkelt open source software voor overheden en leveranciers. Als idealistische partij werken wij aan innovatie van diensten en doen mee aan innovatieprojecten. <Link to="/projecten">Lees meer</Link>'
    },
    
    {
      title: 'Trainingen',
      description: 'Conduction heeft veel ervaring opgedaan rondom Common Ground ontwikkeling, beheer van omgevingen en software. Deze ervaring delen wij graag met u in de vorm van trainingen en adviezen. Benieuwd hoe wij u kunnen helpen? <Link to="/trainingen">Lees meer</Link>'
    },
  ]
  return (
    <Layout title={siteConfig.title} description="Conduction | Public Tech">
      <Hero title="Public Tech" subtitle="" paragraphs={['Wij zijn wat je zou kunnen noemen Digital Socials, wij ontwikkelen techniek volgens de Common Ground principes, waarbij mens en community centraal staan. Graag dragen we dan ook bij aan het ontwikkelen van digitale oplossingen voor maatschappelijke vraagstukken:','<strong>"Tech to serve people"</strong>', 'Meer weten over ons bedrijf? Plan een afspraak.']} image="/img/mainHero.png" button={{
        title: 'Maak kennis met het bedrijf',
        link: '/over-ons'
      }}/>
      <main>
        <CardsSection title="Wat wij doen" image="/img/whatWeDo.png" cards={cards} cols={2}/>
        <WithWhom />
        <ContactTeaser />
        <Socials />
        <Footer />
      </main>
    </Layout>
  );
} 