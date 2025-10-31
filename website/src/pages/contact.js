import React from 'react';
import Layout from '@theme/Layout';
import ContactTeaser from '../components/Contact';
import Socials from '../components/Socials';
import Footer from '../components/Footer';
import styles from './index.module.css';

export default function Contact() {
    return (
        <Layout title="Contact" description="Neem contact op">
            <div className={styles.contactPageWrapper}>
                <div className={styles.contactPageContent + ' ' + styles.extendedbg}>
                    <div className={'container'}>
                        <ContactTeaser />
                    </div>
                </div>
                <Socials />
                <Footer />
            </div>
        </Layout>
    );
} 