#!/usr/bin/env python3
"""
Transform processed bill JSON to web app format and copy to src/data/bills.

This script:
1. Loads the processed bill JSON from pipeline/output
2. Transforms it to match the web app's expected Bill interface
3. Saves it to src/data/bills for the Astro web app
"""

import json
import sys
from pathlib import Path
import re
import shutil
from shared import TOPICS, slugify


def extract_bill_number(filename: str) -> str:
    """Extract bill number from filename (e.g., '1. National...' -> '1')."""
    match = re.match(r'^(\d+)\.', filename)
    return match.group(1) if match else ''


def transform_bill(bill_data: dict, filename: str) -> dict:
    """Transform pipeline JSON to web app format.

    Args:
        bill_data: Processed bill data from pipeline
        filename: Original filename (without .json extension)

    Returns:
        Dict matching the web app's Bill interface
    """
    bill_number = extract_bill_number(filename)
    bill_id = slugify(filename)

    # Get executive summary
    executive_summary = bill_data.get('executiveSummary', '')
    if not executive_summary:
        executive_summary = f"Analysis of {filename}"

    # Transform impact analyses to impacts format
    impacts = {}
    impact_analyses = bill_data.get('impactAnalyses', {})

    # Map topic names to impact keys (must match frontend IMPACT_CATEGORIES)
    topic_to_key = {
        'Digital Innovation': 'innovation',
        'Freedom of Speech': 'freedomOfSpeech',
        'Privacy & Data Rights': 'privacy',
        'Business Environment': 'business'
    }

    # Initialize impacts dict for categories with analyses
    for topic in TOPICS:
        if topic in impact_analyses:
            analysis_data = impact_analyses[topic]
            impact_key = topic_to_key.get(topic, slugify(topic))

            # The analysis field contains both score and analysis text
            analysis_content = analysis_data.get('analysis', {})

            impacts[impact_key] = {
                'score': analysis_content.get('score', 'neutral'),
                'description': analysis_content,  # Keep the whole object with score and analysis
                'relatedProvisions': []  # Will be populated from provisions
            }

    # Initialize a separate dict to collect provisions for ALL categories (even those without analyses)
    all_category_provisions = {
        'innovation': [],
        'freedomOfSpeech': [],
        'privacy': [],
        'business': []
    }

    # Transform provisions
    provisions = []
    sections = bill_data.get('sections', [])

    for section in sections:
        if section.get('category', {}).get('type') != 'provision':
            continue

        provision_id = section.get('id', '')

        # Determine which impacts this provision affects
        related_impacts = []
        impact_data = section.get('impact', {})
        if impact_data:
            impact_levels = impact_data.get('levels', {})
            for topic, level in impact_levels.items():
                # Include if not neutral or none
                if level and level != 'neutral' and level != 'none':
                    impact_key = topic_to_key.get(topic, slugify(topic))
                    related_impacts.append(impact_key)

                    # Add to impact's related provisions (for categories with analyses)
                    if impact_key in impacts:
                        if 'relatedProvisions' not in impacts[impact_key]:
                            impacts[impact_key]['relatedProvisions'] = []
                        impacts[impact_key]['relatedProvisions'].append(provision_id)
                    # Collect for categories WITHOUT analyses (for potential linking)
                    elif impact_key in all_category_provisions:
                        all_category_provisions[impact_key].append(provision_id)

        provisions.append({
            'id': provision_id,
            'section': section.get('index', ''),
            'title': section.get('title', ''),
            'plainLanguage': section.get('summary', ''),
            'rawText': section.get('rawText', ''),
            'relatedImpacts': related_impacts
        })

    # Transform key concerns
    key_concerns = []
    for concern in bill_data.get('keyConcerns', []):
        key_concerns.append({
            'id': concern.get('id', ''),
            'title': concern.get('title', ''),
            'severity': concern.get('severity', 'medium'),
            'description': concern.get('description', ''),
            'relatedProvisions': concern.get('relatedProvisions', []),
            'relatedImpacts': []  # Could be derived from provisions if needed
        })

    # Get title from metadata (cleaned, without number prefix) or fallback to filename
    metadata = bill_data.get('metadata', {})
    bill_title = metadata.get('title', filename)

    # Get PDF path from metadata if available
    pdf_path = metadata.get('pdfPath', None)

    # Add relatedProvisions to categories that don't have impact analyses
    # This ensures even categories without severe/high impacts can link to relevant provisions
    for category_key, provision_ids in all_category_provisions.items():
        if category_key not in impacts and provision_ids:
            # Category has no analysis but has some provisions - add them for frontend linking
            impacts[category_key] = {
                'score': 'neutral',
                'description': None,  # Frontend will show default message
                'relatedProvisions': provision_ids
            }

    # Build final bill object
    web_bill = {
        'id': bill_id,
        'title': bill_title,
        'summary': executive_summary,
        'pdfPath': pdf_path,  # Add PDF path for download button
        'impacts': impacts,
        'keyConcerns': key_concerns,
        'provisions': provisions,
        'notebookLMVideo': {
            'url': '',  # To be added manually
            'duration': '10:00'
        },
        'deadline': '2025-12-31',  # Default deadline
        'submissionMethod': 'Email to clerk@parliament.gov.gh',  # Default
        'relatedBills': []  # To be added manually
    }

    return web_bill


def process_bill(json_path: Path, web_app_dir: Path, dry_run: bool = False):
    """Transform and copy a bill to the web app.

    Args:
        json_path: Path to pipeline bill JSON
        web_app_dir: Path to web app's src/data/bills directory
        dry_run: If True, only show output without saving

    Note: Always overwrites existing files to ensure latest data is used.
    """
    print(f"\nProcessing: {json_path.name}")
    print("=" * 80)

    # Load pipeline JSON
    with open(json_path, 'r', encoding='utf-8') as f:
        bill_data = json.load(f)

    # Extract filename without extension
    filename = json_path.stem
    bill_id = slugify(filename)

    # Output path
    output_path = web_app_dir / f"{bill_id}.json"

    # Always overwrite (no check needed - we always want latest data)
    if output_path.exists():
        print(f"Overwriting existing file at: {output_path.relative_to(web_app_dir.parent.parent.parent)}")
    else:
        print(f"Creating new file at: {output_path.relative_to(web_app_dir.parent.parent.parent)}")

    print(f"Bill ID: {bill_id}")
    print(f"Filename: {filename}")
    print()

    # Transform
    web_bill = transform_bill(bill_data, filename)

    # Show summary
    print("Transformed Data:")
    print(f"  Title: {web_bill['title']}")
    print(f"  ID: {web_bill['id']}")
    print(f"  Impacts: {len(web_bill['impacts'])} categories")
    print(f"  Key Concerns: {len(web_bill.get('keyConcerns', []))}")
    print(f"  Provisions: {len(web_bill.get('provisions', []))}")
    print()

    if dry_run:
        print("Dry run - not saving")
        print(f"Would save to: {output_path}")
        return

    # Ensure output directory exists
    web_app_dir.mkdir(parents=True, exist_ok=True)

    # Save
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(web_bill, f, indent=2, ensure_ascii=False)

    print(f"✓ Saved to: {output_path.relative_to(web_app_dir.parent.parent.parent)}")

    # Copy PDF to public directory if available
    if web_bill.get('pdfPath'):
        pdf_filename = json_path.stem + '.pdf'
        source_pdf = json_path.parent.parent / 'pdfs' / pdf_filename

        if source_pdf.exists():
            # Create public/pdfs directory if it doesn't exist
            project_root = web_app_dir.parent.parent.parent
            public_pdfs_dir = project_root / 'public' / 'pdfs'
            public_pdfs_dir.mkdir(parents=True, exist_ok=True)

            dest_pdf = public_pdfs_dir / pdf_filename
            shutil.copy2(source_pdf, dest_pdf)
            print(f"✓ Copied PDF to: {dest_pdf.relative_to(project_root)}")
        else:
            print(f"⚠ Warning: PDF not found at {source_pdf}")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python 10_transform_for_web.py <bill-json-path> [--dry-run]")
        print()
        print("Example:")
        print("  python 10_transform_for_web.py 'output/1. National Information Technology Authority (Amendment) Bill.json'")
        print("  python 10_transform_for_web.py output/bill.json --dry-run  # Test without saving")
        print()
        print("Note: Always overwrites existing files to ensure latest data is used.")
        sys.exit(1)

    # Check for flags
    dry_run = "--dry-run" in sys.argv

    # Get bill path
    bill_path = Path(sys.argv[1])

    if not bill_path.exists():
        print(f"Error: File not found: {bill_path}")
        sys.exit(1)

    # Determine web app directory
    # Assume script is in pipeline/scripts, web app is ../src/data/bills
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    web_app_dir = project_root / 'src' / 'data' / 'bills'

    print(f"Pipeline JSON: {bill_path}")
    print(f"Web App Dir: {web_app_dir.relative_to(project_root)}")
    print()

    # Process
    try:
        process_bill(bill_path, web_app_dir, dry_run=dry_run)
    except Exception as e:
        print(f"Error processing {bill_path.name}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
