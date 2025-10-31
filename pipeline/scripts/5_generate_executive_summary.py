#!/usr/bin/env python3
"""
Generate executive summary for bills using DSPy.

This script takes categorized, summarized, and impact-assessed provisions
and generates a concise executive summary of the bill.
"""

import json
import sys
from pathlib import Path
import dspy
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()


class ExecutiveSummaryGenerator(dspy.Signature):
    """Generate a comprehensive executive summary for a Ghanaian bill.

    The summary should:
    - Be 3-4 paragraphs
    - Use minimal markdown formatting: **bold** for key terms/concerns, bullet lists where helpful
    - Provide objective analysis, NOT promotional language
    - Start with what the bill DOES (not "aims to do", "likely", or "probably")
    - Use definitive language based on actual provisions provided
    - DO NOT use speculative words like "likely", "probably", "could", "might" - you have the actual bill content
    - Identify key provisions and their practical implications
    - Highlight potential concerns, risks, or controversial aspects (use **bold** to emphasize concerns)
    - Note any provisions that affect rights, freedoms, or business operations
    - Be balanced - mention both opportunities and challenges
    - Be written in accessible language for non-experts
    - Reference Ghana (NOT Uganda or any other country)
    - Cover impacts across: Digital Innovation, Freedom of Speech, Privacy & Data Rights, Business Environment
    """

    bill_title: str = dspy.InputField(desc="The bill title")
    provisions_summary: str = dspy.InputField(desc="Complete JSON of ALL bill provisions with their plain language summaries - you have full access to the entire bill content")

    executive_summary: str = dspy.OutputField(desc="Comprehensive executive summary about this Ghanaian bill (3-4 paragraphs, definitive analysis based on actual provisions)")


def setup_dspy():
    """Initialize DSPy with Claude Sonnet model."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY not found in environment variables")
        print("Please create a .env file with your Anthropic API key")
        print("See .env.example for template")
        sys.exit(1)

    # Using Claude Sonnet 4.5 for executive summary generation (better quality for synthesis)
    # temperature=0 for consistent outputs
    lm = dspy.LM(model="claude-sonnet-4-5", api_key=api_key, temperature=0)
    dspy.configure(lm=lm)

    return lm


def generate_executive_summary(bill_title: str, sections: list) -> str:
    """Generate an executive summary for a bill.

    Args:
        bill_title: The bill title
        sections: List of section dicts with title, summary, impacts, category

    Returns:
        Executive summary string
    """
    # Collect preambles and high-impact provisions
    relevant_sections = []

    for section in sections:
        category = section.get('category', {}).get('type', '')

        # Always include preambles (bill context/purpose)
        if category == 'preamble':
            relevant_sections.append({
                'type': 'preamble',
                'title': section.get('title', ''),
                'content': section.get('rawText', '')[:500]  # First 500 chars
            })
            continue

        # Skip metadata
        if category != 'provision':
            continue

        # Include all provisions with summaries (impact assessment comes later)
        if 'summary' in section:
            relevant_sections.append({
                'type': 'provision',
                'title': section.get('title', ''),
                'summary': section.get('summary', '')
            })

    # Convert to JSON string for the LLM
    sections_json = json.dumps(relevant_sections, indent=2)

    # Generate summary
    generator = dspy.ChainOfThought(ExecutiveSummaryGenerator)
    result = generator(bill_title=bill_title, provisions_summary=sections_json)

    return result.executive_summary


def process_bill(json_path: Path, dry_run: bool = False, force: bool = False):
    """Process a bill JSON file and generate executive summary.

    Args:
        json_path: Path to bill JSON file
        dry_run: If True, only show summary without saving
        force: If True, regenerate even if summary exists
    """
    print(f"\nProcessing: {json_path.name}")
    print("=" * 80)

    # Load bill JSON
    with open(json_path, 'r', encoding='utf-8') as f:
        bill_data = json.load(f)

    # Check if already has executive summary
    if 'executiveSummary' in bill_data and not force:
        print("✓ Executive summary already exists")
        print("  Skipping (use --force to regenerate)")
        return

    sections = bill_data.get('sections', [])
    if not sections:
        print("No sections found in bill")
        return

    # Extract bill title (use filename)
    bill_title = json_path.stem

    # Count provisions
    provisions = [
        s for s in sections
        if s.get('category', {}).get('type') == 'provision'
    ]

    if not provisions:
        print("No provisions found in bill")
        return

    print(f"Bill: {bill_title}")
    print(f"Provisions: {len(provisions)}")
    print()

    # Generate executive summary
    print("Generating executive summary...")
    executive_summary = generate_executive_summary(bill_title, sections)

    # Show result
    print()
    print("=" * 80)
    print("EXECUTIVE SUMMARY")
    print("=" * 80)
    print()
    print(executive_summary)
    print()
    print("=" * 80)
    print()

    if dry_run:
        print("Dry run - not saving changes")
        return

    # Add to bill data
    bill_data['executiveSummary'] = executive_summary

    # Save
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(bill_data, f, indent=2, ensure_ascii=False)

    print(f"✓ Saved executive summary to: {json_path.name}")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python 5_generate_executive_summary.py <bill-json-path> [--dry-run] [--force]")
        print()
        print("Example:")
        print("  python 5_generate_executive_summary.py 'output/1. National Information Technology Authority (Amendment) Bill.json'")
        print("  python 5_generate_executive_summary.py output/bill.json --dry-run  # Test without saving")
        print("  python 5_generate_executive_summary.py output/bill.json --force    # Regenerate")
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
