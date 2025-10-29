/**
 * Standard impact categories for bill analysis
 * Each bill can include any/all of these impact assessments
 */

export const IMPACT_CATEGORIES = {
  innovation: {
    name: 'Digital Innovation',
    icon: 'bulb',
    iconColor: 'purple',
    bgColor: 'bg-purple-100',
    iconColorClass: 'text-purple-600',
  },
  freedomOfSpeech: {
    name: 'Freedom of Speech',
    icon: 'message-circle',
    iconColor: 'blue',
    bgColor: 'bg-blue-100',
    iconColorClass: 'text-blue-600',
  },
  privacy: {
    name: 'Privacy & Data Rights',
    icon: 'lock',
    iconColor: 'green',
    bgColor: 'bg-green-100',
    iconColorClass: 'text-green-600',
  },
  business: {
    name: 'Business Environment',
    icon: 'briefcase',
    iconColor: 'orange',
    bgColor: 'bg-orange-100',
    iconColorClass: 'text-orange-600',
  },
} as const;

export type ImpactKey = keyof typeof IMPACT_CATEGORIES;

/**
 * Helper to get impact category metadata
 */
export function getImpactCategory(key: string) {
  return IMPACT_CATEGORIES[key as ImpactKey];
}

/**
 * Helper to get impact display name
 */
export function getImpactName(key: string) {
  const category = getImpactCategory(key);
  return category?.name || key;
}
