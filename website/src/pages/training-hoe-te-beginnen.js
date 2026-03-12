import React from 'react';
import Layout from '@theme/Layout';
import Footer from '../components/Footer';
import Socials from '../components/Socials';
import ContactTeaser from '../components/Contact';
import Hero from '../components/Hero';
import styles from './index.module.css';
import Link from '@docusaurus/Link';
import InfoBlock from '../components/InfoBlock';

export default function TrainingHoeTeBeginnen() {

    const leertrajectParagraphs = [
        `<ul><li><strong>Basis kennis van Common Ground</strong></li></ul>`,
        `<ul><li><strong>Common Ground architectuurvisie</strong></li></ul>`,
        `API's: alles wat je erover moet weten`,
        `Privacy by design`,
        `Common Ground standaarden (VNG, GEMMA, Internationaal)`,
        `<ul><li><strong>Verschillende tooling</strong></li></ul>`,
        `<ul><li><strong>Common Ground ontwikkelingen binnen- en buiten de gemeente</strong></li></ul>`,
        `Waar vind je de ontwikkelingen en projecten`,
        `<ul><li><strong>Opkomende technologieën en nieuwe uitdagingen</strong></li></ul>`,
        `<ul><li><strong>Stappen voor jouw organisatie met Common Ground</strong></li></ul>`,
        `<ul><li><strong>Bepalen scope leertraject</strong></li></ul>`,
        `Hier wordt gekeken welke vormen van beheer van toepassing zijn voor jullie organisatie.`,
        `Hoe kunnen jullie het datalandschap inrichten volgens Common Ground en leren jullie de middelen beheersen`,
        `<ul><li><strong>Roadmap opstellen om doelen te bereiken</strong></li></ul>`,
        `<ul><li><strong>Ervaring opdoen, van klein naar groot</strong></li></ul>`,
        `<ul><li><strong>Kleine cyclische experimenten aan de hand van de roadmap</strong></li></ul>`,
        `<ul><li><strong>Eerste component naar productie</strong></li></ul>`,
        `<ul><li><strong>Begeleiding van het eerste component naar productiegang.</strong></li></ul>`,
    ]

    const praktischeZakenParagraphs = [
        `<ul><li>De training kan online of op locatie gegeven worden</strong></li></ul>`,
        `<ul><li>Geschikt voor maximaal 8-10 deelnemers, zodat er genoeg tijd is om in te gaan op specifieke vragen</strong></li></ul>`,
        `<ul><li>De training wordt persoonlijk gegeven door onze founders</strong></li></ul>`,
        `<ul><li>Kosten voor de voorbereidingstijd hangen af van uw vraag, neem gerost contact met ons op dan maken we direct een offerte op</strong></li></ul>`,
    ]

    function MeetTheTeam() {
        return (
            <section className={styles.sectionNeutral}>
                <div className="container">
                    <h2 className={styles.sectionTitle}>Maak kennis met onze trainers</h2>
                    <div className="row">
                        <div className="col">
                            <div className={styles.teamMember}>
                                <h3>Ruben</h3>
                                <div className={styles.teamMemberImage}>
                                    <img src="/img/team/ruben.png" alt="Team" />
                                </div>
                                <div className={styles.teamMemberContent}>
                                    <h3 className={styles.teamMemberPosition}>
                                        OMDENKER EN HET BREIN ACHTER DE TECHNIEK
                                    </h3>
                                    <p>Ruben is een omdenker en een bouwer. Hij weet de angel van een probleem om te buigen naar een oplossing voor hetzelfde probleem. Daarbij is hij een echte bouwer, of dat nou gaat over code of een community, hij is van vele markten thuis.</p>
                                    <div className={styles.teamMemberSocials}>
                                        <div className={styles.teamMemberSocialsItem}>
                                            <a className={styles.teamMemberSocialButton} href="https://www.linkedin.com/in/rubenlinde/" target="_blank" rel="noopener noreferrer" aria-label="LinkedIn">
                                                LinkedIn
                                            </a>
                                        </div>
                                        <div className={styles.teamMemberSocialsItem}>
                                            <a className={styles.teamMemberSocialButton} href="mailto:ruben@conduction.nl" target="_blank" rel="noopener noreferrer" aria-label="Email">
                                                Email
                                            </a>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div className="col">
                            <div className={styles.teamMember}>
                                <h3>Matthias</h3>
                                <div className={styles.teamMemberImage}>
                                    <img src="/img/team/matthias.png" alt="Team" />
                                </div>
                                <div className={styles.teamMemberContent}>
                                    <h3 className={styles.teamMemberPosition}>
                                        BEWAKER VAN DE KWALITEIT EN COMMERCIEEL
                                    </h3>
                                    <p>Matthias kenmerkt zich door zijn sterke interesse in techniek, zijn pragmatische instelling, zijn hoge doorzettingsvermogen en zijn goede communicatieve vaardigheden. Matthias komt met ongewone oplossingen voor hardnekkige problemen.</p>
                                    <div className={styles.teamMemberSocials}>
                                        <div className={styles.teamMemberSocialsItem}>
                                            <a className={styles.teamMemberSocialButton} href="https://www.linkedin.com/in/matthiasoliveiro/" target="_blank" rel="noopener noreferrer" aria-label="LinkedIn">
                                                LinkedIn
                                            </a>
                                        </div>
                                        <div className={styles.teamMemberSocialsItem}>
                                            <a className={styles.teamMemberSocialButton} href="mailto:matthias@conduction.nl" target="_blank" rel="noopener noreferrer" aria-label="Email">
                                                Email
                                            </a>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </section>
        );
    }
    return (
        <Layout title="Hoe te beginnen met Common Ground?" description="Hoe te beginnen met Common Ground?">
            <Hero
                title="Hoe te beginnen met Common Ground?"
                paragraphs={[
                    'Conduction heeft deze training ontwikkeld voor gemeenten of organisaties die stappen willen zetten met het leren en implementeren van Common Ground componenten. Common Ground wordt door veel gemeente op dezelfde manier behandeld als pakketsoftware die men op dit moment gewend is. Echter, is Common Ground een ecosysteem waar applicaties (laag 4 en 5) gebruikmaken van dezelfde databronnen (laag 1 en 2). Dit brengt een andere dynamiek op het gebied van governance, beheer en technologie. Om ervaring op te doen met deze aspecten biedt dit leertraject het helpen van het vergaren van die kennis.',
                    'Wil jouw organisatie starten of de volgende stap zetten met Common Ground? Dan is deze training wat voor jullie!',
                    'Heb je vragen over de training of wil je jouw team direct aanmelden?'
                ]}
                image="/img/trainingDetails/basisCGHero.png"
                button={{
                    title: 'Neem hier contact op',
                    link: '/contact'
                }}
            />

            {/* <section className={styles.sectionLight}>
                <div className="container">
                    <h2 className={styles.sectionTitle}>Wat weet je aan het einde van het leertraject</h2>
                    <ul style={{ fontSize: '1.05rem', lineHeight: '1.8' }}>
                        <li><strong>Basis kennis van Common Ground</strong></li>
                        <li><strong>Common Ground architectuurvisie</strong>
                            <ul style={{ marginTop: '10px' }}>
                                <li>API's: alles wat je erover moet weten</li>
                                <li>Privacy by design</li>
                                <li>Common Ground standaarden (VNG, GEMMA, Internationaal)</li>
                            </ul>
                        </li>
                        <li><strong>Verschillende tooling</strong></li>
                        <li><strong>Common Ground ontwikkelingen binnen- en buiten de gemeente</strong>
                            <ul style={{ marginTop: '10px' }}>
                                <li>Waar vind je de ontwikkelingen en projecten</li>
                            </ul>
                        </li>
                        <li><strong>Opkomende technologieën en nieuwe uitdagingen</strong></li>
                        <li><strong>Stappen voor jouw organisatie met Common Ground</strong></li>
                        <li><strong>Bepalen scope leertraject</strong>
                            <ul style={{ marginTop: '10px' }}>
                                <li>Hier wordt gekeken welke vormen van beheer van toepassing zijn voor jullie organisatie</li>
                                <li>Hoe kunnen jullie het datalandschap inrichten volgens Common Ground en leren jullie de middelen beheersen</li>
                            </ul>
                        </li>
                        <li><strong>Roadmap opstellen om doelen te bereiken</strong></li>
                        <li><strong>Ervaring opdoen, van klein naar groot</strong>
                            <ul style={{ marginTop: '10px' }}>
                                <li>Kleine cyclische experimenten aan de hand van de roadmap</li>
                            </ul>
                        </li>
                        <li><strong>Eerste component naar productie</strong>
                            <ul style={{ marginTop: '10px' }}>
                                <li>Begeleiding van het eerste component naar productiegang</li>
                            </ul>
                        </li>
                    </ul>
                </div>
            </section> */}
            <InfoBlock title="Wat weet je aan het einde van het leertraject" sectionColor="sectionLight" imageOnLeft={false} paragraphs={leertrajectParagraphs} image="/img/trainingDetails/CGCheckbox.png" />
            <InfoBlock title="Modules Leertraject Common Ground" sectionColor="sectionLight" imageOnLeft={false} paragraphs={praktischeZakenParagraphs} image="/img/trainingDetails/ProgrammerYellow.png" />

            <section className={styles.sectionLight}>
                <div className="container">
                    <h2 className={styles.sectionTitle}>Modules Leertraject Common Ground</h2>

                    <div style={{ marginBottom: '60px', display: 'flex', gap: '40px', alignItems: 'center' }}>
                        <div style={{ flex: '1' }}>
                            <h3 style={{ color: 'var(--ifm-color-primary)', marginBottom: '15px' }}>Dag 1 – Wat is Common Ground?</h3>
                            <p style={{ fontSize: '1.05rem', lineHeight: '1.7' }}>
                                Tijdens de eerste dag leggen we uit wat Common Ground is, wat het doel is van Common Ground en de Common Ground ontwerpprincipes.
                                We behandelen het 5-lagen model van Common Ground en het verschil tussen componenten, API's en logica. Ook nemen we de voordelen
                                door van privacy by design (security, AVG en data) voor jouw organisatie. Daarnaast worden de standaarden van Common Ground besproken,
                                wat Haven en Kubernetes zijn en welke tools er zijn die jouw team kan gebruiken om aan de slag te gaan met Common Ground
                            </p>
                        </div>
                        <div style={{ flex: '0 0 450px' }}>
                            <img
                                src="/img/trainingDetails/ProgrammerYellow.png"
                                alt="Common Ground Dag 1"
                                style={{ width: '100%', height: 'auto', borderRadius: '8px' }}
                            />
                        </div>
                    </div>

                    <div style={{ marginBottom: '60px', display: 'flex', gap: '40px', alignItems: 'center' }}>
                        <div style={{ flex: '1' }}>
                            <h3 style={{ color: 'var(--ifm-color-primary)', marginBottom: '15px' }}>Common Ground en jouw organisatie</h3>
                            <p style={{ fontSize: '1.05rem', lineHeight: '1.7' }}>
                                Nu dat we weten wat Common Ground is, en wat het niet is, kan de volgende stap gemaakt worden. Jullie organisatie stelt samen met
                                de professionals van Conduction (leer)doelen of vragen op in meerdere sessies.
                            </p>
                            <p style={{ fontSize: '1.05rem', lineHeight: '1.7', marginTop: '15px' }}>Denk hierbij aan doelen of vragen zoals:</p>
                            <ul style={{ fontSize: '1.05rem', lineHeight: '1.8' }}>
                                <li>Kan ik zelf Technisch applicatiebeheer doen?</li>
                                <li>Functioneel beheer op Common Ground-applicaties. Hoe werkt dat?</li>
                                <li>Hoe begrijp ik als Kubernetes en Haven?</li>
                            </ul>
                            <p style={{ fontSize: '1.05rem', lineHeight: '1.7', marginTop: '15px' }}>
                                Verder wordt er een roadmap opgemaakt om de leerdoelen te behalen.
                            </p>
                        </div>
                        <div style={{ flex: '0 0 450px' }}>
                            <img
                                src="/img/trainingDetails/CGCheckbox.png"
                                alt="Common Ground en jouw organisatie"
                                style={{ width: '100%', height: 'auto', borderRadius: '8px' }}
                            />
                        </div>
                    </div>

                    <div style={{ marginBottom: '40px', display: 'flex', gap: '40px', alignItems: 'center' }}>
                        <div style={{ flex: '1' }}>
                            <h3 style={{ color: 'var(--ifm-color-primary)', marginBottom: '15px' }}>Common Ground in productie</h3>
                            <p style={{ fontSize: '1.05rem', lineHeight: '1.7' }}>
                                In de laatste module doen jullie eerst ervaring door middel van cyclische experimenten op basis van de eerder opgestelde roadmap.
                                Er worden applicaties geselecteerd en geïnstalleerd onder begeleiding van Conduction. Deze applicaties hebben nog geen productiegang,
                                om het opdoen van ervaring in deze fase stressvrij te houden.
                            </p>
                            <p style={{ fontSize: '1.05rem', lineHeight: '1.7', marginTop: '15px' }}>
                                Na het behalen van de leerdoelen kan er overgegaan worden tot het implementeren van Common Ground componenten in productie.
                                Conduction begeleidt jullie organisatie met het productie-klaarmaken van de componenten en de (beheer)organisatie.
                            </p>
                        </div>
                        <div style={{ flex: '0 0 450px' }}>
                            <img
                                src="/img/training/computer.png"
                                alt="Common Ground in productie"
                                style={{ width: '100%', height: 'auto', borderRadius: '8px' }}
                            />
                        </div>
                    </div>
                </div>
            </section>

            {/* <section className={styles.sectionNeutral}>
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
                            Voor aanmeldingen en vragen over dit leertraject, stuur meteen een bericht via ons <Link to="/contact">contactformulier</Link> en
                            wij komen persoonlijk bij je terug!
                        </p>
                        <p style={{ fontSize: '1.1rem' }}>
                            Wij bieden hiernaast ook andere trainingen aan. Nieuwsgierig? <Link to="/trainingen">Bekijk ze hier</Link>.
                        </p>
                    </div>
                </div>
            </section> */}
            <MeetTheTeam />
            <ContactTeaser />
            <Socials />
            <Footer />
        </Layout>
    );
}
