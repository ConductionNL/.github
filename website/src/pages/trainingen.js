import React from 'react';
import Layout from '@theme/Layout';
import Hero from '../components/Hero';
import ContactTeaser from '../components/Contact';
import Socials from '../components/Socials';
import Footer from '../components/Footer';
import TrainingCardSection from '../components/TrainingCard';

export default function Trainingen() {
    const paragraphs = [
        'Conduction heeft veel ervaring opgedaan rondom Common Ground ontwikkeling, beheer van omgevingen en software. Wij hebben daarom trainingen ontwikkeld op deze gebieden. De trainingen zijn niet alleen voor gemeenten en overheden, maar ook voor Common Ground minded leveranciers.', 'Meer weten over onze trainingen. Neem contact op'
    ];

    const cards = [
        {
            title: 'Basis Common Ground',
            subtitle: 'Voor iedereen die wil starten met Common Ground',
            description: 'Een korte introductie in Common Ground. Waar we inzoomen op de principes, voordelen, uitdagingen en lopende projecten.',
            image: '/img/training/basis_common.png',
            link: 'https://www.conduction.nl/training-basis-common-ground/'
        },
        {
            title: 'Architectuur Common Ground',
            subtitle: 'Voor architecten, informatiemanagers en product owners',
            description: 'Met deze training kijken we naar de architectuurprincipes van Common ground en passen we die hands-on toe.',
            image: '/img/training/architectuur.png'
        },
        {
            title: 'API Ontwerpen',
            subtitle: 'Voor developers en architecten',
            description: 'Een technische training waarin we de “good practices” van API ontwikkeling volgens Common Ground behandelen.',
            image: '/img/training/api.png'
        },
        {
            title: 'Open Source Software Development',
            subtitle: 'Voor developers en product owners',
            description: 'Wanneer je open source software wilt ontwikkelen loop je tegen unieke uitdagingen aan. Deze training helpt je de uitdagingen het hoofd te bieden.',
            image: '/img/training/computer.png'
        },
        {
            title: 'Privacy by Design',
            subtitle: 'Voor iedereen',
            description: 'Privacy by design is een denkwijze waarmee je de “privacy arm” systemen kan ontwikkelen. Dit zorgt voor een lagere AVG impact.',
            image: '/img/training/privacy.png'
        },
        {
            title: 'Haven/ Kubernetes',
            subtitle: 'Voor beheerders',
            description: 'Bij deze training kijken we naar laag 0 van het Common Ground model. We duiken in Kubernetes en wat de Haven standaard is en wat het niet is.',
            image: '/img/training/kubernetes.png'
        },
        {
            title: 'DashKube',
            subtitle: 'Voor beheerders en informatiemanagers',
            description: 'Een in depth training in het beheren van je eigen Common Ground ecosysteem door middel van van Dashkube.',
            image: '/img/training/dashkube.png'
        },
        {
            title: 'Tenderen',
            subtitle: 'Voor inkoopmanagers van overheden',
            description: 'Hoe schrijf je nu een goede tender als je een (open source) oplossing wil op basis van Common Ground.',
            image: '/img/training/tenderen.png'
        },
        {
            title: 'NLX',
            subtitle: 'Voor developers, beheerders en informatiemanagers',
            description: 'NLX is de derde laag binnen Common Ground. Deze training gaat in op hoe je dit nu goed toepast in je ecosysteem en in je software oplossing.',
            image: '/img/training/nlx.png'
        },
        {
            title: 'Notificatie, Autorisatie en Logging',
            subtitle: 'Voor developers, informatiemanagers en architecten',
            description: 'Technische deepdive voor developers in de drie core services van Common Ground',
            image: '/img/training/notificatie.png'
        },
        {
            title: 'Verzoeken',
            subtitle: 'Voor developers, informatiemanagers en architecten',
            description: 'Deze training behandeld verzoeken bij klantinteractie. We kijken naar de voordelen van omnichannel verzoeken en behandelen de techniek er achter.',
            image: '/img/training/verzoeken.png'
        },
        {
            title: 'Waardepapieren',
            subtitle: 'Voor iedereen',
            description: 'De training digitale Waardepapieren gaat in op de business case, de techniek en het gebruik van de Waardepapieren oplossing.',
            image: '/img/training/papieren.png'
        },
        {
            title: 'Open Source binnen overheid',
            subtitle: 'Voor iedereen binnen de overheid',
            description: 'Deze training is specifiek ontwikkeld om in te gaan op de huidige ontwikkelingen, de voor- en nadelen en welke doelen Open Source nog meer bereikt binnen de overheid',
            image: '/img/training/computer.png',
            link: 'https://www.conduction.nl/training-open-source-en-overheid/'
        },
        {
            title: 'Hoe te beginnen met Common Ground?',
            subtitle: 'Dit leertraject helpt gemeenten on Common Ground',
            description: 'Voor iedere gemeente die stappen wil maken met Common Ground. Met Conduction als kennispartner ontdekt de gemeente wat Common Ground betekent in haar specifieke situatie. Samen stellen we een roadmap op waarin we Common Ground gaan toepassen en uitgaan vinden wat de uitdagingen van de gemeente zijn. Dit geldt niet alleen voor de techniek maar ook voor veranderend beleid, processen en inrichting van de organisatie.',
            image: '/img/training/hoe_te_beginnen.png',
            link: 'https://www.conduction.nl/hoe-te-beginnen-met-common-ground'
        },
    ];

    return (
        <Layout title="Trainingen" description="Trainingen en advies">
            <Hero title="Trainingen" paragraphs={paragraphs} image="/img/trainingenHero.png" button={{
                title: 'Contact',
                link: '/contact'
            }} />
            <TrainingCardSection cards={cards} title="Alle trainingen" />
            <ContactTeaser />
            <Socials />
            <Footer />
        </Layout>
    );
} 