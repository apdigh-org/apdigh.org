#!/bin/bash
# Setup script for the bill processing pipeline

set -e

echo "Setting up bill processing pipeline..."
echo

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

# Activate virtual environment
echo
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo
echo "="*60
echo "Setup complete!"
echo "="*60
echo
echo "To activate the virtual environment, run:"
echo "  source venv/bin/activate"
echo
echo "To process a bill PDF:"
echo "  1. Place PDF in pdfs/ directory"
echo "  2. Run: python scripts/1_pdf_to_text.py pdfs/your-bill.pdf"
echo "  3. Run: python scripts/2_text_to_json.py output/your-bill.md"
echo "  4. Edit the generated JSON in ../src/data/bills/"
echo
