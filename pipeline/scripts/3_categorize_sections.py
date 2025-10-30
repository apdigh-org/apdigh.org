#!/usr/bin/env python3
"""
Categorize bill sections using DSPy.

This script processes extracted bill sections and categorizes them into:
- provision: Actual legal provisions/clauses
- preamble: Bill title, enactment clauses, purpose statements
- metadata: Table of contents, part headings, etc.
"""

import json
import sys
from pathlib import Path
from typing import Literal
import dspy
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Section category type
SectionCategory = Literal["provision", "preamble", "metadata"]


class SectionCategorizer(dspy.Signature):
    """Categorize a bill section based on its title and content.

    Categories:
    - provision: Actual legal provisions that establish rules, powers, functions, etc.
    - preamble: Bill metadata like titles, enactment clauses, purpose statements
    - metadata: Structural elements like TOC headings, part titles, etc.
    """

    title: str = dspy.InputField(desc="The section title")
    content_preview: str = dspy.InputField(desc="First 400 characters of section content")

    category: SectionCategory = dspy.OutputField(desc="The category: provision, preamble, or metadata")


def setup_dspy():
    """Initialize DSPy with Google Gemini 2.0 Flash model."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not found in environment variables")
        print("Please create a .env file with your Google Gemini API key")
        print("See .env.example for template")
        sys.exit(1)

    # Using Gemini 2.0 Flash for fast and accurate categorization
    lm = dspy.LM(model="gemini/gemini-2.0-flash", api_key=api_key)
    dspy.configure(lm=lm)

    return lm


def categorize_section(title: str, raw_text: str) -> dict:
    """Categorize a single section using DSPy.

    Args:
        title: Section title
        raw_text: Full section content

    Returns:
        Dict with 'type' and 'reasoning' keys
    """
    # Create predictor
    categorizer = dspy.ChainOfThought(SectionCategorizer)

    # Get first 400 chars of content for preview
    content_preview = raw_text[:400] if raw_text else ""

    # Run categorization
    result = categorizer(title=title, content_preview=content_preview)

    return {
        "type": result.category,
        "reasoning": result.reasoning
    }


def process_bill(json_path: Path, dry_run: bool = False, force: bool = False):
    """Process a bill JSON file and categorize all sections.

    Args:
        json_path: Path to bill JSON file
        dry_run: If True, only show categorizations without saving
        force: If True, recategorize even if already categorized
    """
    print(f"\nProcessing: {json_path.name}")
    print("=" * 80)

    # Load bill JSON
    with open(json_path, 'r', encoding='utf-8') as f:
        bill_data = json.load(f)

    sections = bill_data.get('sections', [])

    if not sections:
        print("No sections found in bill")
        return

    print(f"Processing {len(sections)} sections")
    print()

    # Categorize each section and flush to disk after each one
    category_counts = {"provision": 0, "preamble": 0, "metadata": 0}

    for i, section in enumerate(sections, 1):
        # Skip if already categorized (unless force mode)
        if 'category' in section and not force:
            continue

        title = section['title']
        raw_text = section.get('rawText', '')

        # Categorize
        category_result = categorize_section(title, raw_text)
        category_type = category_result["type"]

        # Update counts
        category_counts[category_type] += 1

        # Add category hash to section
        section['category'] = category_result

        # Show progress
        print(f"[{i}/{len(sections)}] {category_type.upper()}: {title[:60]}")

        # Flush to disk after each section (unless dry run)
        if not dry_run:
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(bill_data, f, indent=2, ensure_ascii=False)

    print()
    print("Categorization complete!")
    print(f"  Provisions: {category_counts['provision']}")
    print(f"  Preamble: {category_counts['preamble']}")
    print(f"  Metadata: {category_counts['metadata']}")
    print()

    if dry_run:
        print("Dry run - not saving changes")
    else:
        print(f"✓ Saved categorized sections to: {json_path.name}")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python 3_categorize_sections.py <bill-json-path> [--dry-run] [--force]")
        print()
        print("Example:")
        print("  python 3_categorize_sections.py 'output/1. National Information Technology Authority (Amendment) Bill.json'")
        print("  python 3_categorize_sections.py output/bill.json --dry-run  # Test without saving")
        print("  python 3_categorize_sections.py output/bill.json --force    # Recategorize all sections")
        sys.exit(1)

    # Check for flags
    dry_run = "--dry-run" in sys.argv
    force = "--force" in sys.argv or "-f" in sys.argv

    # Get single bill path
    bill_path = Path(sys.argv[1])

    if not bill_path.exists():
        print(f"Error: File not found: {bill_path}")
        sys.exit(1)

    # Setup DSPy
    print("Initializing DSPy...")
    setup_dspy()
    print("✓ DSPy initialized")
    print()

    # Process the bill
    try:
        process_bill(bill_path, dry_run=dry_run, force=force)
    except Exception as e:
        print(f"Error processing {bill_path.name}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
