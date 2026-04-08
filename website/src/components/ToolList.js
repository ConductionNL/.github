import React from 'react';
import siteData from '@site/src/data/site-data.json';

export default function ToolList({category}) {
  const items = siteData.tools[category];
  if (!items) return null;
  return <>{items.join(', ')}</>;
}
