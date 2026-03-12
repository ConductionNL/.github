import React from 'react';
import Layout from '@theme/Layout';
import Hero from '../components/Hero';
import CommonGroundInfoBlock from '../components/CommonGroundInfoBlock';
import ContactTeaser from '../components/Contact';
import Socials from '../components/Socials';
import Footer from '../components/Footer';

export default function CommonGround() {
    const paragraphs = [
        'Gemeenten hebben een nieuwe, moderne, gezamenlijke informatievoorziening nodig voor het uitwisselen van gegevens. Want het huidige stelsel voor gegevensuitwisseling maakt het lastig om snel en flexibel te vernieuwen, te voldoen aan privacywetgeving en efficiënt om te gaan met data. Dat staat de verbetering van de gemeentelijke dienstverlening in de weg. Dus tijd voor een nieuwe beweging: Common Ground werd geboren, waarbij hervorming van de huidige gemeentelijke informatievoorziening, deelbaarheid, data bij de bron en vooral de burger centraal staat.',
        'Meer weten wat Conduction voor jouw gemeente kan betekenen?',
    ];

    const infoBlocks = [
        {
            title: 'Conduction <3 Common Ground',
            description: 'Wij geloven in online gemeenschappen en samen organiseren. Wij geloven in delen, duurzaamheid en transparantie. Vanuit deze gedachte zijn we ook toegetreden tot het Common Ground initiatief van de Nederlandse Gemeenten. Binnen dit initiatief staat samenwerking en publiek eigenaarschap centraal. Sinds 3 Juli 2019 zijn wij ook toegetreden tot het groeipact Common Ground. Met het ondertekenen van dit convenant proberen wij een actieve bijdrage te leveren aan het succes van Common Ground. Dit doen wij door onze techniek volgens de Common Ground principes te ontwikkelen.',
            image: '/img/commonGround/commonGround0.png',
            background: 'yellow'
        },
        {
            title: 'Onze successen',
            description: 'In de afgelopen jaren heeft Conduction, als ontwikkelpartij, in partnerschap met overheidsorganisaties meegewerkt aan verschillende innovatieprojecten. De applicaties zijn ontwikkeld volgens de Common Ground principes en open source beschikbaar en deelbaar. Benieuwd naar onze projecten?',
            image: '/img/commonGround/commonGround1.png',
            background: 'neutral',
            button: {
                title: 'Lees meer',
                link: '/projecten'
            }
        },
        {
            title: 'Advisering',
            description: 'De expertise die Conduction heeft bieden wij ook aan in de vorm van documentatie, tutorials of adviesgesprekken. Onze gespecialiseerde vaardigheden binnen de IT delen wij graag om tot oplossingen te komen. Een afspraak voor een vrijblijvend gesprek is altijd mogelijk.',
            image: '/img/commonGround/commonGround2.png',
            background: 'light',
            button: {
                title: 'Contact',
                link: '/contact'
            }
        },
        {
            title: 'Trainingen',
            description: 'Conduction heeft veel ervaring opgedaan rondom Common Ground ontwikkeling, beheer van omgevingen en software. Wij hebben daarom trainingen ontwikkeld op deze gebieden. De trainingen zijn niet alleen voor gemeenten en overheden, maar ook voor Common Ground minded leveranciers.',
            image: '/img/commonGround/commonGround3.png',
            background: 'neutral',
            button: {
                title: 'Lees meer',
                link: '/trainingen'
            }
        },
        {
            title: 'Development',
            description: 'Conduction ontwikkelt open source software op basis van Common Ground en moderne standaarden. Van maatwerk tot modulaire componenten: we bouwen oplossingen die passen bij de behoeften van gemeenten en publieke organisaties. Onze ervaring zetten we graag in voor jouw project of productidee.',
            image: '/img/commonGround/commonGround4.png',
            background: 'light',
            button: {
                title: 'Lees meer',
                link: '/projecten'
            }
        },
    ]

    return (
        <Layout title="Common Ground" description="Common Ground principes">
            <Hero title="Common Ground" paragraphs={paragraphs} image="/img/commonGroundHero.png" primary={false} button={{
                title: 'Neem contact op',
                link: '/contact'
            }} />
            <main>
                {infoBlocks.map((block, index) => (
                    <CommonGroundInfoBlock key={index} {...block} />
                ))}
            </main>
            <ContactTeaser />
            <Socials />
            <Footer />
        </Layout>
    );
} 