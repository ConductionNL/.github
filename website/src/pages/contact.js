import React from 'react';
import Layout from '@theme/Layout';
import ContactTeaser from '../components/Contact';
import Socials from '../components/Socials';
import Footer from '../components/Footer';
import styles from './index.module.css';

export default function Contact() {
    return (
        <Layout title="Contact" description="Neem contact op">
            <div className={styles.extendedbg}>
                <div className={styles.extendedbg + ' container'}>
                    <ContactTeaser />
                </div>
                <Socials />
                <Footer />
            </div>
        </Layout>
    );
} 