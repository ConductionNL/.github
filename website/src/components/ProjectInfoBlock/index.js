import React from 'react';
import styles from '../../pages/index.module.css';

/*
    title: string
    paragraphs: string[]
    mainImage: string
    partners: string[]  // array of images
*/

export default function ProjectInfoBlock({ title, paragraphs, mainImage, partners, backgroundColor }) {
    return (
        <div className={`${styles.projectInfoBlockContainer} ${backgroundColor === 'light' ? styles.light : styles.neutral}`}>
            <div className={styles.projectInfoBlock + ' container'}>
                <h3 className={styles.sectionTitle}>{title}</h3>
                <div className={styles.projectInfoBlockContent}>
                    {paragraphs.map((paragraph, index) => (
                        <p key={index} dangerouslySetInnerHTML={{ __html: paragraph }} />
                    ))}
                </div>
                <div className={styles.projectInfoBlockImage}>
                    <img src={mainImage} alt={title} />
                </div>
                <div className={styles.projectInfoBlockPartners}>
                    {partners.map((partner, index) => (
                        <img key={index} src={partner} alt={partner} />
                    ))}
                </div>
            </div>
        </div>
    );
}