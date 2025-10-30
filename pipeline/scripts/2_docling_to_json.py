#!/usr/bin/env python3
"""
Extract bill provisions from Docling JSON.

Simple rule: Section headers are provision boundaries.
Everything between section headers is the provision content, formatted as markdown.
"""

import json
import re
import sys
from pathlib import Path


def slugify(text: str) -> str:
    """Convert text to a URL-friendly slug."""
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'\s+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text.strip('-')


def infer_document_structure(texts: list) -> dict:
    """
    Analyze the document to infer structure based on spatial properties.
    Returns indentation levels, header positions, etc.
    """
    from collections import Counter

    # Collect left margins and Y-coordinates
    left_margins = []
    y_coords = []

    for item in texts:
        if item.get('prov'):
            bbox = item.get('prov', [{}])[0].get('bbox', {})
            left = bbox.get('l', 0)
            y = bbox.get('t', 0)
            label = item.get('label', '')
            page = item.get('prov', [{}])[0].get('page_no', 0)

            # Skip TOC pages
            if page <= 2:
                continue

            # Skip headers/footers (they're at extreme Y positions)
            if label in ['page_header', 'page_footer']:
                continue

            if left > 0:
                left_margins.append(left)
            if y > 0:
                y_coords.append(y)

    # Find common left margin values (indentation levels)
    # Group similar values (within 5 points tolerance)
    margin_counter = Counter([round(m / 5) * 5 for m in left_margins])
    common_margins = sorted([m for m, count in margin_counter.items() if count >= 5])

    # Find top Y-coordinate range (for page headers)
    y_coords_sorted = sorted(y_coords, reverse=True)
    top_10_percent = y_coords_sorted[:len(y_coords_sorted)//10] if y_coords_sorted else []
    header_y_threshold = min(top_10_percent) if top_10_percent else 800

    structure = {
        'indentation_levels': common_margins,
        'base_margin': common_margins[0] if common_margins else 72,
        'header_y_threshold': header_y_threshold,
        'centered_threshold': (max(common_margins) + min(common_margins)) / 2 if common_margins else 150
    }

    return structure


def format_as_markdown(text: str, label: str, left_margin: float = 0, doc_structure: dict = None) -> str:
    """Format text based on its Docling label and indentation."""
    if not text:
        return ""

    if label == 'section_header':
        return f"## {text}"
    elif label == 'list_item':
        # Use inferred indentation levels from document structure
        if doc_structure:
            indentation_levels = doc_structure.get('indentation_levels', [])

            # Find which indentation level this item belongs to
            # Default to base level (0)
            indent_level = 0
            for i, level_margin in enumerate(indentation_levels):
                # Match within 5 points tolerance
                if abs(left_margin - level_margin) < 5:
                    indent_level = i
                    break

            # Generate markdown with appropriate indentation
            # Each level adds 2 spaces
            indent = '  ' * indent_level
            return f"{indent}- {text}"
        else:
            # Fallback to simple formatting
            return f"- {text}"
    elif label == 'table':
        return text  # Tables are already formatted as markdown
    else:
        return text


def table_to_markdown(table_data: dict) -> str:
    """Convert Docling table data to markdown table."""
    try:
        table_cells = table_data.get('table_cells', [])
        if not table_cells:
            return ""

        # Find grid dimensions
        max_row = max(cell['end_row_offset_idx'] for cell in table_cells)
        max_col = max(cell['end_col_offset_idx'] for cell in table_cells)

        # Create grid
        grid = [['' for _ in range(max_col)] for _ in range(max_row)]

        # Fill grid with cell text
        for cell in table_cells:
            row = cell['start_row_offset_idx']
            col = cell['start_col_offset_idx']
            text = cell.get('text', '').strip()
            if row < max_row and col < max_col:
                grid[row][col] = text

        # Build markdown table
        if not grid:
            return ""

        lines = []
        # Header row
        lines.append('| ' + ' | '.join(grid[0]) + ' |')
        # Separator
        lines.append('| ' + ' | '.join(['---'] * len(grid[0])) + ' |')
        # Data rows
        for row in grid[1:]:
            lines.append('| ' + ' | '.join(row) + ' |')

        return '\n'.join(lines)
    except Exception:
        return "[Table extraction failed]"


def extract_provisions(doc_dict: dict) -> list:
    """
    Extract provisions from Docling JSON.

    Section headers start new provisions.
    Everything until the next section header is content.
    """
    texts = doc_dict.get('texts', [])
    tables = doc_dict.get('tables', [])

    # Infer document structure from spatial properties
    doc_structure = infer_document_structure(texts)
    print(f"Inferred document structure:")
    print(f"  Indentation levels: {doc_structure['indentation_levels']}")
    print(f"  Base margin: {doc_structure['base_margin']}")
    print(f"  Header Y threshold: {doc_structure['header_y_threshold']:.1f}")
    print()

    # Convert tables to text items with markdown
    table_items = []
    for table in tables:
        page = table.get('prov', [{}])[0].get('page_no', 0)
        bbox = table.get('prov', [{}])[0].get('bbox', {})
        table_md = table_to_markdown(table.get('data', {}))

        if table_md:
            table_items.append({
                'text': table_md,
                'label': 'table',
                'prov': [{
                    'page_no': page,
                    'bbox': bbox
                }]
            })

    # Combine texts and tables
    all_items = texts + table_items

    # Sort by page and Y-coordinate (top to bottom, left to right)
    def sort_key(item):
        prov = item.get('prov', [{}])[0]
        page = prov.get('page_no', 0)
        bbox = prov.get('bbox', {})
        y = bbox.get('t', 0)
        x = bbox.get('l', 0)
        return (page, -y, x)  # negative y because PDF coords are bottom-left origin

    sorted_items = sorted(all_items, key=sort_key)

    provisions = []
    current_provision = None

    for item in sorted_items:
        text = item.get('text', '').strip()
        label = item.get('label', '')
        page = item.get('prov', [{}])[0].get('page_no', 0)

        # Skip table of contents and headers/footers
        if page <= 2 or label in ['page_header', 'page_footer'] or not text:
            continue

        # Skip the bill title banner (centered header at top of pages)
        # It has left margin ~168 and Y-coordinate ~804
        bbox = item.get('prov', [{}])[0].get('bbox', {})
        left_margin = bbox.get('l', 0)
        y_coord = bbox.get('t', 0)

        # Bill title banner is centered and at top of page
        # Use inferred structure to detect
        base_margin = doc_structure['base_margin']
        centered_threshold = doc_structure['centered_threshold']
        header_y_threshold = doc_structure['header_y_threshold']

        is_bill_title_banner = (left_margin > centered_threshold) and (y_coord > header_y_threshold)
        if is_bill_title_banner:
            continue

        # Check if this is a section header that starts a new provision
        is_provision_header = False
        if label == 'section_header':
            # Use left margin to identify real provision boundaries
            # Real provisions are left-aligned at base margin
            # Indented/centered headers are content (quoted sections, page titles, etc.)
            bbox = item.get('prov', [{}])[0].get('bbox', {})
            left_margin = bbox.get('l', 0)

            # Left-aligned section headers (at base margin OR first few indentation levels)
            # Check first 3 indentation levels to catch section headers
            indentation_levels = doc_structure.get('indentation_levels', [])
            leftmost_margins = indentation_levels[:3] if len(indentation_levels) >= 3 else indentation_levels
            is_left_aligned = any(abs(left_margin - margin) < 5 for margin in leftmost_margins)

            if is_left_aligned:
                import re
                # Exclude numbered clauses (they're content, not boundaries)
                # Matches: "1. ", "2 ", "(1)", "(2) ", etc.
                is_numbered_clause = bool(re.match(r'^(\d+[\.\s]|\(\d+\))', text))
                # Exclude quoted section names (they're content being added)
                is_quoted = text.startswith("'") or text.startswith('"')
                # Exclude list items like "(a)", "(b)", "(i)", etc.
                is_lettered_list = bool(re.match(r'^\([a-z]\)', text))

                # If it's left-aligned and not a numbered clause, quote, or lettered list, it's a section boundary
                # Let LLM post-processing determine if it's a real provision or TOC/metadata
                if not is_numbered_clause and not is_quoted and not is_lettered_list:
                    is_provision_header = True

        if is_provision_header:
            # Save previous provision
            if current_provision:
                provisions.append(current_provision)

            # Start new provision
            current_provision = {
                'title': text,
                'content': []
            }
        elif current_provision:
            # Add content to current provision
            formatted = format_as_markdown(text, label, left_margin, doc_structure)
            if formatted:
                current_provision['content'].append(formatted)

    # Don't forget the last provision
    if current_provision:
        provisions.append(current_provision)

    return provisions


def create_bill_json(docling_json_path: str):
    """Create bill JSON from Docling JSON."""
    docling_path = Path(docling_json_path)

    if not docling_path.exists():
        print(f"Error: File not found: {docling_json_path}")
        sys.exit(1)

    # Load Docling JSON
    with open(docling_path, 'r', encoding='utf-8') as f:
        doc_dict = json.load(f)

    # Extract provisions
    provisions = extract_provisions(doc_dict)

    print("=" * 80)
    print(f"EXTRACTED {len(provisions)} PROVISIONS")
    print("=" * 80)
    print()

    # Show preview
    for prov in provisions[:3]:
        content_preview = '\n'.join(prov['content'][:5])
        print(f"{prov['title']}")
        print(content_preview[:200] + "..." if len(content_preview) > 200 else content_preview)
        print("-" * 40)
        print()

    if len(provisions) > 3:
        print(f"... and {len(provisions) - 3} more provisions")
        print()

    # Create bill JSON structure
    # Remove .docling suffix - keep original filename casing for output
    base_name = docling_path.stem.replace('.docling', '')
    # Use slugified version only for internal bill ID
    bill_id = slugify(base_name)

    # Extract bill title from Docling JSON
    bill_title = "CYBERSECURITY (AMENDMENT) BILL, 2025"
    for item in doc_dict.get('texts', []):
        if item.get('label') == 'section_header' and 'BILL' in item.get('text', ''):
            bill_title = item.get('text', '').strip()
            break

    # Build provisions array - minimal structure for LLM post-processing
    bill_provisions = []
    for i, prov in enumerate(provisions, 1):
        raw_text = '\n\n'.join(prov['content']).strip()

        bill_provisions.append({
            "id": slugify(prov['title']),
            "index": i,
            "title": prov['title'],
            "rawText": raw_text
        })

    bill_data = {
        "sections": bill_provisions
    }

    # Write output
    output_path = docling_path.parent / f"{base_name}.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(bill_data, f, indent=2, ensure_ascii=False)

    print("=" * 80)
    print(f"✓ Bill JSON created: {output_path}")
    print("=" * 80)
    print()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python 2_docling_to_json.py <docling-json-path>")
        sys.exit(1)

    create_bill_json(sys.argv[1])
