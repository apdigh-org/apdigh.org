/**
 * Organizational constants for APDI Ghana
 * Only includes info about the organization itself, not page-specific content
 */

export const SITE = {
  name: 'APDI',
  fullName: 'Association for the Protection of Digital Innovation',
  tagline: 'Protecting Digital Innovation',
  url: 'https://apdi.org.gh',

  mission: "Protecting Ghana's digital innovation sector by informing citizens about tech bills and their impacts on startups, innovation, and the digital economy.",

  contact: {
    email: 'contact@apdi.org.gh',
  },

  social: [
    {
      name: 'Twitter',
      icon: 'ti-brand-x',
      url: 'https://twitter.com/apdi_ghana',
    },
    {
      name: 'Facebook',
      icon: 'ti-brand-facebook',
      url: 'https://facebook.com/apdi.ghana',
    },
  ],
} as const;

export const NAV_ITEMS = [
  { href: '/', label: 'Home' },
  { href: '/bills', label: 'Bills' },
  { href: '/timeline', label: 'Timeline' },
  { href: '/dashboard', label: 'Dashboard' },
  { href: '/about', label: 'About' },
] as const;

export const FOOTER_LINKS = {
  quickLinks: [
    { href: '/', label: 'All Bills' },
    { href: '/timeline', label: 'Timeline' },
    { href: '/dashboard', label: 'Dashboard' },
    { href: '/about', label: 'About Us' },
    { href: '/glossary', label: 'Glossary' },
  ],
  resources: [
    { href: '/how-to-comment', label: 'How to Submit Comments' },
    { href: '/find-mp', label: 'Find Your MP' },
    { href: '/partners', label: 'Partner Organizations' },
    { href: '/faq', label: 'FAQ' },
  ],
  legal: [
    { href: '/privacy', label: 'Privacy Policy' },
    { href: '/terms', label: 'Terms of Use' },
  ],
} as const;

