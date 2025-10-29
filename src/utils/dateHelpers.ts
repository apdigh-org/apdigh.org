export function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleDateString('en-GB', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
}

export function formatDateShort(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleDateString('en-GB', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

export function getDaysUntil(dateString: string): number {
  const targetDate = new Date(dateString);
  const today = new Date();
  const diffTime = targetDate.getTime() - today.getTime();
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  return diffDays;
}

export function isUpcoming(dateString: string): boolean {
  return getDaysUntil(dateString) > 0;
}

export function getRelativeTime(dateString: string): string {
  const days = getDaysUntil(dateString);

  if (days < 0) {
    return `${Math.abs(days)} days ago`;
  } else if (days === 0) {
    return 'Today';
  } else if (days === 1) {
    return 'Tomorrow';
  } else if (days < 7) {
    return `In ${days} days`;
  } else if (days < 30) {
    const weeks = Math.floor(days / 7);
    return `In ${weeks} week${weeks > 1 ? 's' : ''}`;
  } else {
    const months = Math.floor(days / 30);
    return `In ${months} month${months > 1 ? 's' : ''}`;
  }
}
