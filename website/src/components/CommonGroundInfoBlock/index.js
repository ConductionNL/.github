import React from 'react';
import Link from '@docusaurus/Link';
import styles from '../../pages/index.module.css';

export default function CommonGroundInfoBlock({ title, description, image, background = 'neutral', button }) {
    const sectionClassName =
        background === 'yellow'
            ? styles.commonGroundSection + ' ' + styles.commonGroundSectionYellow
            : background === 'light'
                ? styles.commonGroundSection + ' ' + styles.commonGroundSectionLight
                : styles.commonGroundSection + ' ' + styles.commonGroundSectionNeutral;

    const contentClassName =
        background === 'yellow'
            ? styles.commonGroundInfoBlockContent + ' ' + styles.commonGroundInfoBlockContentInverted
            : styles.commonGroundInfoBlockContent;

    const buttonClassName =
        background === 'yellow'
            ? styles.commonGroundInfoBlockButton + ' ' + styles.commonGroundInfoBlockButtonInverted
            : styles.commonGroundInfoBlockButton;

    const titleClassName =
        background === 'yellow'
            ? styles.sectionTitle + ' ' + styles.sectionTitleInverted
            : styles.sectionTitle;

    return (
        <section className={sectionClassName}>
            <div className={styles.commonGroundInfoBlock + ' container'}>
                <div className={contentClassName}>
                    <h3 className={titleClassName}>{title}</h3>
                    <p>{description}</p>
                    {button && (
                        <div className={buttonClassName}>
                            <Link to={button.link}>{button.title}</Link>
                        </div>
                    )}
                </div>
                <div className={styles.commonGroundInfoBlockImage}>
                    <img src={image} alt={title} />
                </div>
            </div>
        </section>
    );
}  
