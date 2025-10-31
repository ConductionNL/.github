import React from 'react';
import Layout from '@theme/Layout';
import Hero from '../components/Hero';
import ProjectInfoBlock from '../components/ProjectInfoBlock';
import ContactTeaser from '../components/Contact';
import Socials from '../components/Socials';
import Footer from '../components/Footer';

export default function Projecten() {
    const paragraphs = [
        'In de afgelopen jaren heeft Conduction samen met verschillende overheidsinstanties en leveranciers gewerkt aan projecten, waarbij volgens de Common Ground principes applicaties en componenten zijn ontwikkeld. Hieronder worden die projecten weergegeven.',
        'Nieuwsgierig naar wat Conduction voor jou kan betekenen?'
    ];


    // Projecten structure
    /*
    title: string
    paragraphs: string[]
    mainImage: string
    partners: string[]  // array of images
    */

    const projecten = [
        {
            title: 'OpenWoo.app',
            paragraphs: ['OpenWoo.app helpt gemeenten om documenten rechtstreeks vanuit hun bronsystemen te ontsluiten en automatisch te publiceren — zónder dat daar een aparte Woo-taakapplicatie voor nodig is.', 'Met deze oplossing krijgen inwoners, journalisten en onderzoekers beter toegang tot overheidsinformatie. Zo voldoet de gemeente niet alleen aan de eisen van de Woo, maar sluit ze ook beter aan bij de informatiebehoefte van de samenleving.', 'OpenWoo.app is gebouwd op de Common Ground-principes en daarmee flexibel in gebruik: gemeenten kiezen zelf welke frontendpartij de data ontsluit. De oplossing is gebaseerd op Nextcloud en volledig open source beschikbaar'],
            mainImage: '/img/beheerCarousel/openWoo.png',
            partners: ['/img/partners/io.webp', '/img/partners/yard.png', '/img/partners/Shift2.png', '/img/partners/bct.png']
        },
        {
            title: 'VNG Softwarecatalogus',
            paragraphs: ['De VNG Softwarecatalogus helpt gemeenten bij het beheren en inzichtelijk maken van hun applicatielandschap. Gemeenten registreren hier welke software ze gebruiken, hoe deze is gekoppeld, welke oplossingen beschikbaar zijn en welke standaarden worden toegepast.', 'Zo ontstaat er een gedeeld overzicht dat samenwerking, inkoop en interoperabiliteit binnen het gemeentelijk domein versterkt.', 'De vernieuwing van de Softwarecatalogus wordt ontwikkeld in opdracht van VNG Realisatie en is gebaseerd op OpenCatalogi. Onderliggend maakt het gebruik van dezelfde modulaire componenten als OpenWoo.app. Dit zorgt voor een samenhangende en herbruikbare infrastructuur, volledig open source.'],
            mainImage: '/img/dashkube.png',
            partners: ['/img/partners/vng.png']
        },
        {
            title: 'OpenRegisters',
            paragraphs: ['OpenRegisters is een krachtige open source-oplossing voor het opslaan, beheren en ontsluiten van gegevens. Gemeenten gebruiken het bijvoorbeeld om een verwerkingenregister of publicatieomgeving op te bouwen — maar de toepassing is veel breder: elk type register of gegevensverzameling kan ermee worden ingericht.', 'Van een gemeentelijk verwerkingsregister tot de ledenadministratie van een sportvereniging: OpenRegisters biedt de flexibiliteit om je eigen structuur en datamodellen samen te stellen.', 'Het platform draait bovenop Nextcloud en wordt gezien als een open source alternatief voor Microsoft Access — maar dan flexibeler, webgebaseerd en volledig koppelbaar met andere toepassingen.', 'OpenRegisters vormt ook de basis onder andere producten zoals OpenWoo.app, OpenCatalogi en de VNG Softwarecatalogus, en is gebouwd op een modulaire infrastructuur die hergebruik en integratie eenvoudig maakt.'],
            mainImage: '/img/beheerCarousel/openRegisters.png',
            partners: ['/img/partners/nextcloud.png']
        },
        {
            title: 'WaardePapieren',
            paragraphs: ['Waardepapieren is een dienst waarbij burgers uittreksels digitaal kunnen opvragen bij de gemeente. Voorheen was de burger altijd genoodzaakt om diverse waardepapieren af te halen bij de gemeente, dat kan nu online!', 'Met waardepapieren is het mogelijk om BRP of woonhistorie uittreksels digitaal aan te vragen en deze vervolgens zelf uit te printen.'],
            mainImage: '/img/waardPapieren.png',
            partners: ['/img/partners/hoorn.png', '/img/partners/harderwijk.png', '/img/partners/buren.png', '/img/partners/haarlem.png', '/img/partners/dimpact.png']
        }
    ];


    return (
        <Layout title="Projecten" description="Onze projecten en innovatie">
            <Hero title="Projecten" paragraphs={paragraphs} image="/img/projectenHero.png" button={{
                title: 'Neem contact op',
                link: '/contact'
            }} />
            {projecten.map((project, index) => (
                <ProjectInfoBlock key={index} title={project.title} paragraphs={project.paragraphs} mainImage={project.mainImage} partners={project.partners} backgroundColor={index % 2 === 0 ? 'light' : 'neutral'} />
            ))}
            <ContactTeaser />
            <Socials />
            <Footer />
        </Layout>
    );
} 