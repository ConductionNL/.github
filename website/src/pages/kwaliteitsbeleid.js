import React from 'react';
import Layout from '@theme/Layout';
import styles from './index.module.css';
import Footer from '../components/Footer';

export default function Kwaliteitsbeleid() {
    return (
        <Layout title="Kwaliteitsbeleid" description="Kwaliteitsbeleid">
            <main className="container margin-vert--lg">
                <h2 className={styles.sectionTitle}>Beleidsverklaring kwaliteitsmanagementsysteem Conduction</h2>
                <div className={styles.textSectionContent}>
                    <span className={styles.cursive}>Januari 2025</span>

                    <p>Conduction, opgericht in 2018, streeft naar een betere digitale wereld door democratische, inclusieve en transparante software te ontwikkelen volgens de Common Ground principes. Als Digital Socials richten we ons op het creëren van digitale oplossingen voor maatschappelijke vraagstukken, met ‘Tech to serve people’ als leidraad.</p>

                    <p>Onze missie is een digitale wereld te realiseren die fair, duurzaam en toegankelijk is voor iedereen. Dit doen we door democratische, inclusieve en transparante oplossingen te ontwikkelen met eerlijke verdienmodellen. Onze focus ligt op het bouwen van software en applicaties voor overheden, waarbij de mens centraal staat.</p>

                    <p>Kwaliteit en informatieveiligheid zijn essentieel voor ons. We streven naar voortdurende verbetering van onze dienstverlening volgens de Plan-Do-Check-Act cyclus. Actieve betrokkenheid bij onze omgeving, partners en stakeholders, samen met proactieve inspanningen voor nieuwe dienstverlening, verbeterde kwaliteit en informatiebeveiliging, vormen de kern van ons beleid.</p>

                    <p>Ons kwaliteits- en informatieveiligheidssysteem, conform ISO 9001:2015 en ISO 27001:2022, is ontworpen om te waarborgen dat:</p>
                    <ol style={{ listStyleType: 'disc' }}>
                        <li>Werkmethoden geïdentificeerd en gedocumenteerd zijn voor duidelijkheid onder medewerkers.</li>

                        <li>Processen doeltreffend worden uitgevoerd en beheerst, met aandacht voor risico’s.</li>

                        <li>Middelen beschikbaar zijn en processen worden bewaakt, gemeten, geanalyseerd en indien mogelijk verbeterd.</li>

                        <li>Nieuwe medewerkers snel inzicht krijgen in de werkwijzen.</li>

                        <li>Potentiële klanten inzicht hebben in ons kwaliteitsmanagementsysteem.</li>

                        <li>We voldoen aan wettelijke en overheidsverplichtingen.</li>
                    </ol>
                    <p>We zijn als partners verantwoordelijk voor de uitvoering van het beleid en zorgen ervoor dat de organisatie over de mensen, informatie, middelen en materialen beschikt om het kwaliteitsbeleid te kunnen realiseren. We pakken kansen en mitigeren risico’s. Dit delen we met onze medewerkers en laten hen hier zo veel mogelijk in mee denken. We maken tijd vrij voor onszelf, de interne auditors en medewerkers.</p>

                    <p>De scope van het kwaliteits- en informatieveiligheidssysteem betreft productontwikkeling, beheer/abonnementen, training en advies.</p>

                    <p>Kwaliteit, informatiebeveiliging, continue evaluatie en klanttevredenheid staan centraal bij Conduction. Op 24 juli 2025 zijn de certificaten voor ISO 9001:2015 en ISO 27001:2022 verkregen.</p>

                    <p>Voor meer informatie over ons kwaliteits- en informatieveiligheidssysteem kunt u contact met ons opnemen via het contactformulier.</p>
                </div>
                <div className={styles.documentContainer}>
                        <div className={styles.documentItem}>
                            <img src="/img/certificates/2015.png" alt="ISO 9001:2015" />
                        </div>
                        <div className={styles.documentItem}>
                            <img src="/img/certificates/2022.png" alt="ISO 27001:2022" />
                        </div>
                    </div>
            </main>
            <Footer />
        </Layout>
    );
} 