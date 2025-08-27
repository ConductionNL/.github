import React, { useState, useRef } from 'react';
import clsx from 'clsx';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';
import Column from '../components/Column';
import Columns from '../components/Columns';
import Footer from '../components/Footer';
import Socials from '../components/Socials';
import styles from './index.module.css';
import Hero from '../components/Hero';

function OnzePijlers() {
    return (
        <section className={styles.sectionLight}>
            <div className="container">
                <h2 className={styles.sectionTitle}>Onze pijlers</h2>
                <div className="row">
                    <div className="col">
                        <div className={styles.infoBlock + ' ' + styles.pijler}>
                            <img src="/img/pijlers/samen.png" className={styles.whatWeDoImage} alt="Public Tech" />
                            <h3>Samen</h3>
                            <p>
                                Wij geloven in de kracht van samen organiseren, daarom ontwikkelen wij het liefst samen. Om zo een idee, droom of ideaal op de beste manier vorm te kunnen geven.
                            </p>
                        </div>
                        <div className={styles.infoBlock + ' ' + styles.pijler}>
                            <img src="/img/pijlers/duurzaam.png" className={styles.whatWeDoImage} alt="Public Tech" />
                            <h3>Duurzaam en Innovatief</h3>
                            <p>
                                Alles wat wij maken sluit aan op de behoefte van nu, maar is voorbereid op de toekomst, dat wil zeggen: flexibel genoeg om mee te gaan op bewegingen (on- en offline) van de toekomst.
                            </p>
                        </div>
                    </div>
                    <div className="col">
                        <div className={styles.infoBlock + ' ' + styles.pijler}>
                            <img src="/img/pijlers/open.png" className={styles.whatWeDoImage} alt="Public Tech" />
                            <h3>Open</h3>
                            <p>
                                Alles wat wij ontwikkelen is open source, voor iedereen te gebruiken. Wij geven (onze techniek) graag terug aan de community, zodat anderen er ook mee aan de slag kunnen en mooie concepten kunnen ontwikkelen.
                            </p>
                        </div>
                        <div className={styles.infoBlock + ' ' + styles.pijler}>
                            <img src="/img/pijlers/verantwoord.png" className={styles.whatWeDoImage} alt="Public Tech" />
                            <h3>Verantwoord</h3>
                            <p>
                                Op een bewuste en verantwoorde wijze ontwikkelen en ondernemen staat bij ons hoog in het vaandel. Transparantie en eerlijkheid zijn daarbij key, dus daar houden wij ons aan 🙂
                            </p>
                        </div>
                    </div>
                </div>
                <div className={styles.contentButton}>
                    <Link to="/over-ons">NEEM CONTACT OP</Link>
                </div>
            </div>
        </section>
    );
}

function MeetTheTeam() {
    return (
        <section className={styles.sectionNeutral}>
            <div className="container">
                <h2 className={styles.sectionTitle}>Meet the team</h2>
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
                            <h3>Marleen</h3>
                            <div className={styles.teamMemberImage}>
                                <img src="/img/team/marleen.png" alt="Team" />
                            </div>
                            <div className={styles.teamMemberContent}>
                                <h3 className={styles.teamMemberPosition}>
                                    CREATIEF. VERBINDEND EN HOUDT IEDEREEN SCHERP
                                </h3>
                                <p>Marleen is onderzoekend. Met een kleine dosis technical skills, een onuitputtelijke nieuwsgierigheid en een creatieve insteek, onderzoekt zij een vraagstuk/de markt. Om zo alle mogelijkheden te kunnen benutten die tot (online) groei en verbinding kunnen leiden.</p>
                                <div className={styles.teamMemberSocials}>
                                    <div className={styles.teamMemberSocialsItem}>
                                        <a className={styles.teamMemberSocialButton} href="https://www.linkedin.com/in/marleen-romijn-45a45054/" target="_blank" rel="noopener noreferrer" aria-label="LinkedIn">
                                            LinkedIn
                                        </a>
                                    </div>
                                    <div className={styles.teamMemberSocialsItem}>
                                        <a className={styles.teamMemberSocialButton} href="mailto:marleen@conduction.nl" target="_blank" rel="noopener noreferrer" aria-label="Email">
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
                <div className="row">
                    <div className="col">
                        <div className={styles.teamMember}>
                            <h3>Robert</h3>
                            <div className={styles.teamMemberImage}>
                                <img src="/img/team/robert.png" alt="Team" />
                            </div>
                            <div className={styles.teamMemberContent}>
                                <h3 className={styles.teamMemberPosition}>
                                    OBSERVANT. DEVELOPER MET SCHERPE ZINTUIGEN
                                </h3>
                                <p>Robert is een toegewijde developer en er ontgaat hem niks. Puzzelen met code en tot een gerichte oplossing komen, daar wordt hij heel blij van.</p>
                                <div className={styles.teamMemberSocials}>
                                    <div className={styles.teamMemberSocialsItem}>
                                        <a className={styles.teamMemberSocialButton} href="https://www.linkedin.com/in/robert-zondervan-21ab85193/" target="_blank" rel="noopener noreferrer" aria-label="LinkedIn">
                                            LinkedIn
                                        </a>
                                    </div>
                                    <div className={styles.teamMemberSocialsItem}>
                                        <a className={styles.teamMemberSocialButton} href="mailto:robert@conduction.nl" target="_blank" rel="noopener noreferrer" aria-label="Email">
                                            Email
                                        </a>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div className="col">
                        <div className={styles.teamMember}>
                            <h3>Wilco</h3>
                            <div className={styles.teamMemberImage}>
                                <img src="/img/team/wilco.png" alt="Team" />
                            </div>
                            <div className={styles.teamMemberContent}>
                                <h3 className={styles.teamMemberPosition}>
                                    TEAMPLAYER
                                </h3>
                                <p>Wilco houdt van programmeren, oplossingen bedenken en van mensen (verder) helpen. Hij combineert die twee dingen binnen het team als vanzelf.</p>
                                <div className={styles.teamMemberSocials}>
                                    <div className={styles.teamMemberSocialsItem}>
                                        <a className={styles.teamMemberSocialButton} href="https://www.linkedin.com/in/wilco-louwerse-ba81bb139/" target="_blank" rel="noopener noreferrer" aria-label="LinkedIn">
                                            LinkedIn
                                        </a>
                                    </div>
                                    <div className={styles.teamMemberSocialsItem}>
                                        <a className={styles.teamMemberSocialButton} href="mailto:wilco@conduction.nl" target="_blank" rel="noopener noreferrer" aria-label="Email">
                                            Email
                                        </a>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div className="col">
                        <div className={styles.teamMember}>
                            <h3>Barry</h3>
                            <div className={styles.teamMemberImage}>
                                <img src="/img/team/barry.png" alt="Team" />
                            </div>
                            <div className={styles.teamMemberContent}>
                                <h3 className={styles.teamMemberPosition}>
                                    AANPAKKER. DEVELOPER DIE VAN AANPAKKEN WEET
                                </h3>
                                <p>Barry is nieuwsgierig en open. Hij heeft een enorme drive. He gets things done!</p>
                                    <div className={styles.teamMemberSocials}>
                                    <div className={styles.teamMemberSocialsItem} />
                                    <div className={styles.teamMemberSocialsItem}>
                                        <a className={styles.teamMemberSocialButton} href="mailto:barry@conduction.nl" target="_blank" rel="noopener noreferrer" aria-label="Email">
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

function JoinUs() {
    const [cvFile, setCvFile] = useState(null);
    const [description, setDescription] = useState('');
    const fileInputRef = useRef(null);
    const maxDescriptionLength = 180;
    const handleFileChange = (e) => {
        const file = e.target.files && e.target.files[0];
        setCvFile(file || null);
    };
    const handleDescriptionChange = (e) => {
        setDescription(e.target.value);
    };
    return (
        <section className={styles.sectionPrimary}>
            <div className="container">
                <div className="row">
                    <div className={styles.contactText}>
                        <h5 className={styles.subtitle}>
                            CONDUCTION BLAUW PAST BIJ JOU!
                        </h5>
                        <h2 className={styles.sectionTitle + ' ' + styles.sectionTitleInverted}>Join us</h2>
                        <p>
                            Wij zijn altijd op zoek naar gedreven, originele vakfanaten, pioniers en creatievelingen (to be).
                        </p>
                        <p>
                            Voel je je aangesproken? Neem vooral contact met ons op! 🙂
                        </p>
                    </div>
                    <div className="col">
                        <form className={styles.contactForm} onSubmit={(e) => { if (!cvFile) { e.preventDefault(); } }}>
                            <label>Naam <span className={styles.required}>*</span></label>
                            <input type="text" placeholder="Bijvoorbeeld: Witte de Wit" required />
                            <label>E-mail Addres <span className={styles.required}>*</span></label>
                            <input type="email" placeholder="E.g. john@doe.com" required />
                            <label>Telefoon nummer</label>
                            <input type="tel" placeholder="E.g. +1 300400500" />
                            <label>Omschrijving</label>
                            <textarea placeholder="Beschrijf kort wie je bent en waar we je mee zouden kunnen helpen" value={description} onChange={handleDescriptionChange} maxLength={maxDescriptionLength} />
                            <div className={styles.charCounter}>{description.length}/{maxDescriptionLength}</div>
                            <label className={styles.fileInputLabel}>
                                <input type="file" ref={fileInputRef} className={styles.fileInput} accept=".pdf" onChange={handleFileChange} required />
                                <span>Upload CV</span>
                            </label>
                            {cvFile && (
                                <div className={styles.fileItem}>
                                    <div className={styles.fileItemName}>{cvFile.name}</div>
                                    <div className={styles.fileItemMeta}>{(cvFile.size / 1024).toFixed(1)} KB</div>
                                    <button type="button" onClick={() => { if (fileInputRef.current) { fileInputRef.current.value = ''; } setCvFile(null); }} aria-label="Verwijder bestand">×</button>
                                </div>
                            )}
                            <button type="submit">Verstuur bericht</button>
                        </form>
                    </div>
                </div>
            </div>
        </section>
    );
}

export default function OverOns() {
    const { siteConfig } = useDocusaurusContext();
    const paragraphs = [
        'Conduction is een idealistisch IT-bedrijf dat helpt bij het tot stand brengen van goede ideeën en mooie initiatieven. Wij zetten ons in om de digitale wereld te verbeteren, waarbij mens en community altijd centraal staan. Hierom rust onze techniek op de volgende vier pijlers:',];

    return (
        <Layout title={siteConfig.title} description="Conduction | Over ons">
            <Hero title="Wie zijn wij?" paragraphs={paragraphs} image="/img/mainHero.png" />
            <main>
                <OnzePijlers />
                <MeetTheTeam />
                <JoinUs />
                <Socials />
                <Footer />
            </main>
        </Layout>
    );
} 