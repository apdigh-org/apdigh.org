export interface Category {
  id: string;
  name: string;
  description: string;
  color: string;
  icon: string;
}

export const categories: Category[] = [
  {
    id: 'technology',
    name: 'Technology & Cybersecurity',
    description: 'Bills affecting technology companies, cybersecurity, and digital infrastructure',
    color: 'var(--color-tech-blue)',
    icon: '💻',
  },
  {
    id: 'media',
    name: 'Media & Communications',
    description: 'Bills regulating media, broadcasting, and communications',
    color: 'var(--color-media-purple)',
    icon: '📡',
  },
  {
    id: 'rights',
    name: 'Rights & Freedoms',
    description: 'Bills affecting civil liberties, human rights, and freedoms',
    color: 'var(--color-rights-green)',
    icon: '⚖️',
  },
  {
    id: 'business',
    name: 'Business & Commerce',
    description: 'Bills impacting business operations, commerce, and trade',
    color: 'var(--color-business-orange)',
    icon: '🏢',
  },
  {
    id: 'justice',
    name: 'Justice & Law Enforcement',
    description: 'Bills related to law enforcement, prosecution, and judicial processes',
    color: 'var(--color-justice-red)',
    icon: '👮',
  },
  {
    id: 'privacy',
    name: 'Privacy & Data Protection',
    description: 'Bills concerning personal data, privacy rights, and data protection',
    color: 'var(--color-privacy-teal)',
    icon: '🔒',
  },
];

export function getCategoryById(id: string): Category | undefined {
  return categories.find(cat => cat.id === id);
}

export function getCategoryColor(id: string): string {
  return getCategoryById(id)?.color || 'var(--color-primary-blue)';
}
