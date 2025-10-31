#!/usr/bin/env python3
"""
Assess impact level of bill provisions using DSPy.

This script processes bill provisions and determines their impact level
(high, medium, low, or none). Only provisions with high impact will be
tagged with topics in the next step.
"""

import json
import sys
from pathlib import Path
import dspy
from dotenv import load_dotenv
import os
from shared import TOPICS, ImpactLevel

# Load environment variables
load_dotenv()


class ImpactAssessor(dspy.Signature):
    """Assess the impact level of a bill provision for each topic area.

    Base your assessment on what the provision actually requires, prohibits, or enables.
    Compare against rule of law principles and international democratic standards (GDPR, OECD guidelines,
    Commonwealth constitutions, ECHR, ICCPR).

    IMPORTANT: Assess each provision independently based on its direct impact. You may reference other
    provisions when there is a DIRECT CAUSAL RELATIONSHIP where the combination creates a rule of law
    violation that neither provision creates alone (e.g., vague terms in one provision combined with
    criminal penalties in another). However, do NOT rate a provision as severe merely because it
    "finances," "enables," "facilitates," or "exists within" a broader problematic regime.

    Valid cross-provision analysis:
    - ✓ Vague/undefined terms + enforcement penalties = Legal certainty violation
    - ✓ Broad discretionary power + inadequate oversight = Arbitrary enforcement risk
    - ✓ Coercive authority + absence of due process = Procedural fairness violation
    - ✗ Procedural/transitional provisions rated severe due to bill's substantive content
    - ✗ Definitional provisions rated severe without analyzing enforcement mechanisms

    Procedural provisions (repeals, savings, commencement, interpretation, definitions) should be rated
    based on their own text and direct effects, not the broader bill's substantive requirements.

    Evaluation framework:
    - RULE OF LAW: Legal certainty, non-arbitrariness, equality before the law, judicial independence
    - FUNDAMENTAL JUSTICE: Presumption of innocence, right to fair trial, no punishment without law
    - SEPARATION OF POWERS: Checks and balances, independent oversight, no concentration of incompatible roles
    - PROPORTIONALITY: Penalties proportionate to harm, necessity, least restrictive means
    - DUE PROCESS: Notice, hearing, appeal rights, independent review before coercive action
    - DEMOCRATIC ACCOUNTABILITY: Transparency, parliamentary oversight, limits on executive power

    Rate based on deviation from established democratic norms, not theoretical abuse scenarios.

    Impact levels (negative):
    - severe-negative: Fundamental violations of rule of law principles or international human rights standards.
                       Provisions that would be struck down as unconstitutional in established democracies or
                       violate core principles such as:
                       * Judicial independence (enforcer profits from enforcement)
                       * Proportionality (criminal penalties for administrative matters)
                       * Legal certainty (undefined criminal offenses)
                       * Due process (coercive action without hearing or review)
                       * Separation of powers (investigator + prosecutor + beneficiary in same entity)
                       * Government infrastructure control (mandatory use of government-controlled infrastructure
                         for private business operations, without precedent in OECD democracies, especially when
                         combined with penalties that include license revocation or business exclusion)
    - high-negative: Significant departures from international best practices that exceed norms in most OECD
                     countries. Creates substantial barriers, compliance burdens, or discretionary powers that,
                     while not fundamental rights violations, go beyond what is typical in functioning democracies.
                     Includes government licensing requirements that restrict market entry for activities that are
                     typically unregulated in democracies (e.g., requiring licenses to provide publicly available
                     information or data services).
    - medium-negative: Within the range of democratic practice but missing some procedural refinements or
                       safeguards. Common regulatory approaches that may be on the stricter end but are found
                       in some democratic jurisdictions. Standard government powers (licensing, exemptions,
                       enforcement) that lack optimal oversight but don't represent fundamental departures.
                       Note: Distinguish between licensing for regulated activities (finance, healthcare, aviation
                       operations) which is standard, versus licensing requirements that extend beyond regulated
                       activities to capture general market participation or information provision.
    - low-negative: Minor administrative or technical changes with negligible practical impact. Routine
                    adjustments to existing frameworks.

    Impact levels (neutral/positive):
    - neutral: No meaningful impact on this topic area
    - low-positive: Minor beneficial changes or improvements
    - medium-positive: Moderate improvements to rights, processes, or innovation
    - high-positive: Significant benefits, enables innovation, or meaningfully protects important rights
    - severe-positive: Transformative positive change for rights, freedoms, or innovation

    Topic areas:
    - Digital Innovation: Tech startups, market entry, innovation barriers, compliance costs, chilling effects on experimentation
    - Freedom of Speech: Content monitoring, censorship mechanisms, platform regulations, journalist protections
    - Privacy & Data Rights: Data protection, retention, government access, surveillance capabilities, user privacy
    - Business Environment: Operational costs, compliance requirements, data localization, market barriers, enforcement risk
    """

    bill_context: str = dspy.InputField(desc="Executive summary providing context about what the bill does")
    title: str = dspy.InputField(desc="The provision title")
    content: str = dspy.InputField(desc="The full provision content")

    digital_innovation_impact: ImpactLevel = dspy.OutputField(desc="Impact level on Digital Innovation")
    freedom_of_speech_impact: ImpactLevel = dspy.OutputField(desc="Impact level on Freedom of Speech")
    privacy_data_rights_impact: ImpactLevel = dspy.OutputField(desc="Impact level on Privacy & Data Rights")
    business_environment_impact: ImpactLevel = dspy.OutputField(desc="Impact level on Business Environment")
    confidence: float = dspy.OutputField(desc="Confidence score from 0.0 to 1.0")


def setup_dspy():
    """Initialize DSPy with Claude Haiku model."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY not found in environment variables")
        print("Please create a .env file with your Anthropic API key")
        print("See .env.example for template")
        sys.exit(1)

    # Using Claude Haiku 4.5 for detailed impact assessment
    lm = dspy.LM(model="claude-haiku-4-5", api_key=api_key)
    dspy.configure(lm=lm)

    return lm


def assess_impact(bill_context: str, title: str, raw_text: str) -> dict:
    """Assess the impact level of a provision for each topic area.

    Args:
        bill_context: Executive summary providing bill context
        title: Provision title
        raw_text: Full provision content

    Returns:
        Dict with topic names as keys and impact levels as values
        Example: {
            "Digital Innovation": "high",
            "Freedom of Speech": "none",
            "Privacy & Data Rights": "medium",
            "Business Environment": "high"
        }
    """
    assessor = dspy.ChainOfThought(ImpactAssessor)
    result = assessor(bill_context=bill_context, title=title, content=raw_text)

    return {
        "levels": {
            TOPICS[0]: result.digital_innovation_impact.value,
            TOPICS[1]: result.freedom_of_speech_impact.value,
            TOPICS[2]: result.privacy_data_rights_impact.value,
            TOPICS[3]: result.business_environment_impact.value
        },
        "reasoning": result.reasoning,
        "confidence": result.confidence,
    }


def process_bill(json_path: Path, dry_run: bool = False, force: bool = False):
    """Process a bill JSON file and assess impact for all provisions.

    Args:
        json_path: Path to bill JSON file
        dry_run: If True, only show assessments without saving
        force: If True, reassess even if impact already exists
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

    # Get executive summary for context
    executive_summary = bill_data.get('executiveSummary', '')
    if not executive_summary:
        print("Warning: No executive summary found. Impact assessment will proceed without bill context.")
        executive_summary = "No executive summary available."

    # Count provisions only
    provisions = [s for s in sections if s.get('category', {}).get('type') == 'provision']

    print(f"Processing {len(sections)} sections total")
    print(f"  Provisions to assess: {len(provisions)}")
    print()

    # Assess each provision and batch disk writes
    assessed_count = 0
    BATCH_SIZE = 10  # Save every 10 provisions

    for i, section in enumerate(sections, 1):
        category = section.get('category', {}).get('type', 'unknown')

        # Only process provisions
        if category != 'provision':
            continue

        # Skip if already assessed (unless force mode)
        if 'impact' in section and not force:
            continue

        title = section['title']
        raw_text = section.get('rawText', '')

        # Assess impact for each topic
        result = assess_impact(executive_summary, title, raw_text)

        # Add impacts to section
        section['impact'] = result
        assessed_count += 1

        # Show progress
        print(f"[{assessed_count}/{len(provisions)}] {title[:60]}")
        print(f"  Confidence: {result['confidence']}")
        for topic, level in result['levels'].items():
            if level != "none":
                print(f"  {topic}: {level.upper()}")

        # Batch disk writes - save every BATCH_SIZE provisions (unless dry run)
        if not dry_run and assessed_count % BATCH_SIZE == 0:
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(bill_data, f, indent=2, ensure_ascii=False)
            print(f"  💾 Saved progress ({assessed_count}/{len(provisions)})")
            print()

    # Final save for remaining provisions
    if not dry_run:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(bill_data, f, indent=2, ensure_ascii=False)

    print()
    print("Impact assessment complete!")
    print(f"  Assessed {assessed_count} provisions")
    print()

    if dry_run:
        print("Dry run - not saving changes")
    else:
        print(f"✓ Saved impact assessments to: {json_path.name}")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python 6_assess_impact.py <bill-json-path> [--dry-run] [--force]")
        print()
        print("Example:")
        print("  python 6_assess_impact.py 'output/1. National Information Technology Authority (Amendment) Bill.json'")
        print("  python 6_assess_impact.py output/bill.json --dry-run  # Test without saving")
        print("  python 6_assess_impact.py output/bill.json --force    # Reassess all provisions")
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
