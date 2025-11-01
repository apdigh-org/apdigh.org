/**
 * Organizational constants for APDI Ghana
 * Only includes info about the organization itself, not page-specific content
 */

export const SITE = {
  name: 'APDI',
  fullName: 'Association for the Protection of Digital Innovation',
  tagline: 'Protecting Digital Innovation',
  url: 'https://apdigh.org',
  email: 'contact@apdigh.org',

  mission: "Protecting Ghana's digital innovation sector by informing citizens about tech bills and their impacts on startups, innovation, and the digital economy.",

  social: [
    {
      name: 'Twitter',
      icon: 'ti ti-brand-x',
      url: 'https://twitter.com/apdigh',
      handle: '@apdigh',
    }
  ],
} as const;

export const NAV_ITEMS = [
  { href: '/', label: 'Home' },
  { href: '/bills', label: 'Bills' },
  { href: '/about', label: 'About' },
] as const;

export const FOOTER_LINKS = {
  quickLinks: [
    { href: '/bills', label: 'All Bills' },
    { href: '/about', label: 'About Us' },
  ],
  resources: [
    { href: 'https://github.com/apdigh-org/apdigh.org', label: 'GitHub Repository', external: true },
  ],
  legal: [
    { href: '/about#transparency', label: 'AI Transparency' },
  ],
} as const;

