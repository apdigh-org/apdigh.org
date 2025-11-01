#!/usr/bin/env python3
"""
Generate plain language summaries for bill sections using DSPy.

This script processes categorized bill sections and generates accessible
summaries that explain what each section does in simple language.
"""

import json
import sys
from pathlib import Path
import dspy
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()


class SectionSummarizer(dspy.Signature):
    """Generate a plain language summary of a bill provision.

    The summary should:
    - Explain what the provision does in simple, accessible language
    - Avoid legal jargon where possible
    - Be 3-5 sentences maximum
    - Focus on the practical impact or purpose
    - Remain neutral and descriptive - do not characterize provisions as positive or negative
    """

    title: str = dspy.InputField(desc="The provision title")
    content: str = dspy.InputField(desc="The full provision content")

    summary: str = dspy.OutputField(desc="Plain language summary (2-3 sentences)")


def setup_dspy():
    """Initialize DSPy with Google Gemini 2.0 Flash model."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not found in environment variables")
        print("Please create a .env file with your Google Gemini API key")
        print("See .env.example for template")
        sys.exit(1)

    # Using Gemini 2.0 Flash for fast and accurate summarization
    lm = dspy.LM(model="gemini/gemini-2.0-flash", api_key=api_key)
    dspy.configure(lm=lm)

    return lm


def summarize_section(title: str, raw_text: str) -> str:
    """Generate a plain language summary for a single provision.

    Args:
        title: Provision title
        raw_text: Full provision content

    Returns:
        Plain language summary string
    """
    summarizer = dspy.ChainOfThought(SectionSummarizer)
    result = summarizer(title=title, content=raw_text)

    return result.summary


def process_bill(json_path: Path, dry_run: bool = False, force: bool = False):
    """Process a bill JSON file and generate summaries for all sections.

    Args:
        json_path: Path to bill JSON file
        dry_run: If True, only show summaries without saving
        force: If True, regenerate summaries even if they already exist
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

    # Count provisions only
    provisions = [s for s in sections if s.get('category', {}).get('type') == 'provision']

    print(f"Processing {len(sections)} sections total")
    print(f"  Provisions to summarize: {len(provisions)}")
    print()

    # Summarize each provision and batch disk writes
    summarized_count = 0
    BATCH_SIZE = 10  # Save every 10 provisions

    for i, section in enumerate(sections, 1):
        category = section.get('category', {}).get('type', 'unknown')

        # Only process provisions
        if category != 'provision':
            continue

        # Skip if already summarized (unless force mode)
        if 'summary' in section and not force:
            continue

        title = section['title']
        raw_text = section.get('rawText', '')

        # Generate summary
        summary = summarize_section(title, raw_text)

        # Add summary to section
        section['summary'] = summary
        summarized_count += 1

        # Show progress
        print(f"[{summarized_count}/{len(provisions)}] {title[:60]}")
        print(f"  → {summary}")
        print()

        # Batch disk writes - save every BATCH_SIZE provisions (unless dry run)
        if not dry_run and summarized_count % BATCH_SIZE == 0:
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(bill_data, f, indent=2, ensure_ascii=False)
            print(f"  💾 Saved progress ({summarized_count}/{len(provisions)})")
            print()

    # Final save for remaining provisions
    if not dry_run:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(bill_data, f, indent=2, ensure_ascii=False)

    print()
    print("Summarization complete!")
    print(f"  Summarized {summarized_count} provisions")
    print()

    if dry_run:
        print("Dry run - not saving changes")
    else:
        print(f"✓ Saved summaries to: {json_path.name}")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python 4_summarize_sections.py <bill-json-path> [--dry-run] [--force]")
        print()
        print("Example:")
        print("  python 4_summarize_sections.py 'output/1. National Information Technology Authority (Amendment) Bill.json'")
        print("  python 4_summarize_sections.py output/bill.json --dry-run  # Test without saving")
        print("  python 4_summarize_sections.py output/bill.json --force    # Regenerate all summaries")
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
