import React from 'react';
import styles from '../../pages/index.module.css';

export default function InfoBlock({ title, sectionColor, imageOnLeft, paragraphs, image }) {
    return (
        <section className={styles[sectionColor]}>
            <div className="container">
                <h2 className={styles.sectionTitle}>{title}</h2>
                <div className={styles.infoSection}>
                    {imageOnLeft && <div className={styles.infoSectionImage}>
                        <img src={image} alt={title} />
                    </div>}
                    <div className={styles.infoSectionText}>
                        {paragraphs.map((paragraph, index) => (
                            <p key={index} dangerouslySetInnerHTML={{ __html: paragraph }} />
                        ))}
                    </div>
                    {!imageOnLeft && <div className={styles.infoSectionImage}>
                        <img src={image} alt={title} />
                    </div>}
                </div>
            </div>
        </section>
    );
}