import React from 'react';
import Layout from '@theme/Layout';
import styles from './index.module.css';
import Footer from '../components/Footer';

export default function Privacy() {
    return (
        <Layout title="Privacy" description="Privacy statement">
            <main className="container margin-vert--lg">
                <div className={styles.privacyTextSection}>
                    <div className={styles.textSectionBlock}>
                        <h2 className={styles.sectionTitle}>Privacy beleid (op basis van de AVG, voortvloeiend uit de Europese Privacy Verordening 2016/679)</h2>
                        <p>Conduction B.V. gebruikt persoonsgegevens alleen voor het doel waarvoor de gegevens zijn opgeslagen. Conduction B.V. deelt persoonsgegevens niet met derden, tenzij dit voor het opslagdoel nodig is. Conduction B.V. bewaart persoonsgegevens niet langer dan nodig is op basis van het opslagdoel van de gegevens. Conduction B.V. houdt met alle mogelijke middelen en maatregelen persoonsgegevens veilig tegen inzage van onbevoegden. Conduction B.V. vraagt toestemming aan relaties voor het opslaan van persoonsgegevens. Conduction B.V. informeert [klanten] over hun rechten ten aanzien van hun persoonsgegevens. Conduction B.V. informeert haar relaties over het doel van de verwerking van persoonsgegevens. Conduction B.V. informeert de relatie indien Conduction B.V. bijzondere handelingen met de persoonsgegevens gaat verrichten.</p>
                    </div>
                    <div className={styles.textSectionBlock}>
                        <h2 className={styles.sectionTitle}>Risico beoordeling (Data Protection Impact Assesment-DPIA)</h2>
                        <p>Risico’s bestaan in het door Conduction B.V. onbedoeld wijzigen, lekken of zoekraken van informatie waardoor schade ontstaat aan de externe belanghebbenden van Conduction B.V. .</p>
                        <p>Tegen dit risico neemt Conduction B.V. de maatregelen in dit privacy beleid of ISMS, voert deze uit en beoordeelt deze op effectiviteit. De procedures van het privacy beleid of ISMS zijn onderwerp van continu onderzoek en verbetering. Alle medewerkers worden bij de veiligheids-procedures betrokken, op de wijzen als in dit privacy beleid of ISMS beschreven.</p>
                    </div>
                    <div className={styles.textSectionBlock}>
                        <h2 className={styles.sectionTitle}>Procedure risico beoordeling</h2>
                        <p>Conduction B.V. reduceert bovenstaande gevaren doordat zij werkt op basis van haar privacy beleid of ISMS. Bij iedere interne audit en management review wordt een risico-beoordeling dataveiligheid uitgevoerd.</p>
                        <p>Buiten het beheer van het privacy beleid of ISMS blijft een rest-risico bestaan. De bekende risico’s voor Conduction B.V. worden via de interne audits en management reviews geanalyseerd. Maatregelen voor die risico’s zijn in het privacy beleid of ISMS opgenomen en worden beheerd en uitgevoerd. Rest-risico’s bestaan uit extreem wijzigende omstandigheden die Conduction B.V. niet voorziet. Die risico’s acht Conduction B.V. onvermijdelijk. Na een onvoorzien incident wordt een nieuwe risico beoordeling uitgevoerd. Eventuele remedies neemt Conduction B.V. in het privacy beleid of ISMS op.</p>
                    </div>
                </div>
            </main>
            <Footer />
        </Layout>
    );
} 