import React from 'react';
import styles from '../../pages/index.module.css';
import Link from '@docusaurus/Link';

export default function CardsSection({ title, image, cards, cols = 1 }) {
    const toHtml = (source) => {
        if (!source) return '';
        let html = String(source);
        html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2">$1</a>');
        html = html.replace(/<\s*Link\s+to=\"([^\"]+)\"\s*>/g, '<a href="$1">');
        html = html.replace(/<\s*\/\s*Link\s*>/g, '</a>');
        html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
        html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');
        return html;
    };
    const totalColumns = Math.max(1, cols);
    const totalCards = Array.isArray(cards) ? cards.length : 0;
    const base = Math.floor(totalCards / totalColumns);
    const remainder = totalCards % totalColumns;

    const columns = Array.from({ length: totalColumns }, (_, columnIndex) => {
        const sizeForThisColumn = base + (columnIndex < remainder ? 1 : 0);
        const start = columnIndex * base + Math.min(columnIndex, remainder);
        const end = start + sizeForThisColumn;
        return cards.slice(start, end);
    });

    return (
        <section className={styles.sectionLight}>
            <div className="container">
                <h2 className={styles.sectionTitle}>{title}</h2>
                <div className="row">
                    <div className="col">
                        <img src={image} className={styles.whatWeDoImage} alt={title} />
                    </div>
                    {columns.map((columnCards, columnIndex) => (
                        <div className="col" key={columnIndex}>
                            {columnCards.map((card, cardIndex) => (
                                <div className={styles.infoBlock} key={`${columnIndex}-${cardIndex}`}>
                                    <h3>{card.title}</h3>
                                    <p dangerouslySetInnerHTML={{ __html: toHtml(card.description) }} />
                                </div>
                            ))}
                        </div>
                    ))}
                </div>
            </div>
        </section>
    );
}