#!/bin/bash
# Convenience script to process a bill PDF through the entire pipeline

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if PDF path is provided
if [ $# -eq 0 ]; then
    echo -e "${RED}Error: No PDF file specified${NC}"
    echo
    echo "Usage: ./process_bill.sh <filename> [--force]"
    echo
    echo "Example:"
    echo "  ./process_bill.sh my-bill.pdf"
    echo "  ./process_bill.sh 'Bill Name.pdf'"
    echo "  ./process_bill.sh my-bill.pdf --force  # Force reconversion"
    echo
    exit 1
fi

PDF_INPUT="$1"
FORCE_FLAG=""

# Check for --force flag
if [[ "$2" == "--force" ]] || [[ "$2" == "-f" ]]; then
    FORCE_FLAG="--force"
fi

# If the input is just a filename (no path), look in pdfs/ directory
if [[ "$PDF_INPUT" != *"/"* ]]; then
    PDF_PATH="pdfs/$PDF_INPUT"
else
    PDF_PATH="$PDF_INPUT"
fi

# Check if PDF exists
if [ ! -f "$PDF_PATH" ]; then
    echo -e "${RED}Error: PDF file not found: $PDF_PATH${NC}"
    echo
    echo "Available PDFs in pdfs/ directory:"
    ls -1 pdfs/*.pdf 2>/dev/null || echo "  (none found)"
    echo
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${RED}Error: Virtual environment not found${NC}"
    echo "Run ./setup.sh first"
    exit 1
fi

# Activate virtual environment
echo -e "${BLUE}Activating virtual environment...${NC}"
source venv/bin/activate

# Get PDF filename without extension
PDF_FILENAME=$(basename "$PDF_PATH" .pdf)
MARKDOWN_OUTPUT="output/${PDF_FILENAME}.md"
DOCLING_JSON="output/${PDF_FILENAME}.docling.json"
JSON_OUTPUT="output/${PDF_FILENAME}.json"

echo
echo "=========================================="
echo -e "${BLUE}Processing Bill PDF${NC}"
echo "=========================================="
echo "Input:   $PDF_PATH"
echo "Outputs: $MARKDOWN_OUTPUT"
echo "         $DOCLING_JSON"
echo "         $JSON_OUTPUT"
echo

# Step 1: PDF to Text
echo -e "${YELLOW}Step 1/3: Converting PDF to structured text...${NC}"
python scripts/1_pdf_to_text.py "$PDF_PATH" $FORCE_FLAG

if [ $? -ne 0 ]; then
    echo -e "${RED}Error in PDF conversion${NC}"
    exit 1
fi

echo
echo -e "${GREEN}✓ PDF conversion complete${NC}"
echo

# Step 2: Docling JSON to Bill JSON
echo -e "${YELLOW}Step 2/3: Extracting bill sections...${NC}"
python scripts/2_docling_to_json.py "$DOCLING_JSON" $FORCE_FLAG

if [ $? -ne 0 ]; then
    echo -e "${RED}Error in section extraction${NC}"
    exit 1
fi

echo
echo -e "${GREEN}✓ Section extraction complete${NC}"
echo

# Step 3: Categorize sections with LLM
echo -e "${YELLOW}Step 3/3: Categorizing sections with LLM...${NC}"
python scripts/3_categorize_sections.py "$JSON_OUTPUT" $FORCE_FLAG

if [ $? -ne 0 ]; then
    echo -e "${RED}Error in categorization${NC}"
    exit 1
fi

echo
echo "=========================================="
echo -e "${GREEN}Pipeline Complete!${NC}"
echo "=========================================="
echo
echo "Generated files in output/ directory:"
echo "  📄 Markdown:     $MARKDOWN_OUTPUT"
echo "  📊 Docling JSON: $DOCLING_JSON"
echo "  📦 Bill JSON:    $JSON_OUTPUT (categorized)"
echo
