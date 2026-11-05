import React, {useEffect, useRef, useState} from 'react';
import matrix from '@site/src/data/sig-matrix.json';
import styles from './SigMatrix.module.css';

const STAR_CLASS = {5: styles.s5, 4: styles.s4, 3: styles.s3, 2: styles.s2, 1: styles.s1, '<4': styles.below};
const STATE_CLASS = {pass: styles.s4, fail: styles.below, warn: styles.s2, skip: styles.empty};
const STATE_TEXT = {pass: 'passes', fail: 'fails', warn: 'warns', skip: 'did not run'};

const wholePct = (part, total) => `${Math.round((part / total) * 100)}%`;
const starText = (stars) => (stars === '<4' ? '<4' : `${stars}★`);
const starLabel = (stars) => (stars === '<4' ? 'below 4 stars' : `${stars} star${stars === 1 ? '' : 's'}`);

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
      All {apps.length} apps: {four} of {checks} SIG maintainability checks at 4 stars or better
      ({wholePct(four, checks)}). This average is our own figure, not a SIG score.
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

function Empty({app, what}) {
  return (
    <td className={styles.empty} title={`${app}: ${what}`}>
      <span aria-hidden="true">·</span>
      <span className={styles.srOnly}>{what}</span>
    </td>
  );
}

function StarCell({app, row}) {
  const cell = row.cells[app];
  if (!cell) return <Empty app={app} what="not measured for this app" />;
  const floored = (matrix.apps[app].floor?.checks || []).includes(row.id);
  if (cell.stars === null || cell.stars === undefined) {
    return <td title={`${app}, ${row.label}: ${cell.title || cell.text}`}><span className={styles.value}>{cell.text}</span></td>;
  }
  const title = `${app}, ${row.label}: ${cell.text}, ${starLabel(cell.stars)}`
    + `${cell.title ? ` (${cell.title})` : ''}${floored ? ', floored by gate 123' : ''}`;
  return (
    <td className={`${styles.cell} ${STAR_CLASS[cell.stars]} ${floored ? styles.floored : ''}`} title={title}>
      <span className={styles.star}>
        {starText(cell.stars)}
        {floored && <Lock label="floored" />}
      </span>
      <span className={styles.value}>{cell.text}</span>
    </td>
  );
}

function StateCell({app, cell, what}) {
  if (!cell) return <Empty app={app} what={what} />;
  return (
    <td className={`${styles.cell} ${STATE_CLASS[cell.state]}`} title={`${app}: ${cell.title}`}>
      <span className={styles.star}>{cell.text}</span>
      {cell.sub && <span className={styles.value}>{cell.sub}</span>}
      {!cell.sub && <span className={styles.srOnly}>{STATE_TEXT[cell.state]}</span>}
    </td>
  );
}

function Legend() {
  return (
    <ul className={styles.legend}>
      {[5, 4, 3, 2, 1].map((s) => (
        <li key={s}><span className={`${styles.swatch} ${STAR_CLASS[s]}`}>{s}★</span> {starLabel(s)}</li>
      ))}
      <li><span className={`${styles.swatch} ${styles.below}`}>&lt;4</span> misses 4 stars where no lower band is published or estimated</li>
      <li><span className={`${styles.swatch} ${styles.s4} ${styles.floored}`}>4★<Lock /></span> floored: gate 123 refuses a change that loses this check</li>
      <li><span className={`${styles.swatch} ${styles.empty}`}>·</span> not measured for this app</li>
    </ul>
  );
}

function SectionRow({title, span}) {
  return (
    <tr className={styles.section}>
      <th scope="rowgroup" className={styles.sticky}>{title}</th>
      <td colSpan={span} />
    </tr>
  );
}

function GroupRow({title, span}) {
  return (
    <tr className={styles.group}>
      <th scope="rowgroup" className={styles.sticky}>{title}</th>
      <td colSpan={span} />
    </tr>
  );
}

function CategoryRows({category, apps}) {
  const [open, setOpen] = useState(false);
  const id = `sig-${category.id.replace('.', '-')}`;
  return (
    <>
      <tr>
        <th scope="row" className={styles.sticky}>
          <button
            type="button"
            className={styles.toggle}
            aria-expanded={open}
            aria-controls={id}
            onClick={() => setOpen(!open)}>
            <span aria-hidden="true">{open ? '▾' : '▸'}</span> {category.title}
          </button>
          <span className={styles.value}>gates passing of applicable, and findings</span>
        </th>
        {apps.map((app) => (
          <StateCell key={app} app={app} cell={category.cells[app]} what="no applicable gate in this category" />
        ))}
      </tr>
      {open && category.gates.map((gate, index) => (
        <tr key={gate.id} id={index === 0 ? id : undefined} className={styles.child}>
          <th scope="row" className={styles.sticky}>{gate.label}</th>
          {apps.map((app) => (
            <StateCell key={app} app={app} cell={gate.cells[app]} what="not applicable" />
          ))}
        </tr>
      ))}
    </>
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
      <Scroller label={`Quality matrix per app, measured ${matrix.measured}`}>
        <table className={styles.table}>
          <thead className={styles.head}>
            <tr>
              <th scope="col" className={styles.sticky}>measure</th>
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
                SIG checks at 4 stars or better
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
              <th scope="row" className={styles.sticky}>SIG checks at 5 stars</th>
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
            {matrix.sections.map((section) => (
              <React.Fragment key={section.id}>
                <SectionRow title={section.title} span={span} />
                {section.groups.map((group) => (
                  <React.Fragment key={`${section.id}-${group.title}`}>
                    <GroupRow title={group.title} span={span} />
                    {group.rows.map((row) => (
                      <tr key={row.id}>
                        <th scope="row" className={styles.sticky}>
                          {row.label}
                          <span className={styles.value}>{row.limits}</span>
                        </th>
                        {apps.map((app) => <StarCell key={app} app={app} row={row} />)}
                      </tr>
                    ))}
                  </React.Fragment>
                ))}
              </React.Fragment>
            ))}
            <SectionRow title="Gates per category" span={span} />
            {matrix.gateCategories.map((category) => (
              <CategoryRows key={category.id} category={category} apps={apps} />
            ))}
          </tbody>
        </table>
      </Scroller>
    </div>
  );
}

export function SigBeyond() {
  return (
    <table>
      <thead>
        <tr>
          <th scope="col">measure</th>
          <th scope="col">why we add it</th>
          <th scope="col">basis of the bands</th>
        </tr>
      </thead>
      <tbody>
        {matrix.beyond.map((row) => (
          <tr key={row.label}>
            <th scope="row">{row.label}</th>
            <td>{row.why}</td>
            <td>{row.basis}</td>
          </tr>
        ))}
      </tbody>
    </table>
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
                  if (!cell) return <Empty key={app} app={app} what="none" />;
                  return <td key={app} title={`${app}: ${cell.detail}`}>{String(cell.value)}</td>;
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </Scroller>
    </div>
  );
}
