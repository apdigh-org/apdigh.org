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
import subprocess
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

                    # Ensure this impact category exists in impacts dict
                    if impact_key not in impacts:
                        impacts[impact_key] = {
                            'score': 'neutral',
                            'description': None,
                            'relatedProvisions': []
                        }

                    # Add this provision to the impact's related provisions list
                    impacts[impact_key]['relatedProvisions'].append(provision_id)

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


def generate_og_image_svg(web_bill: dict) -> str:
    """Generate SVG for Open Graph image using og-default.svg template.

    Args:
        web_bill: Transformed bill data

    Returns:
        SVG string for OG image (1200x630px)
    """
    import html
    title = html.escape(web_bill['title'])

    # Split title into multiple lines with max width constraint (900px at 64px font ≈ 35 chars)
    # Using character-based wrapping for precise width control
    max_chars_per_line = 35
    words = title.split()
    lines = []
    current_line = ''

    for word in words:
        test_line = (current_line + ' ' + word).strip() if current_line else word
        if len(test_line) <= max_chars_per_line:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            # Handle single words longer than max
            if len(word) > max_chars_per_line:
                lines.append(word[:max_chars_per_line - 3] + '...')
                current_line = ''
            else:
                current_line = word

    if current_line:
        lines.append(current_line)

    # Limit to 2 lines max to keep layout clean
    if len(lines) > 2:
        lines = lines[:2]
        lines[-1] = lines[-1][:max_chars_per_line - 3] + '...'

    # Generate title tspans (centered with proper line spacing)
    title_tspans = ''
    for i, line in enumerate(lines):
        dy = '0' if i == 0 else '70'
        title_tspans += f'<tspan x="600" dy="{dy}">{line}</tspan>'

    # Get top 4 impacts by severity
    IMPACT_CATEGORIES = {
        'innovation': {'name': 'Innovation', 'icon': 'bulb'},
        'freedomOfSpeech': {'name': 'Free Speech', 'icon': 'speakerphone'},
        'privacy': {'name': 'Privacy', 'icon': 'shield-lock'},
        'business': {'name': 'Business', 'icon': 'briefcase'},
    }

    impact_colors = {
        'severe-negative': '#DC2626',
        'high-negative': '#EA580C',
        'medium-negative': '#F59E0B',
        'low-negative': '#EAB308',
        'neutral': '#6B7280',
        'low-positive': '#3B82F6',
        'medium-positive': '#10B981',
        'high-positive': '#059669',
        'severe-positive': '#16A34A',
    }

    impacts = []
    for key, impact_data in web_bill.get('impacts', {}).items():
        if impact_data.get('score'):
            category = IMPACT_CATEGORIES.get(key, {})
            impacts.append({
                'key': key,
                'name': category.get('name', key),
                'icon': category.get('icon', 'alert-circle'),
                'score': impact_data.get('score', 'neutral')
            })

    # Sort by severity
    severity_order = ['severe-negative', 'high-negative', 'medium-negative', 'low-negative',
                     'neutral', 'low-positive', 'medium-positive', 'high-positive', 'severe-positive']
    impacts.sort(key=lambda x: severity_order.index(x['score']))

    # Take top 4 impacts
    top_impacts = impacts[:4]

    # Generate 2x2 grid of impact cards (centered)
    impact_cards = ''
    card_width = 250
    card_height = 90
    gap = 30
    total_width = (card_width * 2) + gap
    start_x = (1200 - total_width) // 2
    start_y = 300

    positions = [
        (start_x, start_y),
        (start_x + card_width + gap, start_y),
        (start_x, start_y + card_height + gap),
        (start_x + card_width + gap, start_y + card_height + gap)
    ]

    for i, impact in enumerate(top_impacts):
        if i >= 4:
            break
        x, y = positions[i]
        color = impact_colors.get(impact['score'], '#6B7280')
        name = html.escape(impact['name'])

        # Shorten name if too long
        if len(name) > 12:
            name = name[:10] + '...'

        # Format impact severity label
        score_map = {
            'severe-negative': 'SEVERE IMPACT',
            'high-negative': 'HIGH IMPACT',
            'medium-negative': 'MEDIUM IMPACT',
            'low-negative': 'LOW IMPACT',
            'neutral': 'NEUTRAL',
            'low-positive': 'LOW BENEFIT',
            'medium-positive': 'MEDIUM BENEFIT',
            'high-positive': 'HIGH BENEFIT',
            'severe-positive': 'MAJOR BENEFIT',
        }
        score_label = score_map.get(impact['score'], impact['score'].upper())

        impact_cards += f'''
  <g transform="translate({x}, {y})">
    <rect x="0" y="0" width="{card_width}" height="{card_height}" rx="8" fill="{color}" opacity="0.15"/>
    <rect x="0" y="0" width="{card_width}" height="{card_height}" rx="8" fill="none" stroke="{color}" stroke-width="2"/>
    <text x="{card_width // 2}" y="35" font-family="Inter, system-ui, sans-serif" font-size="20" font-weight="600" fill="{color}" text-anchor="middle">{name}</text>
    <text x="{card_width // 2}" y="70" font-family="Inter, system-ui, sans-serif" font-size="16" font-weight="600" fill="{color}" text-anchor="middle" opacity="0.8">{score_label}</text>
  </g>'''

    # Modified template: large shield watermark, centered title, impact grid
    return f'''<svg width="1200" height="630" viewBox="0 0 1200 630" xmlns="http://www.w3.org/2000/svg">
  <!-- Background -->
  <rect width="1200" height="630" fill="#FDFAF6"/>

  <!-- Ghana flag stripe at top -->
  <rect x="0" y="0" width="400" height="8" fill="#CE1126"/>
  <rect x="400" y="0" width="400" height="8" fill="#FCD116"/>
  <rect x="800" y="0" width="400" height="8" fill="#006B3F"/>

  <!-- Main content area with subtle border -->
  <rect x="60" y="80" width="1080" height="470" fill="white" stroke="#E5E7EB" stroke-width="2" rx="12"/>

  <!-- APDI Logo/Shield as watermark (huge, centered) -->
  <g transform="translate(40, -40) scale(28)" opacity="0.08">
    <path d="M20 2L4 10V18C4 27.94 10.84 37.14 20 39C29.16 37.14 36 27.94 36 18V10L20 2Z"
          fill="none" stroke="#2A8181" stroke-width="2.5"/>
    <circle cx="20" cy="20" r="2.5" fill="#2A8181"/>
    <line x1="20" y1="17.5" x2="20" y2="13" stroke="#2A8181" stroke-width="2"/>
    <line x1="20" y1="22.5" x2="20" y2="27" stroke="#2A8181" stroke-width="2"/>
    <line x1="17.5" y1="20" x2="13" y2="20" stroke="#2A8181" stroke-width="2"/>
    <line x1="22.5" y1="20" x2="27" y2="20" stroke="#2A8181" stroke-width="2"/>
  </g>

  <!-- Bill Title (larger, centered, bold) -->
  <text x="600" y="200" font-family="Inter, system-ui, sans-serif" font-size="64" font-weight="700" fill="#111827" text-anchor="middle">
    {title_tspans}
  </text>

  <!-- URL at bottom -->
  <text x="100" y="500" font-family="Inter, system-ui, sans-serif" font-size="24" font-weight="600" fill="#2A8181">
    apdigh.org
  </text>

  <!-- Impact indicators (2x2 grid) -->
  {impact_cards}
</svg>'''


def generate_concern_og_image_svg(concern: dict, bill_title: str) -> str:
    """Generate SVG for concern Open Graph image.

    Args:
        concern: Concern data with title, severity, description
        bill_title: Parent bill title for context

    Returns:
        SVG string for concern OG image (1200x630px)
    """
    import html

    concern_title = html.escape(concern['title'])
    bill_title_escaped = html.escape(bill_title)
    severity = concern.get('severity', 'medium')

    # Split concern title into multiple lines (max 35 chars per line)
    max_chars_per_line = 40
    words = concern_title.split()
    lines = []
    current_line = ''

    for word in words:
        test_line = (current_line + ' ' + word).strip() if current_line else word
        if len(test_line) <= max_chars_per_line:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            # Handle single words longer than max
            if len(word) > max_chars_per_line:
                lines.append(word[:max_chars_per_line - 3] + '...')
                current_line = ''
            else:
                current_line = word

    if current_line:
        lines.append(current_line)

    # Limit to 3 lines max
    if len(lines) > 3:
        lines = lines[:3]
        lines[-1] = lines[-1][:max_chars_per_line - 3] + '...'

    # Generate title tspans
    title_tspans = ''
    for i, line in enumerate(lines):
        dy = '0' if i == 0 else '55'
        title_tspans += f'<tspan x="600" dy="{dy}">{line}</tspan>'

    # Severity badge styling
    severity_config = {
        'critical': {
            'label': 'CRITICAL SEVERITY',
            'bg': '#FEE2E2',
            'border': '#DC2626',
            'text': '#991B1B'
        },
        'high': {
            'label': 'HIGH SEVERITY',
            'bg': '#FED7AA',
            'border': '#EA580C',
            'text': '#9A3412'
        },
        'medium': {
            'label': 'MEDIUM SEVERITY',
            'bg': '#FEF3C7',
            'border': '#F59E0B',
            'text': '#92400E'
        },
        'low': {
            'label': 'LOW SEVERITY',
            'bg': '#E5E7EB',
            'border': '#6B7280',
            'text': '#374151'
        }
    }

    config = severity_config.get(severity, severity_config['medium'])

    # Split bill title into multiple lines for context (max 60 chars per line)
    max_chars_bill = 60
    words_bill = bill_title_escaped.split()
    lines_bill = []
    current_line_bill = ''

    for word in words_bill:
        test_line = (current_line_bill + ' ' + word).strip() if current_line_bill else word
        if len(test_line) <= max_chars_bill:
            current_line_bill = test_line
        else:
            if current_line_bill:
                lines_bill.append(current_line_bill)
            current_line_bill = word

    if current_line_bill:
        lines_bill.append(current_line_bill)

    # Limit to 2 lines max
    if len(lines_bill) > 2:
        lines_bill = lines_bill[:2]
        lines_bill[-1] = lines_bill[-1][:max_chars_bill - 3] + '...'

    # Generate bill context tspans
    bill_context_tspans = ''
    for i, line in enumerate(lines_bill):
        dy = '0' if i == 0 else '30'
        bill_context_tspans += f'<tspan x="600" dy="{dy}">{line}</tspan>'

    return f'''<svg width="1200" height="630" viewBox="0 0 1200 630" xmlns="http://www.w3.org/2000/svg">
  <!-- Background -->
  <rect width="1200" height="630" fill="#FDFAF6"/>

  <!-- Ghana flag stripe at top -->
  <rect x="0" y="0" width="400" height="8" fill="#CE1126"/>
  <rect x="400" y="0" width="400" height="8" fill="#FCD116"/>
  <rect x="800" y="0" width="400" height="8" fill="#006B3F"/>

  <!-- Main content area with subtle border -->
  <rect x="60" y="80" width="1080" height="470" fill="white" stroke="#E5E7EB" stroke-width="2" rx="12"/>

  <!-- APDI Logo/Shield as watermark (huge, centered) -->
  <g transform="translate(40, -40) scale(28)" opacity="0.08">
    <path d="M20 2L4 10V18C4 27.94 10.84 37.14 20 39C29.16 37.14 36 27.94 36 18V10L20 2Z"
          fill="none" stroke="#2A8181" stroke-width="2.5"/>
    <circle cx="20" cy="20" r="2.5" fill="#2A8181"/>
    <line x1="20" y1="17.5" x2="20" y2="13" stroke="#2A8181" stroke-width="2"/>
    <line x1="20" y1="22.5" x2="20" y2="27" stroke="#2A8181" stroke-width="2"/>
    <line x1="17.5" y1="20" x2="13" y2="20" stroke="#2A8181" stroke-width="2"/>
    <line x1="22.5" y1="20" x2="27" y2="20" stroke="#2A8181" stroke-width="2"/>
  </g>

  <!-- Severity Badge (top center) -->
  <g transform="translate(600, 150)">
    <rect x="-120" y="-20" width="240" height="50" rx="25" fill="{config['bg']}" stroke="{config['border']}" stroke-width="3"/>
    <text x="0" y="12" font-family="Inter, system-ui, sans-serif" font-size="18" font-weight="700" fill="{config['text']}" text-anchor="middle">{config['label']}</text>
  </g>

  <!-- Concern Title (centered, bold) -->
  <text x="600" y="270" font-family="Inter, system-ui, sans-serif" font-size="48" font-weight="700" fill="#111827" text-anchor="middle">
    {title_tspans}
  </text>

  <!-- Bill Context -->
  <text x="600" y="420" font-family="Inter, system-ui, sans-serif" font-size="20" font-weight="600" fill="#6B7280" text-anchor="middle">
    {bill_context_tspans}
  </text>

  <!-- URL at bottom -->
  <text x="100" y="500" font-family="Inter, system-ui, sans-serif" font-size="24" font-weight="600" fill="#2A8181">
    apdigh.org
  </text>
</svg>'''


def convert_svg_to_png(svg_path: Path, png_path: Path) -> bool:
    """Convert SVG to PNG using rsvg-convert or ImageMagick fallback.

    Args:
        svg_path: Input SVG file
        png_path: Output PNG file

    Returns:
        True if successful, False otherwise
    """
    # Try rsvg-convert first (best quality)
    try:
        cmd = ['rsvg-convert', '-w', '1200', '-h', '630', '-o', str(png_path), str(svg_path)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0 and png_path.exists():
            return True
    except FileNotFoundError:
        pass

    # Fallback to ImageMagick (magick)
    try:
        cmd = ['magick', str(svg_path), '-resize', '1200x630', str(png_path)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0 and png_path.exists():
            return True
    except FileNotFoundError:
        pass

    # Fallback to ImageMagick 6 (convert)
    try:
        cmd = ['convert', str(svg_path), '-resize', '1200x630', str(png_path)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0 and png_path.exists():
            return True
    except FileNotFoundError:
        pass

    # No converter found
    print("  ⚠ Warning: No SVG converter found. Install one to generate PNG OG images.")
    print("     macOS: brew install librsvg  (or brew install imagemagick)")
    print("     Ubuntu: sudo apt-get install librsvg2-bin  (or imagemagick)")
    return False


def generate_og_image(web_bill: dict, bill_id: str, project_root: Path):
    """Generate Open Graph image for the bill.

    Args:
        web_bill: Transformed bill data
        bill_id: Bill slug ID
        project_root: Project root directory
    """
    try:
        # Create output directory
        og_dir = project_root / 'public' / 'images' / 'og'
        og_dir.mkdir(parents=True, exist_ok=True)

        # Generate SVG
        svg_content = generate_og_image_svg(web_bill)
        svg_path = og_dir / f"{bill_id}.svg"

        with open(svg_path, 'w', encoding='utf-8') as f:
            f.write(svg_content)

        print(f"✓ Generated OG SVG: {svg_path.relative_to(project_root)}")

        # Convert to PNG
        png_path = og_dir / f"{bill_id}.png"
        if convert_svg_to_png(svg_path, png_path):
            size_kb = png_path.stat().st_size // 1024
            print(f"✓ Converted to PNG: {png_path.relative_to(project_root)} ({size_kb}KB)")
        else:
            print(f"  ⚠ PNG conversion failed, but SVG is available")

    except Exception as e:
        print(f"  ⚠ Warning: Could not generate OG image: {e}")


def generate_concern_og_images(web_bill: dict, bill_id: str, project_root: Path):
    """Generate Open Graph images for all concerns in the bill.

    Args:
        web_bill: Transformed bill data
        bill_id: Bill slug ID
        project_root: Project root directory
    """
    concerns = web_bill.get('keyConcerns', [])
    if not concerns:
        return

    try:
        # Create concerns OG directory
        og_concerns_dir = project_root / 'public' / 'images' / 'og' / 'concerns'
        og_concerns_dir.mkdir(parents=True, exist_ok=True)

        bill_title = web_bill.get('title', 'Bill')

        for concern in concerns:
            concern_id = concern.get('id', '')
            if not concern_id:
                continue

            # Generate SVG
            svg_content = generate_concern_og_image_svg(concern, bill_title)
            filename_base = f"{bill_id}_{concern_id}"
            svg_path = og_concerns_dir / f"{filename_base}.svg"

            with open(svg_path, 'w', encoding='utf-8') as f:
                f.write(svg_content)

            print(f"  ✓ Generated concern OG SVG: {svg_path.relative_to(project_root)}")

            # Convert to PNG
            png_path = og_concerns_dir / f"{filename_base}.png"
            if convert_svg_to_png(svg_path, png_path):
                size_kb = png_path.stat().st_size // 1024
                print(f"  ✓ Converted to PNG: {png_path.relative_to(project_root)} ({size_kb}KB)")

    except Exception as e:
        print(f"  ⚠ Warning: Could not generate concern OG images: {e}")


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

    # Get project root
    project_root = web_app_dir.parent.parent.parent

    # Copy PDF to public directory if available
    if web_bill.get('pdfPath'):
        pdf_filename = json_path.stem + '.pdf'
        source_pdf = json_path.parent.parent / 'pdfs' / pdf_filename

        if source_pdf.exists():
            # Create public/pdfs directory if it doesn't exist
            public_pdfs_dir = project_root / 'public' / 'pdfs'
            public_pdfs_dir.mkdir(parents=True, exist_ok=True)

            dest_pdf = public_pdfs_dir / pdf_filename
            shutil.copy2(source_pdf, dest_pdf)
            print(f"✓ Copied PDF to: {dest_pdf.relative_to(project_root)}")
        else:
            print(f"⚠ Warning: PDF not found at {source_pdf}")

    # Generate Open Graph image
    generate_og_image(web_bill, bill_id, project_root)

    # Generate concern OG images
    generate_concern_og_images(web_bill, bill_id, project_root)


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
