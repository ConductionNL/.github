import React from 'react';
import Link from '@docusaurus/Link';
import styles from '../../pages/index.module.css';

function TrainingCard({ title, subtitle, description, image, link = null, background = 'default' }) {
    const cardClassName =
        background === 'yellow'
            ? styles.trainingCard + ' ' + styles.trainingCardYellow
            : styles.trainingCard;

    return (
        <div className={cardClassName}>
            <h3 className={styles.trainingCardTitle}>{title}</h3>
            <div className={styles.trainingCardImage}>
                <img src={image} alt={title} />
            </div>
            {subtitle && <p className={styles.trainingCardSubtitle}>{subtitle}</p>}
            <p className={styles.trainingCardDescription}>{description}</p>
            {link && (
                <Link className={styles.trainingCardButton} to={link}>Meer info</Link>
            )}
        </div>
    );
}

export default function TrainingCardSection({ cards, title }) {
    return (
        <section className={styles.trainingCardSection + ' container margin-vert--lg'}>
            <h2 className={styles.sectionTitle}>{title}</h2>
            <div className={styles.trainingCardGrid}>
                {cards.map((card, index) => (
                    <TrainingCard key={index} {...card} />
                ))}
            </div>
        </section>
    );
}