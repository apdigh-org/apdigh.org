"""
Shared constants for the bill processing pipeline.
"""

import re
from enum import Enum


def slugify(text: str) -> str:
    """Convert text to a URL-friendly slug.

    Args:
        text: Text to slugify

    Returns:
        URL-friendly slug (lowercase, hyphens, alphanumeric only)
    """
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'\s+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text.strip('-')


class Topic(str, Enum):
    """Topic areas for impact assessment."""
    DIGITAL_INNOVATION = "Digital Innovation"
    FREEDOM_OF_SPEECH = "Freedom of Speech"
    PRIVACY_DATA_RIGHTS = "Privacy & Data Rights"
    BUSINESS_ENVIRONMENT = "Business Environment"


# Topic areas list (for iteration)
TOPICS = [topic.value for topic in Topic]


class ImpactLevel(str, Enum):
    """Impact levels for bill provisions and analyses (can be positive or negative)."""
    SEVERE_NEGATIVE = "severe-negative"
    HIGH_NEGATIVE = "high-negative"
    MEDIUM_NEGATIVE = "medium-negative"
    LOW_NEGATIVE = "low-negative"
    Neutral = "neutral"
    LOW_POSITIVE = "low-positive"
    MEDIUM_POSITIVE = "medium-positive"
    HIGH_POSITIVE = "high-positive"
    SEVERE_POSITIVE = "severe-positive"


class Severity(str, Enum):
    """Severity levels for key concerns."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# Section categories
CATEGORY_PROVISION = "provision"
CATEGORY_PREAMBLE = "preamble"
CATEGORY_METADATA = "metadata"
