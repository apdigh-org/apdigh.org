export interface SEOProps {
  title: string;
  description: string;
  ogImage?: string;
  ogType?: string;
  canonicalURL?: string;
  noindex?: boolean;
}

export function generateSEO(props: SEOProps) {
  const {
    title,
    description,
    ogImage = '/images/og-default.png',
    ogType = 'website',
    canonicalURL,
    noindex = false,
  } = props;

  const siteTitle = 'APDI Ghana';
  const fullTitle = title === siteTitle ? title : `${title} | ${siteTitle}`;

  return {
    title: fullTitle,
    description,
    ogImage,
    ogType,
    canonicalURL,
    noindex,
  };
}

export function getBillOGImage(billId: string): string {
  return `/images/og/${billId}.png`;
}

export function getConcernOGImage(billId: string, concernId: string): string {
  return `/images/og/concerns/${billId}_${concernId}.png`;
}

export function truncateDescription(text: string, maxLength: number = 160): string {
  if (text.length <= maxLength) return text;

  const truncated = text.substring(0, maxLength - 3);
  const lastSpace = truncated.lastIndexOf(' ');

  return truncated.substring(0, lastSpace) + '...';
}
