import React from 'react';
import matrix from '@site/src/data/sig-matrix.json';
import styles from './SigMatrix.module.css';

const pct = (share) => `${(share * 100).toFixed(1)}%`;

const STAR_TEXT = {5: '5', 4: '4', below: '<4'};
const STAR_CLASS = {5: styles.s5, 4: styles.s4, below: styles.below};

function limitText(row) {
  const op = row.minimum ? 'at least' : 'at most';
  return `4-star ${op} ${pct(row.four)}, 5-star ${op} ${pct(row.five)}`;
}

function Cell({app, language, row}) {
  const cell = row.cells[app];
  if (!cell) {
    return (
      <td className={styles.empty} title={`${app} has no ${language} code`}>
        <span aria-hidden="true">·</span>
        <span className={styles.srOnly}>no {language} code</span>
      </td>
    );
  }
  const title = `${app}, ${language} ${row.label}: ${pct(cell.share)} (${limitText(row)})`;
  return (
    <td className={`${styles.cell} ${STAR_CLASS[cell.stars]}`} title={title}>
      <span className={styles.star}>{STAR_TEXT[cell.stars]}</span>
      <span className={styles.value}>{pct(cell.share)}</span>
    </td>
  );
}

function Legend() {
  return (
    <ul className={styles.legend}>
      <li><span className={`${styles.swatch} ${styles.s5}`}>5</span> meets our 5-star yardstick, half of each 4-star limit</li>
      <li><span className={`${styles.swatch} ${styles.s4}`}>4</span> meets the 4-star limit of the guidance</li>
      <li><span className={`${styles.swatch} ${styles.below}`}>&lt;4</span> misses the 4-star limit; the guidance gives no limits for 3, 2 or 1 stars</li>
      <li><span className={`${styles.swatch} ${styles.empty}`}>·</span> the app has no code in this language</li>
    </ul>
  );
}

export default function SigMatrix() {
  const apps = Object.keys(matrix.apps);
  const span = apps.length;
  return (
    <div className={styles.matrix}>
      <Legend />
      <div
        className={styles.scroller}
        role="region"
        aria-label={`SIG checks per app, measured ${matrix.measured}`}
        tabIndex={0}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th scope="col" className={styles.sticky}>check</th>
              {apps.map((app) => (
                <th scope="col" key={app} className={styles.app}>
                  <a href={`https://github.com/ConductionNL/${app}/tree/${matrix.apps[app].head}`}>{app}</a>
                  <span className={styles.value}>{matrix.apps[app].head.slice(0, 8)}</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr className={styles.total}>
              <th scope="row" className={styles.sticky}>checks at 4 stars or better</th>
              {apps.map((app) => (
                <td key={app}>{matrix.apps[app].four}/{matrix.apps[app].checks}</td>
              ))}
            </tr>
            <tr className={styles.total}>
              <th scope="row" className={styles.sticky}>checks at 5 stars</th>
              {apps.map((app) => (
                <td key={app}>{matrix.apps[app].five}/{matrix.apps[app].checks}</td>
              ))}
            </tr>
            {matrix.groups.map((group) => (
              <React.Fragment key={group.language}>
                <tr className={styles.group}>
                  <th scope="rowgroup" className={styles.sticky}>{group.language}</th>
                  <td colSpan={span} />
                </tr>
                {group.rows.map((row) => (
                  <tr key={row.id}>
                    <th scope="row" className={styles.sticky}>
                      {row.label}
                      <span className={styles.value}>{limitText(row)}</span>
                    </th>
                    {apps.map((app) => (
                      <Cell key={app} app={app} language={group.language} row={row} />
                    ))}
                  </tr>
                ))}
              </React.Fragment>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
