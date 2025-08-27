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
import InfoBlock from '../components/InfoBlock';
import Carousel from '../components/Carousel';
import styles from './index.module.css';

export default function Beheer() {
    const { siteConfig } = useDocusaurusContext();

    const cards = [
        {
            title: 'Uw eigen private cloud',
            description: 'Om uw Common Ground applicaties en componenten te installeren richten wij voor u een eigen private cloud in volgens het <a href="https://haven.commonground.nl/">Haven principe</a>. Hierbij ontzorgen wij met de implementatie, ondersteuning en onderhoud, zodat u zekerheid heeft van een supportovereenkomst voor het beheer van uw omgeving.',
        },
        {
            title: 'Aangepast op uw behoefte',
            description: 'De eisen tot de infrastructuur voor uw omgeving worden in grote mate bepaald door het aantal componenten en de intensiteit van het gebruik. Dit betekent dat u zelfs kunt bepalen of uw cloud inhouse of extern draait.',
        },
        {
            title: 'Nextcloud',
            description: 'Nextcloud, het Europese open source alternatief voor Microsoft 365. Wij leveren een Nextcloud-omgeving op maat, die voldoet aan Common Ground-principes en volledig onder eigen regie draait. U kiest zelf of u deze omgeving lokaal, in de cloud of in een datacenter laat hosten — zonder vendor lock-in.',
        },
        {
            title: 'Eén aanspreekpunt',
            description: 'Met onze beheer propositie biedt Conduction één aanspreekpunt voor software, installatie en beheer. Hierdoor heeft u één aanspreekpunt voor support voor alles. Er is geen onduidelijkheid over bij wie de verantwoordelijkheid ligt als er issues optreden. Alles valt binnen één Service Level Agreement.',
        }]

    const applicatiesParagraphs = [
        'Alle Common Ground applicaties kunnen in beheer worden gebracht op Nextcloud zolang ze voldoen aan de <a href="https://commonground.nl/cms/view/12f73f0d-ae26-4021-ba52-849eef37d11f/de-common-ground-principes">standaarden</a>. Ook niet- Common Ground applicaties kunnen op Nextcloud draaien. Deze worden met maatwerk passend gemaakt.',
        'Hieronder staan een aantal voorbeeld applicaties die op Nextcloud kunnen draaien:'
    ]

    const dashKubeParagraphs = [
        'DashKube is een Kubernetes georiënteerd dashboard dat organisaties en ontwikkelaars helpt om eenvoudig een Kubernetes-omgeving op te zetten en te configureren. Door de Kubernetes-management tool is het niet meer nodig Kubernetes te leren en is je ecosysteem binnen no time up and running. Voor meer informatie bezoek <a href="https://www.dashkube.com/">DashKube</a>.',
    ]

    const slides = [
        {
            title: 'OpenWoo.app',
            description: 'Geef inwoners, journalisten en onderzoekers toegang tot wat ze zoeken. OpenWoo.app ontsluit overheidsinformatie automatisch en betrouwbaar.',
            image: '/img/beheerCarousel/openWoo.png',
            link: 'https://openwoo.app'
        },
        {
            title: 'OpenCatalogi',
            description: 'Grip op je digitale infrastructuurbegint bij overzicht. OpenCatalogi maakt applicaties en koppelingen inzichtelijk en herbruikbaar.',
            image: '/img/beheerCarousel/openCatalogi.png',
            link: 'https://opencatalogi.nl'
        },
        {
            title: 'OpenRegisters',
            description: 'OpenRegisters is de flexibele oplossing voor elk type gegevensregister. Van gemeentelijke verwerkingen tot verenigingsleden: alles gestructureerd en beheersbaar.',
            image: '/img/beheerCarousel/openRegisters.png',
            link: 'https://openregisters.nl'
        },
        {
            title: 'Nextcloud',
            description: 'Nextcloud biedt een veilige, uitbreidbare infrastructuur voor publieke diensten. Ideaal voor databeheer, koppelingen en herbruikbare applicaties.',
            image: '/img/beheerCarousel/nextCloud.png',
            link: 'https://nextcloud.com'
        },
        {
            title: 'Open Webconcept',
            description: 'Binnen het Open Webconcept ontwikkelen gemeenten samen online toepassingen en dataservices.',
            image: '/img/beheerCarousel/openWebconcept.png',
            link: 'https://openwebconcept.nl'
        }
    ]
    
    return (
        <Layout title={siteConfig.title} description="Conduction | Beheer">
            <main>
                <Hero title="Beheer" subtitle="Product:" paragraphs={['Uw gemeente wil graag aan de slag met Common Ground, of wil een Common Ground applicatie gebruiken. Maar u heeft nog geen ervaring met kubernetes en of het draaien van Common Ground applicaties? Geen probleem, we ontzorgen u van A tot Z en verzorgen zowel het beheer van uw omgevingen, certificaten als het installeren en onderhouden van componenten en applicaties. Zo bent u snel online zonder de zorgen. Wilt u later de omgeving in eigen beheer? Geen probleem, wij dragen de omgeving graag aan u over.', 'Wil je weten of de Nextcloud iets voor jouw gemeente is?']} image="/img/beheerHero.png" button={{
                    title: 'Neem hier contact op',
                    link: '/contact'
                }} />
                <CardsSection title="Beheer goed geregeld" image="/img/beheer-info.png" cards={cards} cols={2}/>
                <InfoBlock title="Applicaties" sectionColor="sectionNeutral" imageOnLeft={false} paragraphs={applicatiesParagraphs} image="/img/applicaties.png" />
                <Carousel slides={slides} autoPlayMs={5000} />
                <InfoBlock title="DashKube" sectionColor="sectionLight" imageOnLeft={false} paragraphs={dashKubeParagraphs} image="/img/dashkube.png" />
                <ContactTeaser />
                <Socials />
                <Footer />
            </main>
        </Layout>
    );
} 