import React from 'react';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';

const SECTIONS = [
  {
    title: 'Roadmap',
    href: '/ROADMAP',
    blurb: 'Approved direction for the Conduction app ecosystem. Items here are next, not yet planned as OpenSpec changes.',
  },
  {
    title: 'Claude workflow',
    href: '/claude/',
    blurb: 'Spec-driven development with OpenSpec, GitHub Issues and Claude Code. Skills, commands, conventions, parallel agents.',
  },
  {
    title: 'ISO compliance',
    href: '/iso/',
    blurb: 'Engineering pipeline mapped to ISO/IEC standards. Clause-by-clause coverage, with gaps surfaced as a first-class output.',
  },
  {
    title: 'Services',
    href: '/Services/CodebaseStewardship',
    blurb: 'How Conduction maintains the open-source apps it ships. SLA, codebase stewardship, NL Design tokens.',
  },
  {
    title: 'Catalog',
    href: '/Catalogi',
    blurb: 'The Conduction catalog: mission, core values, and the open-source software components that put them into practice.',
  },
  {
    title: 'Products',
    href: '/Products',
    blurb: 'Productportfolio: SLA/SAAS, implementatie, training en consultancy.',
  },
];

export default function Home() {
  const { siteConfig } = useDocusaurusContext();
  return (
    <Layout
      title={siteConfig.title}
      description="Engineering, product, and ISO knowledge base for Conduction."
    >
      <main className="container" style={{ paddingBlock: '64px 96px' }}>
        <header style={{ maxWidth: '720px', marginBottom: '48px' }}>
          <p
            style={{
              fontFamily: 'var(--ff-mono, monospace)',
              fontSize: '0.85rem',
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
              color: 'var(--c-blue-cobalt, #25408F)',
              marginBottom: '12px',
            }}
          >
            docs.conduction.nl
          </p>
          <h1 style={{ marginBottom: '16px' }}>Conduction Docs</h1>
          <p style={{ fontSize: '1.15rem', lineHeight: 1.6, opacity: 0.85 }}>
            Engineering, product, and ISO knowledge base. Source markdown lives at{' '}
            <Link to="https://github.com/ConductionNL/.github/tree/main/docs">
              github.com/ConductionNL/.github/docs
            </Link>
            .
          </p>
        </header>

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
              onMouseEnter={(e) => {
                e.currentTarget.style.transform = 'translateY(-2px)';
                e.currentTarget.style.boxShadow = '0 8px 24px rgba(0,0,0,0.06)';
                e.currentTarget.style.borderColor = 'var(--c-blue-cobalt, #25408F)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = '';
                e.currentTarget.style.boxShadow = '';
                e.currentTarget.style.borderColor = 'var(--ifm-color-emphasis-200, #e5e5e5)';
              }}
            >
              <h2 style={{ fontSize: '1.25rem', marginBottom: '8px', marginTop: 0 }}>{s.title}</h2>
              <p style={{ margin: 0, fontSize: '0.95rem', lineHeight: 1.5, opacity: 0.8 }}>
                {s.blurb}
              </p>
            </Link>
          ))}
        </section>
      </main>
    </Layout>
  );
}
