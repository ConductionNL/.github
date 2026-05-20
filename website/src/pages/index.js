import React from 'react';
import Link from '@docusaurus/Link';
import Layout from '@theme/Layout';
import { DetailHero } from '@conduction/docusaurus-preset/components';

const ICONS = {
  identity: (
    <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="9" r="3.2" />
      <path d="M5.5 19c1.2-3 3.7-4.5 6.5-4.5s5.3 1.5 6.5 4.5" />
      <path d="M4 4h3M17 4h3M4 20h3M17 20h3M4 4v3M20 4v3M4 17v3M20 17v3" />
    </svg>
  ),
  wayofwork: (
    <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <path d="M5 4h11l3 3v13a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1z" />
      <path d="M8 9h8M8 13h8M8 17h5" />
    </svg>
  ),
  roadmap: (
    <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 7l5-2 6 2 5-2v12l-5 2-6-2-5 2z" />
      <path d="M9 5v14M15 7v14" />
    </svg>
  ),
  claude: (
    <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 6h16M4 12h10M4 18h16" />
      <circle cx="18" cy="12" r="2" fill="currentColor" />
    </svg>
  ),
  hydra: (
    <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="5" cy="12" r="2" />
      <circle cx="19" cy="6" r="2" />
      <circle cx="19" cy="18" r="2" />
      <path d="M7 12h4l4-6h2M11 12h4l4 6h2" />
    </svg>
  ),
  iso: (
    <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2l9 4v6c0 5-4 9-9 10-5-1-9-5-9-10V6z" />
      <path d="M9 12l2 2 4-4" />
    </svg>
  ),
  support: (
    <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <path d="M18 8a6 6 0 1 0-12 0v4a3 3 0 0 0 3 3h1v-7H7" />
      <path d="M18 8v4a3 3 0 0 1-3 3h-1v-7h3" />
      <path d="M14 19h-1.5a2 2 0 0 1-2-2V15" />
    </svg>
  ),
  products: (
    <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 7l9-4 9 4-9 4z" />
      <path d="M3 12l9 4 9-4" />
      <path d="M3 17l9 4 9-4" />
    </svg>
  ),
};

const SECTIONS = [
  { title: 'Identity', href: 'https://identity.conduction.nl/', icon: ICONS.identity,
    blurb: 'Who Conduction is. Brand, voice, and visual identity for both our culture and our designs — the shared identity every (digital) employee carries.' },
  { title: 'Way of Work', href: '/WayOfWork/way-of-work/', icon: ICONS.wayofwork,
    blurb: 'How Conduction operates day-to-day — onboarding, roles, building software, and customer support. The handbook every (digital) employee follows.' },
  { title: 'Roadmap', href: 'https://github.com/orgs/ConductionNL/projects/4', icon: ICONS.roadmap,
    blurb: 'Where the Conduction app ecosystem is heading — tracked live on GitHub Projects. What’s next, what’s in flight, and what’s shipped, alongside the issues that drive each spec.' },
  { title: 'Claude workflow', href: '/claude/', icon: ICONS.claude,
    blurb: 'Spec-driven development with OpenSpec, GitHub Issues and Claude Code. Skills, commands, conventions, parallel agents.' },
  { title: 'Hydra', href: '/hydra/', icon: ICONS.hydra,
    blurb: 'Conduction\'s agentic spec-driven CI/CD pipeline. From an OpenSpec change to a reviewed PR — Builder, parallel code + security review, with a human in the loop at the end.' },
  { title: 'ISO compliance', href: '/iso/', icon: ICONS.iso,
    blurb: 'Engineering pipeline mapped to ISO/IEC standards. Clause-by-clause coverage, with gaps surfaced as a first-class output.' },
  { title: 'Support', href: 'https://www.conduction.nl/support/', icon: ICONS.support,
    blurb: 'How we keep customers running. SLA, incident response, and codebase stewardship — see the support plans on conduction.nl.' },
  { title: 'Products', href: 'https://www.conduction.nl/apps/', icon: ICONS.products,
    blurb: 'The Conduction app portfolio — see what we build and ship at conduction.nl/apps.' },
];

const HEX_CLIP = 'polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%)';

/**
 * Hero-right illustration. Honeycomb of hex tiles around a central
 * cobalt anchor, each surrounding tile holding one of the doc-section
 * icons. Mirrors the brand `<HexNetwork/>` pattern; rendered inline
 * to avoid needing logo SVG assets for a docs hub.
 */
function DocsHubMock() {
  const ring = [
    {icon: ICONS.identity,   row: 0, col: 0},
    {icon: ICONS.wayofwork,  row: 0, col: 2},
    {icon: ICONS.hydra,      row: 1, col: -1},
    {icon: ICONS.claude,     row: 1, col: 3},
    {icon: ICONS.iso,        row: 2, col: 0},
    {icon: ICONS.products,   row: 2, col: 2},
  ];
  const W = 92;
  const H = 106;
  const VGAP = -28;
  const HEX_FILL = 'rgba(255, 255, 255, 0.08)';
  const HEX_STROKE = 'rgba(255, 255, 255, 0.45)';
  const tileStyle = (row, col) => ({
    position: 'absolute',
    width: W,
    height: H,
    top: row * (H + VGAP),
    left: col * (W / 2),
    clipPath: HEX_CLIP,
    WebkitClipPath: HEX_CLIP,
    background: HEX_FILL,
    border: `1px solid ${HEX_STROKE}`,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: '#fff',
  });
  return (
    <div
      aria-hidden="true"
      style={{
        position: 'relative',
        width: W * 2,
        height: 3 * H + 2 * VGAP,
        marginLeft: 'auto',
      }}
    >
      {ring.map((t, i) => (
        <div key={i} style={tileStyle(t.row, t.col)}>
          <span style={{width: 32, height: 32, display: 'inline-block', color: 'rgba(255,255,255,0.85)'}}>
            {t.icon}
          </span>
        </div>
      ))}
      {/* Centre anchor: solid orange Conduction hex */}
      <div
        style={{
          position: 'absolute',
          width: W,
          height: H,
          top: 1 * (H + VGAP),
          left: 1 * (W / 2),
          clipPath: HEX_CLIP,
          WebkitClipPath: HEX_CLIP,
          background: 'var(--c-orange-knvb)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#fff',
          fontFamily: 'var(--ff-display, inherit)',
          fontWeight: 700,
          fontSize: 22,
        }}
      >
        C
      </div>
    </div>
  );
}

export default function Home() {
  return (
    <Layout
      title="How We Work"
      description="How Conduction operates — culture, roles, expectations, and the way our (digital) employees act."
    >
      <DetailHero
        background="cobalt"
        title="How We Work"
        tagline="How Conduction operates — culture, roles, expectations, and the way our (digital) employees act."
        iconColor="var(--c-orange-knvb)"
        icon={
          <svg viewBox="0 0 24 24">
            <path d="M4 4h11l4 4v13a1 1 0 0 1-1 1H4z" />
            <path d="M15 4v4h4" />
            <path d="M8 12h8M8 16h8M8 20h5" />
          </svg>
        }
        primaryCta={{ label: 'Explore our identity', href: 'https://identity.conduction.nl/', tone: 'orange' }}
        secondaryCta={{ label: 'View on GitHub', href: 'https://github.com/ConductionNL/.github/tree/main/docs' }}
        illustration={<DocsHubMock />}
      />

      <main className="container" style={{ paddingBlock: '48px 96px' }}>
        <section
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
            gap: '20px',
          }}
        >
          {SECTIONS.map((s) => (
            <Link
              key={s.href}
              to={s.href}
              style={{
                display: 'block',
                padding: '24px',
                borderRadius: '12px',
                background: 'var(--ifm-card-background-color, #fff)',
                border: '1px solid var(--ifm-color-emphasis-200, #e5e5e5)',
                textDecoration: 'none',
                color: 'inherit',
                transition: 'transform 120ms ease, box-shadow 120ms ease, border-color 120ms ease',
              }}
            >
              <span
                aria-hidden="true"
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  width: '44px',
                  height: '50px',
                  background: 'var(--c-blue-cobalt, #25408F)',
                  color: '#fff',
                  clipPath: HEX_CLIP,
                  WebkitClipPath: HEX_CLIP,
                  marginBottom: '14px',
                }}
              >
                <span style={{ width: '22px', height: '22px', display: 'inline-block' }}>
                  {s.icon}
                </span>
              </span>
              <h2 style={{ fontSize: '1.2rem', margin: '0 0 6px', fontFamily: 'var(--ff-display, inherit)' }}>
                {s.title}
              </h2>
              <p style={{ margin: 0, fontSize: '0.95rem', lineHeight: 1.5, opacity: 0.78 }}>
                {s.blurb}
              </p>
            </Link>
          ))}
        </section>
      </main>
    </Layout>
  );
}
