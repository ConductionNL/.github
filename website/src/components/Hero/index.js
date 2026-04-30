import React from 'react';
import clsx from 'clsx';
import Link from '@docusaurus/Link';
import styles from '../../pages/index.module.css';

export default function Hero({ title, subtitle, image, paragraphs, button, primary = true }) {
    return (
        <header className={clsx('hero hero--primary', styles.heroBanner, !primary && styles.heroBannerInverted)}>
            <div className={styles.heroContainer + ' container'}>
                <div className={styles.heroContent}>
                    <h1 className={clsx(styles.heroTitle, !primary && styles.heroTitleInverted)}>{title}</h1>
                    {subtitle && (
                        <h5 className={styles.heroSubtitle}>
                            {subtitle}
                        </h5>
                    )}
                    {paragraphs.map((paragraph, index) => (
                        <p
                            className={clsx(styles.heroParagraph, !primary && styles.heroParagraphInverted)}
                            key={index}
                            dangerouslySetInnerHTML={{ __html: paragraph }}
                        />
                    ))}
                    {button && (
                        <div className={styles.buttons}>
                            <Link className={clsx(styles.primaryHeroLink, !primary && styles.primaryHeroLinkInverted)} to={button.link || '#'}>
                                {button.title}
                            </Link>
                        </div>
                    )}
                </div>
                <div className={styles.heroImage}>
                    <img src={image} alt={title} />
                </div>
            </div>
        </header>
    );
}