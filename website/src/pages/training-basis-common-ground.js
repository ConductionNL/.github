import React from 'react';
import Layout from '@theme/Layout';
import Footer from '../components/Footer';
import Socials from '../components/Socials';
import ContactTeaser from '../components/Contact';
import Hero from '../components/Hero';
import styles from './index.module.css';
import Link from '@docusaurus/Link';

export default function TrainingBasisCommonGround() {
    return (
        <Layout title="Training basis Common Ground" description="Training basis Common Ground">
            <Hero
                title="Training basis Common Ground"
                paragraphs={[
                    'Conduction heeft deze training ontwikkeld voor gemeenten of organisaties die vooruit willen met Common Ground. We beginnen met de basiskennis van Common Ground, bespreken ontwikkelingen binnen en buiten de gemeente en formuleren samen met jouw team een concreet advies waar jouw organisatie op door kan bouwen.',
                    'Wil jouw organisatie starten of de volgende stap zetten met Common Ground? Dan is deze training wat voor jullie!',
                    'Heb je vragen over de training of wil je jouw team direct aanmelden?'
                ]}
                image="/img/trainingDetails/basisCGHero.png"
                button={{
                    title: 'Neem hier contact op',
                    link: '/contact'
                }}
            />

            <section className={styles.sectionLight}>
                <div className="container">
                    <h2 className={styles.sectionTitle}>Wat weet je aan het einde van de training</h2>
                    <div className="row">
                        <div className="col col--6">
                            <img src="/img/trainingDetails/CGCheckbox.png" alt="Common Ground" style={{ width: '100%', height: 'auto' }} />
                        </div>
                        <div className="col col--6">
                            <div className={styles.infoBlock}>
                                <ul style={{ listStyle: 'none', paddingLeft: 0 }}>
                                    <li style={{ marginBottom: '20px' }}>
                                        <strong>Basis kennis van Common Ground</strong>
                                    </li>
                                    <li style={{ marginBottom: '20px' }}>
                                        <strong>Common Ground architectuurvisie</strong>
                                        <ul style={{ marginTop: '10px' }}>
                                            <li>API's: alles wat je erover moet weten</li>
                                            <li>Privacy by design</li>
                                            <li>Common Ground standaarden</li>
                                            <li>Verschillende tooling</li>
                                        </ul>
                                    </li>
                                    <li style={{ marginBottom: '20px' }}>
                                        <strong>Common Ground ontwikkelingen binnen en buiten de gemeente</strong>
                                        <ul style={{ marginTop: '10px' }}>
                                            <li>Waar vind je de ontwikkelingen en projecten</li>
                                        </ul>
                                    </li>
                                    <li style={{ marginBottom: '20px' }}>
                                        <strong>Opkomende technologieën en nieuwe uitdagingen</strong>
                                    </li>
                                    <li style={{ marginBottom: '20px' }}>
                                        <strong>Stappen voor jouw organisatie met Common Ground</strong>
                                    </li>
                                </ul>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            <section className={styles.sectionNeutral}>
                <div className="container">
                    <h2 className={styles.sectionTitle}>Praktische zaken en kosten</h2>
                    <ul style={{ fontSize: '1.1rem', lineHeight: '1.8' }}>
                        <li>De training wordt online gegeven en duurt een halve dag</li>
                        <li>Geschikt voor maximaal 5 deelnemers, zodat er genoeg tijd is om in te gaan op specifieke vragen</li>
                        <li>De training wordt persoonlijk gegeven door onze founders</li>
                        <li>Kosten van de training zijn €2500,- (excl. BTW)</li>
                    </ul>
                    <p style={{ marginTop: '20px' }}>
                        Kosten voor de voorbereidingstijd hangen af van uw vraag, neem gerust contact met ons op dan maken we direct een offerte op.
                    </p>
                </div>
            </section>

            <section className={styles.sectionLight}>
                <div className="container">
                    <h2 className={styles.sectionTitle}>Modules Basis Common Ground</h2>

                    <div style={{ marginBottom: '40px' }}>
                        <h3 style={{ color: 'var(--ifm-color-primary)', marginBottom: '15px' }}>Wat is Common Ground?</h3>
                        <p style={{ fontSize: '1.05rem', lineHeight: '1.7' }}>
                            Tijdens de training leggen we uit wat Common Ground is, wat het doel is van Common Ground en de Common Ground ontwerpprincipes.
                            We behandelen het 5-lagen model van Common Ground en het verschil tussen componenten, API's en logica. Ook nemen we de voordelen
                            door van privacy by design (security, AVG en data) voor jouw organisatie. Daarnaast worden de standaarden van Common Ground besproken,
                            wat Haven en Kubernetes zijn en welke tools er zijn die jouw team kan gebruiken om aan de slag te gaan met Common Ground.
                        </p>
                    </div>

                    <div style={{ marginBottom: '40px' }}>
                        <h3 style={{ color: 'var(--ifm-color-primary)', marginBottom: '15px' }}>Common Ground, nu en in de toekomst</h3>
                        <p style={{ fontSize: '1.05rem', lineHeight: '1.7' }}>
                            Er vinden volop ontwikkelingen plaats binnen de Common Ground community. Het is van belang om op de hoogte te zijn van de
                            uitdagingen én de kansen voor jouw organisatie. Tijdens de training bespreken we waar je deze opkomende technologieën en
                            veranderingen kan volgen, zoals de verschillende app stores, welke Common Ground projecten er zijn, de Haal Centraal transitie,
                            maar ook hoe Common Ground zich ontwikkelt buiten gemeenten.
                        </p>
                    </div>

                    <div style={{ marginBottom: '40px' }}>
                        <h3 style={{ color: 'var(--ifm-color-primary)', marginBottom: '15px' }}>Common Ground en jouw organisatie</h3>
                        <p style={{ fontSize: '1.05rem', lineHeight: '1.7' }}>
                            In deze module doen we samen met jouw team een screening om te kijken wat jouw organisatie nodig heeft om de volgende stappen
                            te zetten met Common Ground.
                        </p>
                        <p style={{ fontSize: '1.05rem', lineHeight: '1.7' }}>
                            Hieruit volgt een hands on advies. We kijken welke ontwikkelingen en projecten het beste passen bij jouw organisatie en met
                            welke andere overheidsinstanties en leveranciers samengewerkt kan worden binnen de community. Ook kijken we naar de kansen
                            die er voor jou organisatie liggen, zodat ook jij mee kan gaan met de Common Ground beweging.
                        </p>
                    </div>
                </div>
            </section>

            <section className={styles.sectionNeutral}>
                <div className="container">
                    <h2 className={styles.sectionTitle}>Maak kennis met onze trainers</h2>
                    <div className="row" style={{ marginTop: '40px' }}>
                        <div className="col col--6">
                            <div className={styles.teamMember}>
                                <img src="/img/team/ruben.png" alt="Ruben" style={{ borderRadius: '50%', width: '200px', height: '200px', objectFit: 'cover' }} />
                                <h3>Ruben</h3>
                                <h4 style={{ fontWeight: '600', fontSize: '1.1rem', color: 'var(--ifm-color-primary)' }}>Omdenker en het brein achter de techniek</h4>
                                <p>
                                    Ruben is een omdenker en een bouwer. Vaak weet de angel van een probleem om te buigen naar een oplossing.
                                    Of dat nou gaat over code of community, hij is van vele markten thuis.
                                </p>
                                <Link to="https://www.linkedin.com/in/rubenvanderlaan/" target="_blank" className={styles.teamMemberSocialButton}>
                                    LinkedIn
                                </Link>
                            </div>
                        </div>
                        <div className="col col--6">
                            <div className={styles.teamMember}>
                                <img src="/img/team/matthias.png" alt="Matthias" style={{ borderRadius: '50%', width: '200px', height: '200px', objectFit: 'cover' }} />
                                <h3>Matthias</h3>
                                <h4 style={{ fontWeight: '600', fontSize: '1.1rem', color: 'var(--ifm-color-primary)' }}>Bewaker van de kwaliteit en commercieel</h4>
                                <p>
                                    Matthias kenmerkt zich door zijn interesse in techniek, zijn pragmatische instelling, zijn doorzettingsvermogen
                                    en zijn communicatieve vaardigheden.
                                </p>
                                <Link to="https://www.linkedin.com/in/matthias-decker-92b2981b9/" target="_blank" className={styles.teamMemberSocialButton}>
                                    LinkedIn
                                </Link>
                            </div>
                        </div>
                    </div>

                    <div style={{ marginTop: '60px', textAlign: 'center' }}>
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
