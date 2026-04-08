import React from 'react';
import siteData from '@site/src/data/site-data.json';

// Access nested values: <Val path="emails.support" /> renders "support@conduction.nl"
export function Val({path}) {
  const value = path.split('.').reduce((obj, key) => obj?.[key], siteData);
  if (value == null) return null;
  return <>{String(value)}</>;
}

// Render as mailto link: <Email path="emails.support" /> renders <a href="mailto:...">support@conduction.nl</a>
export function Email({path}) {
  const value = path.split('.').reduce((obj, key) => obj?.[key], siteData);
  if (value == null) return null;
  return <a href={`mailto:${value}`}>{value}</a>;
}

// Render as external link: <ExtLink path="links.passwork" label="Passwork" />
export function ExtLink({path, label}) {
  const value = path.split('.').reduce((obj, key) => obj?.[key], siteData);
  if (value == null) return null;
  return <a href={value} target="_blank" rel="noopener noreferrer">{label || value}</a>;
}
