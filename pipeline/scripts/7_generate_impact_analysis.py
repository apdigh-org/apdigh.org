#!/usr/bin/env python3
"""
Generate topic-level impact analysis for bills using DSPy.

This script takes provisions with severe/high impacts and generates
a comprehensive impact analysis for each affected topic area.
"""

import json
import sys
from pathlib import Path
import dspy
from dotenv import load_dotenv
import os
from shared import TOPICS, Topic, ImpactLevel

# Load environment variables
load_dotenv()


class TopicImpactAnalyzer(dspy.Signature):
    """Generate impact analysis for a specific topic area.

    The analysis should:
    - Assess the overall impact level considering all provisions
    - Summarize how the bill affects this topic area
    - Explain the severity and scope of the impact
    - Identify key provisions driving the impact
    - Be 2-3 paragraphs
    - Be written in accessible language
    """

    bill_context: str = dspy.InputField(desc="Executive summary providing context about what the bill does")
    topic: Topic = dspy.InputField(desc="The topic area")
    bill_title: str = dspy.InputField(desc="The bill title")
    provisions_summary: str = dspy.InputField(desc="JSON of provisions affecting this topic with their summaries")

    overall_impact: ImpactLevel = dspy.OutputField(desc="Overall impact level for this topic considering all provisions")
    impact_analysis: str = dspy.OutputField(desc="Impact analysis for this topic (2-3 paragraphs)")


def setup_dspy():
    """Initialize DSPy with Claude Sonnet model."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY not found in environment variables")
        print("Please create a .env file with your Anthropic API key")
        print("See .env.example for template")
        sys.exit(1)

    # Using Claude Sonnet for topic-level synthesis (better at connecting dots across provisions)
    lm = dspy.LM(model="claude-sonnet-4-5", api_key=api_key)
    dspy.configure(lm=lm)

    return lm


def generate_topic_impact_analysis(bill_context: str, topic: str, bill_title: str, provisions: list) -> dict:
    """Generate impact analysis for a specific topic.

    Args:
        bill_context: Executive summary providing bill context
        topic: Topic name
        bill_title: Bill title
        provisions: List of provisions affecting this topic

    Returns:
        Dict with 'score' (overall impact level) and 'analysis' (text)
    """
    # Convert to JSON for LLM
    provisions_json = json.dumps(provisions, indent=2)

    # Generate analysis
    analyzer = dspy.ChainOfThought(TopicImpactAnalyzer)
    result = analyzer(bill_context=bill_context, topic=topic, bill_title=bill_title, provisions_summary=provisions_json)

    return {
        "score": result.overall_impact.value,
        "analysis": result.impact_analysis
    }


def process_bill(json_path: Path, dry_run: bool = False, force: bool = False):
    """Process a bill JSON file and generate topic-level impact analyses.

    Args:
        json_path: Path to bill JSON file
        dry_run: If True, only show analyses without saving
        force: If True, regenerate even if exists
    """
    print(f"\nProcessing: {json_path.name}")
    print("=" * 80)

    # Load bill JSON
    with open(json_path, 'r', encoding='utf-8') as f:
        bill_data = json.load(f)

    # Check if already has impact analyses
    if 'impactAnalyses' in bill_data and not force:
        print("✓ Impact analyses already exist")
        print("  Skipping (use --force to regenerate)")
        return

    sections = bill_data.get('sections', [])
    if not sections:
        print("No sections found in bill")
        return

    # Get executive summary for context
    executive_summary = bill_data.get('executiveSummary', '')
    if not executive_summary:
        print("Warning: No executive summary found.")
        executive_summary = "No executive summary available."

    # Use filename as bill title
    bill_title = json_path.stem

    print(f"Bill: {bill_title}")
    print()

    # Collect provisions by topic (severe/high for analysis, intelligent selection for related provisions)
    topic_provisions = {topic: [] for topic in TOPICS}
    topic_severe_provisions = {topic: [] for topic in TOPICS}  # For frontend linking
    topic_high_provisions = {topic: [] for topic in TOPICS}  # Fallback for frontend linking

    for section in sections:
        if section.get('category', {}).get('type') != 'provision':
            continue

        impacts = section.get('impact', {})
        if not impacts:
            continue

        impact_levels = impacts.get('levels', {})
        for topic in TOPICS:
            impact_level = impact_levels.get(topic, 'none')
            # Include severe or high impacts for analysis (LLM sees all significant impacts)
            if impact_level in ['severe-negative', 'high-negative', 'severe-positive', 'high-positive']:
                topic_provisions[topic].append({
                    'id': section.get('id', ''),
                    'title': section.get('title', ''),
                    'rawText': section.get('rawText', ''),
                    'impact_level': impact_level
                })

            # Collect SEVERE provisions for frontend linking (priority)
            if impact_level in ['severe-negative', 'severe-positive']:
                topic_severe_provisions[topic].append(section.get('id', ''))
            # Collect HIGH provisions as fallback (if no severe exist)
            elif impact_level in ['high-negative', 'high-positive']:
                topic_high_provisions[topic].append(section.get('id', ''))

    # Generate impact analysis for each topic with severe/high impacts
    impact_analyses = {}

    for topic in TOPICS:
        provisions = topic_provisions[topic]

        if not provisions:
            print(f"{topic}: No severe/high impact provisions - skipping")
            continue

        print(f"{topic}: Analyzing {len(provisions)} provision(s)...")

        # Generate analysis
        analysis = generate_topic_impact_analysis(executive_summary, topic, bill_title, provisions)

        # Intelligently select related provisions for UI:
        # - Prefer SEVERE provisions if any exist
        # - Fall back to HIGH provisions if no severe exist
        # - This ensures users always see relevant provision links
        related_provs = topic_severe_provisions[topic] if topic_severe_provisions[topic] else topic_high_provisions[topic]

        impact_analyses[topic] = {
            "analysis": analysis,
            "affectedProvisions": len(provisions),  # Count includes high+severe (for stats)
            "relatedProvisions": related_provs  # SEVERE (preferred) or HIGH provisions (fallback)
        }

        print(f"  ✓ Generated ({len(provisions)} provisions)")
        print()

    if not impact_analyses:
        print("No topics with severe/high impact found")
        print("Skipping impact analysis generation")
        return

    # Show results
    print()
    print("=" * 80)
    print("TOPIC IMPACT ANALYSES")
    print("=" * 80)
    print()

    for topic, data in impact_analyses.items():
        print(f"## {topic}")
        print(f"({data['affectedProvisions']} provisions)")
        print()
        print(data['analysis'])
        print()
        print("-" * 80)
        print()

    if dry_run:
        print("Dry run - not saving changes")
        return

    # Add to bill data
    bill_data['impactAnalyses'] = impact_analyses

    # Save
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(bill_data, f, indent=2, ensure_ascii=False)

    print(f"✓ Saved impact analyses to: {json_path.name}")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python 7_generate_impact_analysis.py <bill-json-path> [--dry-run] [--force]")
        print()
        print("Example:")
        print("  python 7_generate_impact_analysis.py 'output/1. National Information Technology Authority (Amendment) Bill.json'")
        print("  python 7_generate_impact_analysis.py output/bill.json --dry-run  # Test without saving")
        print("  python 7_generate_impact_analysis.py output/bill.json --force    # Regenerate")
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
