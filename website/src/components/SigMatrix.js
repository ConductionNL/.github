import React, {useEffect, useRef, useState} from 'react';
import matrix from '@site/src/data/sig-matrix.json';
import styles from './SigMatrix.module.css';

const pct = (share) => `${(share * 100).toFixed(1)}%`;

const STAR_TEXT = {5: '5', 4: '4', below: '<4'};
const STAR_CLASS = {5: styles.s5, 4: styles.s4, below: styles.below};

const wholePct = (part, total) => `${Math.round((part / total) * 100)}%`;

function useAppFilter() {
  const [query, setQuery] = useState('');
  const all = Object.keys(matrix.apps);
  const needle = query.trim().toLowerCase();
  return {all, apps: all.filter((app) => app.includes(needle)), query, setQuery};
}

function AppFilter({filter}) {
  return (
    <div className={styles.filter}>
      <label>
        Search apps{' '}
        <input
          type="search"
          value={filter.query}
          onChange={(event) => filter.setQuery(event.target.value)}
        />
      </label>
      <span role="status">Showing {filter.apps.length} of {filter.all.length} apps</span>
    </div>
  );
}

function FleetAverage() {
  const apps = Object.values(matrix.apps);
  const four = apps.reduce((sum, app) => sum + app.four, 0);
  const checks = apps.reduce((sum, app) => sum + app.checks, 0);
  return (
    <p className={styles.average}>
      All {apps.length} apps: {four} of {checks} checks at 4 stars or better ({wholePct(four, checks)}).
      This average is our own figure, not a SIG score.
    </p>
  );
}

function Scroller({label, children}) {
  const top = useRef(null);
  const main = useRef(null);
  const [width, setWidth] = useState(0);
  useEffect(() => {
    const element = main.current;
    const observer = new ResizeObserver(() => setWidth(element.scrollWidth));
    observer.observe(element);
    observer.observe(element.firstElementChild);
    return () => observer.disconnect();
  }, []);
  return (
    <>
      <div
        ref={top}
        className={styles.topScroll}
        aria-hidden="true"
        onScroll={() => { main.current.scrollLeft = top.current.scrollLeft; }}>
        <div style={{width}} />
      </div>
      <div
        ref={main}
        className={styles.scroller}
        role="region"
        aria-label={label}
        tabIndex={0}
        onScroll={() => { top.current.scrollLeft = main.current.scrollLeft; }}>
        {children}
      </div>
    </>
  );
}

function limitText(row) {
  const op = row.minimum ? 'at least' : 'at most';
  return `4-star ${op} ${pct(row.four)}, 5-star ${op} ${pct(row.five)}`;
}

function Lock({label}) {
  return (
    <>
      <svg className={styles.lock} viewBox="0 0 10 12" width="9" height="11" aria-hidden="true" focusable="false">
        <path d="M2.5 5V3.5a2.5 2.5 0 0 1 5 0V5" fill="none" stroke="currentColor" strokeWidth="1.4" />
        <rect x="1" y="5" width="8" height="6.5" rx="1" fill="currentColor" />
      </svg>
      {label && <span className={styles.srOnly}>{label}</span>}
    </>
  );
}

function Cell({app, language, row}) {
  const cell = row.cells[app];
  const floored = (matrix.apps[app].floor?.checks || []).includes(row.id);
  if (!cell) {
    return (
      <td className={styles.empty} title={`${app} has no ${language} code`}>
        <span aria-hidden="true">·</span>
        <span className={styles.srOnly}>no {language} code</span>
      </td>
    );
  }
  const floorText = floored ? ', floored by gate 123' : '';
  const title = `${app}, ${language} ${row.label}: ${pct(cell.share)} (${limitText(row)})${floorText}`;
  return (
    <td
      className={`${styles.cell} ${STAR_CLASS[cell.stars]} ${floored ? styles.floored : ''}`}
      title={title}>
      <span className={styles.star}>
        {STAR_TEXT[cell.stars]}
        {floored && <Lock label="floored" />}
      </span>
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
      <li><span className={`${styles.swatch} ${styles.s4} ${styles.floored}`}>4<Lock /></span> floored: gate 123 refuses a change that loses this check</li>
      <li><span className={`${styles.swatch} ${styles.empty}`}>·</span> the app has no code in this language</li>
    </ul>
  );
}

export default function SigMatrix() {
  const filter = useAppFilter();
  const {apps} = filter;
  const span = Math.max(apps.length, 1);
  return (
    <div className={styles.matrix}>
      <Legend />
      <FleetAverage />
      <AppFilter filter={filter} />
      <Scroller label={`SIG checks per app, measured ${matrix.measured}`}>
        <table className={styles.table}>
          <thead className={styles.head}>
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
              <th scope="row" className={styles.sticky}>
                checks at 4 stars or better
                <span className={styles.value}>and the share of the app's checks</span>
              </th>
              {apps.map((app) => (
                <td key={app}>
                  {matrix.apps[app].four}/{matrix.apps[app].checks}
                  <span className={styles.value}>{wholePct(matrix.apps[app].four, matrix.apps[app].checks)}</span>
                </td>
              ))}
            </tr>
            <tr className={styles.total}>
              <th scope="row" className={styles.sticky}>checks at 5 stars</th>
              {apps.map((app) => (
                <td key={app}>{matrix.apps[app].five}/{matrix.apps[app].checks}</td>
              ))}
            </tr>
            <tr className={styles.total}>
              <th scope="row" className={styles.sticky}>
                floored checks
                <span className={styles.value}>floor recorded at commit</span>
              </th>
              {apps.map((app) => {
                const floor = matrix.apps[app].floor;
                return (
                  <td key={app}>
                    {floor ? floor.checks.length : '·'}
                    {floor?.measured_at && <span className={styles.value}>{floor.measured_at.slice(0, 8)}</span>}
                  </td>
                );
              })}
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
      </Scroller>
    </div>
  );
}

export function SigFloors() {
  const floors = matrix.floors;
  const filter = useAppFilter();
  if (!floors) return null;
  const {apps} = filter;
  return (
    <div className={styles.matrix}>
      <AppFilter filter={filter} />
      <Scroller label={`Floors and ratchets per app, read ${floors.read}`}>
        <table className={styles.table}>
          <thead className={styles.head}>
            <tr>
              <th scope="col" className={styles.sticky}>floor</th>
              {apps.map((app) => (
                <th scope="col" key={app} className={styles.app}>
                  <a href={`https://github.com/ConductionNL/${app}/tree/${floors.refs[app]}`}>{app}</a>
                  <span className={styles.value}>{floors.refs[app].slice(0, 8)}</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {floors.rows.map((row) => (
              <tr key={row.id}>
                <th scope="row" className={styles.sticky}>
                  {row.label}
                  <span className={styles.value}>{row.what}</span>
                </th>
                {apps.map((app) => {
                  const cell = row.cells[app];
                  if (!cell) {
                    return (
                      <td key={app} className={styles.empty} title={`${app} has no ${row.label}`}>
                        <span aria-hidden="true">·</span>
                        <span className={styles.srOnly}>none</span>
                      </td>
                    );
                  }
                  return (
                    <td key={app} title={`${app}: ${cell.detail}`}>{String(cell.value)}</td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </Scroller>
    </div>
  );
}
