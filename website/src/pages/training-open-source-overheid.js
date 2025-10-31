import React from 'react';
import Layout from '@theme/Layout';
import Footer from '../components/Footer';
import Socials from '../components/Socials';
import ContactTeaser from '../components/Contact';
import Hero from '../components/Hero';
import styles from './index.module.css';
import Link from '@docusaurus/Link';

export default function TrainingOpenSourceOverheid() {
    return (
        <Layout title="Training Open Source binnen overheid" description="Training Open Source binnen overheid">
            <Hero
                title="Training Open Source binnen overheid"
                paragraphs={[
                    'Deze training is specifiek ontwikkeld voor iedereen binnen de overheid en gaat in op de huidige ontwikkelingen, de voor- en nadelen en welke doelen Open Source nog meer bereikt binnen de overheid.',
                    'Meer weten over de training?'
                ]}
                image="/img/trainingDetails/ProgrammerYellow.png"
                button={{
                    title: 'Neem hier contact op',
                    link: '/contact'
                }}
            />

            <section className={styles.sectionLight}>
                <div className="container">
                    <h2 className={styles.sectionTitle}>Inhoud van de training</h2>

                    <div style={{ marginBottom: '40px' }}>
                        <h3 style={{ color: 'var(--ifm-color-primary)', marginBottom: '15px' }}>(Algemene) voordelen van Open Source</h3>
                        <ul style={{ fontSize: '1.05rem', lineHeight: '1.8' }}>
                            <li><strong>Bredere kennisbasis</strong> - Door open source te delen, ontstaat een grotere pool aan kennis en expertise</li>
                            <li><strong>Gezamenlijke doorontwikkeling</strong> - Samen met andere organisaties kunnen oplossingen worden verbeterd</li>
                            <li><strong>Breder leverancierslandschap</strong> - Minder afhankelijkheid van specifieke leveranciers</li>
                            <li><strong>Verstrekking economische infrastructuur Nederland</strong> - Bijdrage aan de Nederlandse digitale economie</li>
                            <li><strong>Vergroten arbeidsmarkt</strong> - Meer professionals met relevante kennis en ervaring</li>
                            <li><strong>Transparantie</strong> - Inzicht in hoe software werkt en wat deze doet</li>
                        </ul>
                    </div>

                    <div style={{ marginBottom: '40px' }}>
                        <h3 style={{ color: 'var(--ifm-color-primary)', marginBottom: '15px' }}>Voorbeelden van andere projecten</h3>
                        <ul style={{ fontSize: '1.05rem', lineHeight: '1.8' }}>
                            <li><strong>Signalen</strong> → Interne code van gemeente Amsterdam die 'extern' gegaan is</li>
                            <li><strong>Coronamelder & Coronacheck</strong> - Succesvolle open source projecten op nationaal niveau</li>
                        </ul>
                    </div>

                    <div style={{ marginBottom: '40px' }}>
                        <h3 style={{ color: 'var(--ifm-color-primary)', marginBottom: '15px' }}>Tegenstanders worden bondgenoten</h3>
                        <p style={{ fontSize: '1.05rem', lineHeight: '1.7' }}>
                            Hoe organisaties als Foundation for Public Code & Code for NL samenwerking stimuleren en een community bouwen
                            waarin iedereen bijdraagt.
                        </p>
                    </div>

                    <div style={{ marginBottom: '40px' }}>
                        <h3 style={{ color: 'var(--ifm-color-primary)', marginBottom: '15px' }}>Kwantificeren van baten vs. kosten</h3>
                        <ul style={{ fontSize: '1.05rem', lineHeight: '1.8' }}>
                            <li><strong>Baten</strong>: Gedeelde kennis, bijdragen van anderen, innovatie</li>
                            <li><strong>Kosten</strong>: Beheer en marketing rondom community, tijd en middelen</li>
                        </ul>
                        <p style={{ fontSize: '1.05rem', lineHeight: '1.7', marginTop: '15px' }}>
                            We bespreken hoe je dit concreet in kaart kunt brengen voor jouw organisatie.
                        </p>
                    </div>
                </div>
            </section>

            <section className={styles.sectionNeutral}>
                <div className="container">
                    <div style={{ marginBottom: '40px' }}>
                        <h3 style={{ color: 'var(--ifm-color-primary)', marginBottom: '15px' }}>Risico's</h3>
                        <p style={{ fontSize: '1.05rem', lineHeight: '1.7' }}><strong>Wat kan er fout gaan?</strong></p>
                        <ul style={{ fontSize: '1.05rem', lineHeight: '1.8' }}>
                            <li>Ivoren toren - Intern ontwikkelen zonder externe input</li>
                            <li>Open Source in name only - Code is openbaar maar geen echte community</li>
                        </ul>
                    </div>

                    <div style={{ marginBottom: '40px' }}>
                        <h3 style={{ color: 'var(--ifm-color-primary)', marginBottom: '15px' }}>Hoe werkt het met Auditors</h3>
                        <p style={{ fontSize: '1.05rem', lineHeight: '1.7' }}>
                            Hoe ga je om met audits bij open source software? Wat zijn de aandachtspunten en hoe borg je kwaliteit?
                        </p>
                    </div>

                    <div style={{ marginBottom: '40px' }}>
                        <h3 style={{ color: 'var(--ifm-color-primary)', marginBottom: '15px' }}>Wat wordt er precies bedoeld met: tegenstander worden bondgenoten?</h3>
                        <ul style={{ fontSize: '1.05rem', lineHeight: '1.8' }}>
                            <li>Open opstellen voorstellen tot verbetering</li>
                            <li>Maak iedereen probleemeigenaar</li>
                            <li>Bouw aan een actieve community</li>
                        </ul>
                    </div>

                    <div style={{ marginBottom: '40px' }}>
                        <h3 style={{ color: 'var(--ifm-color-primary)', marginBottom: '15px' }}>Benieuwd naar:</h3>
                        <p style={{ fontSize: '1.05rem', lineHeight: '1.7' }}>
                            Kwantificeren van baten (in kennis en bijdragen) vs. kosten (beheer en marketing rondom community)?
                            We behandelen concrete voorbeelden en tools die je direct kunt toepassen.
                        </p>
                    </div>

                    <div style={{ marginTop: '60px', textAlign: 'center' }}>
                        <p style={{ fontSize: '1.1rem', marginBottom: '20px' }}>
                            <strong>Interesse in deze training?</strong>
                        </p>
                        <p style={{ fontSize: '1.1rem', marginBottom: '20px' }}>
                            Voor aanmeldingen en vragen over de training, stuur meteen een bericht via ons <Link to="/contact">contactformulier</Link> en
                            wij komen persoonlijk bij je terug!
                        </p>
                        <p style={{ fontSize: '1.1rem' }}>
                            Wij bieden hiernaast ook andere trainingen aan. Nieuwsgierig? <Link to="/trainingen">Bekijk ze hier</Link>.
                        </p>
                    </div>
                </div>
            </section>

            <ContactTeaser />
            <Socials />
            <Footer />
        </Layout>
    );
}
