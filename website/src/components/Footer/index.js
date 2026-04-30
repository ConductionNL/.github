import React from 'react';
import styles from '../../pages/index.module.css';
import { Link } from 'react-router-dom';

export default function Footer() {
    return (
        <footer className={styles.footer}>
            <div className={styles.footerContent + " row container"}>
                <div className={styles.footerContentLeft + " col"}>
                    <p>
                        © {new Date().getFullYear()} Conduction. All Rights Reserved. Made with love by Conduction
                    </p>
                    <p>
                        <Link to="/contact">contact</Link>
                        <span>|</span>
                        <Link to="/privacy">privacy</Link>
                        <span>|</span>
                        <Link to="/kwaliteitsbeleid">kwaliteitsbeleid</Link>
                    </p>
                </div>
                <div className={styles.footerContentRight + " col"}>
                    <div className={styles.certificate}>
                        <img src="/img/2015.png" alt="Certificate 2015" />
                    </div>
                    <div className={styles.certificate}>
                        <img src="/img/2022.png" alt="Certificate 2022" />
                    </div>
                </div>
            </div>
        </footer>
    );
}