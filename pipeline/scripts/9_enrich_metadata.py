#!/usr/bin/env python3
"""
Enrich bill JSON with metadata.

This script adds metadata fields like bill title, PDF path, processing dates,
and statistics to the bill JSON after all processing is complete.
"""

import json
import sys
import re
from pathlib import Path
from datetime import datetime, timezone
from shared import slugify


def remove_number_prefix(text: str) -> str:
    """Remove leading number prefix from bill title (e.g., '1. ' or '15. ')."""
    return re.sub(r'^\d+\.\s*', '', text)


def extract_bill_title(sections: list) -> str:
    """Extract bill title from preamble sections.

    Args:
        sections: List of bill sections

    Returns:
        Bill title string
    """
    for section in sections:
        if section.get('category', {}).get('type') == 'preamble':
            title = section.get('title', '')
            if title and len(title) > 10:  # Skip very short titles
                return title

    return ""


def calculate_statistics(sections: list) -> dict:
    """Calculate statistics about the bill.

    Args:
        sections: List of bill sections

    Returns:
        Dict with statistics
    """
    stats = {
        'totalSections': len(sections),
        'provisions': 0,
        'preambles': 0,
        'metadata': 0,
        'withSummaries': 0,
        'withImpacts': 0
    }

    for section in sections:
        category_type = section.get('category', {}).get('type', '')

        if category_type == 'provision':
            stats['provisions'] += 1
        elif category_type == 'preamble':
            stats['preambles'] += 1
        elif category_type == 'metadata':
            stats['metadata'] += 1

        if section.get('summary'):
            stats['withSummaries'] += 1

        if section.get('impacts'):
            stats['withImpacts'] += 1

    return stats


def enrich_metadata(json_path: Path, force: bool = False):
    """Enrich bill JSON with metadata.

    Args:
        json_path: Path to bill JSON file
        force: If True, regenerate even if metadata exists
    """
    print(f"\nProcessing: {json_path.name}")
    print("=" * 80)

    # Load bill JSON
    with open(json_path, 'r', encoding='utf-8') as f:
        bill_data = json.load(f)

    # Check if already has metadata
    if 'metadata' in bill_data and not force:
        print("✓ Metadata already exists")
        print("  Skipping (use --force to regenerate)")
        return

    sections = bill_data.get('sections', [])
    if not sections:
        print("No sections found in bill")
        return

    # Use filename as the reliable source
    # Remove number prefix from title, but keep it in slug
    bill_title = remove_number_prefix(json_path.stem)
    bill_slug = slugify(json_path.stem)

    print(f"Bill: {bill_title}")
    print()

    # Calculate statistics
    stats = calculate_statistics(sections)

    # Find corresponding PDF path
    pdf_name = json_path.stem + '.pdf'
    pdf_path = json_path.parent.parent / 'pdfs' / pdf_name

    # Build metadata
    metadata = {
        'title': bill_title,
        'slug': bill_slug,
        'pdfPath': f'pdfs/{pdf_name}' if pdf_path.exists() else None,
        'processedAt': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        'statistics': stats
    }

    # Show metadata
    print("Metadata:")
    print(f"  Title: {metadata['title']}")
    print(f"  Slug: {metadata['slug']}")
    print(f"  PDF Path: {metadata['pdfPath']}")
    print()
    print("Statistics:")
    print(f"  Total sections: {stats['totalSections']}")
    print(f"  Provisions: {stats['provisions']}")
    print(f"  Preambles: {stats['preambles']}")
    print(f"  Metadata: {stats['metadata']}")
    print(f"  With summaries: {stats['withSummaries']}")
    print(f"  With impacts: {stats['withImpacts']}")
    print()

    # Add to bill data
    bill_data['metadata'] = metadata

    # Save
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(bill_data, f, indent=2, ensure_ascii=False)

    print(f"✓ Saved metadata to: {json_path.name}")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python 9_enrich_metadata.py <bill-json-path> [--force]")
        print()
        print("Example:")
        print("  python 9_enrich_metadata.py 'output/1. National Information Technology Authority (Amendment) Bill.json'")
        print("  python 9_enrich_metadata.py output/bill.json --force    # Regenerate")
        sys.exit(1)

    # Check for flags
    force = "--force" in sys.argv or "-f" in sys.argv

    # Get single bill path
    bill_path = Path(sys.argv[1])

    if not bill_path.exists():
        print(f"Error: File not found: {bill_path}")
        sys.exit(1)

    # Process the bill
    try:
        enrich_metadata(bill_path, force=force)
    except Exception as e:
        print(f"Error processing {bill_path.name}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
