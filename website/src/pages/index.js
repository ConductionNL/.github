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
  iso: (
    <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2l9 4v6c0 5-4 9-9 10-5-1-9-5-9-10V6z" />
      <path d="M9 12l2 2 4-4" />
    </svg>
  ),
  services: (
    <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="3" />
      <path d="M12 2v3M12 19v3M2 12h3M19 12h3M5 5l2 2M17 17l2 2M5 19l2-2M17 7l2-2" />
    </svg>
  ),
  catalog: (
    <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 4h6a3 3 0 0 1 3 3v13a2 2 0 0 0-2-2H4z" />
      <path d="M20 4h-6a3 3 0 0 0-3 3v13a2 2 0 0 1 2-2h7z" />
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
  { title: 'Roadmap', href: '/ROADMAP/', icon: ICONS.roadmap,
    blurb: 'Approved direction for the Conduction app ecosystem. Next up, not yet planned as OpenSpec changes.' },
  { title: 'Claude workflow', href: '/claude/', icon: ICONS.claude,
    blurb: 'Spec-driven development with OpenSpec, GitHub Issues and Claude Code. Skills, commands, conventions, parallel agents.' },
  { title: 'ISO compliance', href: '/iso/', icon: ICONS.iso,
    blurb: 'Engineering pipeline mapped to ISO/IEC standards. Clause-by-clause coverage, with gaps surfaced as a first-class output.' },
  { title: 'Services', href: '/Services/CodebaseStewardship/', icon: ICONS.services,
    blurb: 'How Conduction maintains the open-source apps it ships. SLA, codebase stewardship, NL Design tokens.' },
  { title: 'Catalog', href: '/Catalogi/', icon: ICONS.catalog,
    blurb: 'The Conduction catalog: mission, core values, and the open-source software components that put them into practice.' },
  { title: 'Products', href: '/Products/', icon: ICONS.products,
    blurb: 'Productportfolio: SLA/SAAS, implementatie, training en consultancy.' },
];

const HEX_CLIP = 'polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%)';

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
        primaryCta={{ label: 'Explore our identity', href: 'https://identity.conduction.nl/' }}
        secondaryCta={{ label: 'View on GitHub', href: 'https://github.com/ConductionNL/.github/tree/main/docs' }}
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
