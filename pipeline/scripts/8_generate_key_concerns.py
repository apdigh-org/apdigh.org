#!/usr/bin/env python3
"""
Generate key concerns for bills using DSPy.

This script identifies the most critical issues in a bill based on
severe/high impact provisions and generates structured concerns.
"""

import json
import sys
from pathlib import Path
from typing import List
import dspy
from dotenv import load_dotenv
import os
import re
from shared import TOPICS, Topic, Severity

# Load environment variables
load_dotenv()


class KeyConcernGenerator(dspy.Signature):
    """Generate a key concern from a single high-impact provision.

    When identifying concerns, think about:

    1. WHAT MAKES THIS CRITICAL:
       - Undefined terms that grant arbitrary power ("critical data", "public interest")
       - Perverse incentives (enforcer profits from enforcement)
       - Disproportionate penalties (imprisonment for business activities)
       - Data localization requirements with criminal sanctions
       - Surveillance infrastructure without adequate oversight

    2. WHO IS HARMED:
       - Startups and SMEs facing disproportionate compliance burdens
       - Citizens facing surveillance or speech restrictions
       - Journalists, activists, researchers at risk of prosecution
       - Foreign companies effectively locked out of market

    3. ABUSE POTENTIAL:
       - Could this be weaponized against political opponents?
       - Does vague language enable selective enforcement?
       - Are penalties severe enough to create chilling effects?
       - What's the realistic worst-case scenario?

    A key concern should:
    - Have a clear, attention-grabbing title (5-8 words)
    - Explain the specific problem this provision creates (2-3 sentences)
    - Focus on practical impact on rights, freedoms, or businesses
    - Be written in accessible language for non-experts
    - Use markdown formatting: **bold** for key terms, quoted provisions, or critical issues
    - Be specific to this particular provision's issue
    - Consider the broader bill context when assessing severity
    - Highlight institutional design flaws, not just direct impacts
    - Quote specific language from the raw text when relevant
    - Use the impact analysis to identify the core problem
    """

    bill_context: str = dspy.InputField(desc="Executive summary providing context about what the bill does")
    topic: Topic = dspy.InputField(desc="The affected topic area")
    provision_title: str = dspy.InputField(desc="The provision's title")
    provision_raw_text: str = dspy.InputField(desc="The actual legal text of the provision")
    provision_summary: str = dspy.InputField(desc="Plain language summary of what the provision does")
    impact_reasoning: str = dspy.InputField(desc="Detailed impact analysis identifying specific problems, institutional design flaws, and critical issues")
    impact_level: str = dspy.InputField(desc="The impact level (severe-negative or high-negative)")

    title: str = dspy.OutputField(desc="Concern title (5-8 words, attention-grabbing)")
    description: str = dspy.OutputField(desc="Concern description (2-3 sentences explaining the problem, use markdown formatting)")
    severity: Severity = dspy.OutputField(desc="Severity level: critical, high, medium or low")


def setup_dspy():
    """Initialize DSPy with Claude Sonnet model."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY not found in environment variables")
        print("Please create a .env file with your Anthropic API key")
        print("See .env.example for template")
        sys.exit(1)

    # Using Claude Sonnet 4.5 for key concerns (better at identifying critical issues)
    # temperature=0 for consistent outputs
    lm = dspy.LM(model="claude-sonnet-4-5", api_key=api_key, temperature=0)
    dspy.configure(lm=lm)

    return lm


def slugify(text: str) -> str:
    """Convert text to a URL-friendly slug."""
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'\s+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text.strip('-')


def generate_key_concern(bill_context: str, topic: str, provision: dict) -> dict:
    """Generate a key concern for a single provision.

    Args:
        bill_context: Executive summary for context
        topic: Topic name
        provision: Provision dict with id, title, summary, raw_text, impact_reasoning, impact_level

    Returns:
        Concern dict with id, title, description, severity, relatedProvisions
    """
    # Generate concern
    generator = dspy.ChainOfThought(KeyConcernGenerator)
    result = generator(
        bill_context=bill_context,
        topic=topic,
        provision_title=provision['title'],
        provision_raw_text=provision['raw_text'],
        provision_summary=provision['summary'],
        impact_reasoning=provision['impact_reasoning'],
        impact_level=provision['impact_level']
    )

    return {
        "id": slugify(result.title),
        "title": result.title,
        "severity": result.severity.value,
        "description": result.description,
        "relatedProvisions": [provision['id']]
    }


def process_bill(json_path: Path, dry_run: bool = False, force: bool = False):
    """Process a bill JSON file and generate key concerns.

    Args:
        json_path: Path to bill JSON file
        dry_run: If True, only show concerns without saving
        force: If True, regenerate even if exists
    """
    print(f"\nProcessing: {json_path.name}")
    print("=" * 80)

    # Load bill JSON
    with open(json_path, 'r', encoding='utf-8') as f:
        bill_data = json.load(f)

    # Check if already has key concerns
    if 'keyConcerns' in bill_data and not force:
        print("✓ Key concerns already exist")
        print("  Skipping (use --force to regenerate)")
        return

    sections = bill_data.get('sections', [])
    if not sections:
        print("No sections found in bill")
        return

    # Use filename as bill title
    bill_title = json_path.stem

    print(f"Bill: {bill_title}")

    # Get executive summary for context
    executive_summary = bill_data.get('executiveSummary', '')
    if not executive_summary:
        print("Warning: No executive summary found. Key concerns will be generated without bill context.")
        executive_summary = "No executive summary available."

    print()

    # Collect ALL provisions with severe-negative or high-negative impacts
    # Strategy: Use ALL severe and high provisions (no caps)
    severe_provisions = []
    high_provisions = []

    for section in sections:
        if section.get('category', {}).get('type') != 'provision':
            continue

        impact = section.get('impact', {})
        if not impact:
            continue

        impact_levels = impact.get('levels', {})
        confidence = impact.get('confidence', 0.5)

        # Find the first severe-negative or high-negative impact for this provision
        severe_impact = None
        high_impact = None

        for topic in TOPICS:
            impact_level = impact_levels.get(topic, 'none')
            if impact_level == 'severe-negative' and not severe_impact:
                severe_impact = {'topic': topic, 'level': impact_level}
            elif impact_level == 'high-negative' and not high_impact:
                high_impact = {'topic': topic, 'level': impact_level}

        provision_data = {
            'id': section.get('id', ''),
            'title': section.get('title', ''),
            'raw_text': section.get('rawText', ''),
            'summary': section.get('summary', ''),
            'impact_reasoning': impact.get('reasoning', ''),
            'confidence': confidence
        }

        if severe_impact:
            severe_provisions.append({**provision_data, 'impact_level': severe_impact['level'], 'topic': severe_impact['topic']})
        elif high_impact:
            high_provisions.append({**provision_data, 'impact_level': high_impact['level'], 'topic': high_impact['topic']})

    # Sort high provisions by confidence (descending) for consistent ordering
    high_provisions.sort(key=lambda x: x['confidence'], reverse=True)

    # Use ALL severe and high provisions (no caps)
    impactful_provisions = severe_provisions + high_provisions

    if not impactful_provisions:
        print("No provisions with severe-negative or high-negative impact found")
        print("Clearing any existing key concerns")
        bill_data['keyConcerns'] = []
        with open(json_path, 'w') as f:
            json.dump(bill_data, f, indent=2)
        print("✓ Cleared key concerns")
        return

    print(f"Found {len(severe_provisions)} SEVERE-negative provision(s)")
    print(f"Found {len(high_provisions)} HIGH-negative provision(s)")
    print(f"Generating {len(impactful_provisions)} key concern(s) from ALL severe and high provisions")
    print()

    # Generate one concern per provision
    key_concerns = []

    for i, provision in enumerate(impactful_provisions, 1):
        print(f"[{i}/{len(impactful_provisions)}] {provision['topic']}: {provision['title'][:50]}...")

        concern = generate_key_concern(executive_summary, provision['topic'], provision)
        key_concerns.append(concern)

        print(f"  ✓ {concern['severity'].upper()}: {concern['title']}")
        print()

    # Sort by severity (critical > high > medium > low)
    severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
    key_concerns.sort(key=lambda x: severity_order.get(x['severity'], 99))

    # Show results
    print()
    print("=" * 80)
    print(f"KEY CONCERNS ({len(key_concerns)})")
    print("=" * 80)
    print()

    for i, concern in enumerate(key_concerns, 1):
        print(f"{i}. [{concern['severity'].upper()}] {concern['title']}")
        print(f"   {concern['description']}")
        print(f"   Related provisions: {len(concern['relatedProvisions'])}")
        print()

    if dry_run:
        print("Dry run - not saving changes")
        return

    # Add to bill data
    bill_data['keyConcerns'] = key_concerns

    # Save
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(bill_data, f, indent=2, ensure_ascii=False)

    print(f"✓ Saved {len(key_concerns)} key concerns to: {json_path.name}")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python 8_generate_key_concerns.py <bill-json-path> [--dry-run] [--force]")
        print()
        print("Example:")
        print("  python 8_generate_key_concerns.py 'output/1. National Information Technology Authority (Amendment) Bill.json'")
        print("  python 8_generate_key_concerns.py output/bill.json --dry-run  # Test without saving")
        print("  python 8_generate_key_concerns.py output/bill.json --force    # Regenerate")
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
