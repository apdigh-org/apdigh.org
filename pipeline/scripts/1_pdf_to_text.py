#!/usr/bin/env python3
"""
Convert a bill PDF to structured text using Docling.

Exports both markdown (for human review) and structured JSON (for parsing).

Usage:
    python 1_pdf_to_text.py <path-to-pdf>

Example:
    python 1_pdf_to_text.py pdfs/cybersecurity-bill-2025.pdf
"""

import sys
import os
import json
from pathlib import Path
from docling.document_converter import DocumentConverter

def convert_pdf_to_text(pdf_path: str, output_dir: str = "output", force: bool = False):
    """
    Convert a PDF to structured markdown and JSON using Docling.

    Args:
        pdf_path: Path to the PDF file
        output_dir: Directory to save the output files
        force: If True, reconvert even if outputs already exist
    """
    # Ensure output directory exists
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Get the PDF filename without extension
    pdf_filename = Path(pdf_path).stem
    markdown_output = Path(output_dir) / f"{pdf_filename}.md"
    json_output = Path(output_dir) / f"{pdf_filename}.docling.json"

    # Check if outputs already exist
    if markdown_output.exists() and json_output.exists() and not force:
        print(f"✓ Outputs already exist:")
        print(f"  - Markdown: {markdown_output}")
        print(f"  - JSON: {json_output}")
        print(f"  Skipping PDF conversion (use --force to reconvert)")
        print(f"\nNext step:")
        print(f"  python scripts/2_docling_to_json.py {json_output}")
        return markdown_output, json_output

    print(f"Converting PDF: {pdf_path}")
    print(f"Outputs:")
    print(f"  - Markdown: {markdown_output}")
    print(f"  - JSON: {json_output}")

    # Initialize the DocumentConverter
    converter = DocumentConverter()

    # Convert the PDF
    result = converter.convert(pdf_path)

    # Export to markdown (for human review)
    markdown_content = result.document.export_to_markdown()
    with open(markdown_output, 'w', encoding='utf-8') as f:
        f.write(markdown_content)

    # Export to structured JSON (for parsing)
    doc_dict = result.document.export_to_dict()
    with open(json_output, 'w', encoding='utf-8') as f:
        json.dump(doc_dict, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Conversion complete!")
    print(f"✓ Markdown saved to: {markdown_output}")
    print(f"✓ Structured JSON saved to: {json_output}")
    print(f"\nNext step:")
    print(f"  python scripts/2_docling_to_json.py {json_output}")

    return markdown_output, json_output

def main():
    if len(sys.argv) < 2:
        print("Usage: python 1_pdf_to_text.py <path-to-pdf> [--force]")
        print("\nExample:")
        print("  python 1_pdf_to_text.py pdfs/cybersecurity-bill-2025.pdf")
        print("  python 1_pdf_to_text.py pdfs/bill.pdf --force  # Force reconversion")
        sys.exit(1)

    pdf_path = sys.argv[1]
    force = '--force' in sys.argv or '-f' in sys.argv

    if not os.path.exists(pdf_path):
        print(f"Error: PDF file not found: {pdf_path}")
        sys.exit(1)

    if not pdf_path.lower().endswith('.pdf'):
        print(f"Error: File must be a PDF: {pdf_path}")
        sys.exit(1)

    convert_pdf_to_text(pdf_path, force=force)

if __name__ == "__main__":
    main()
