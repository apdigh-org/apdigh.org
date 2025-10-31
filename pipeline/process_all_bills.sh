#!/bin/bash
# Process all bill PDFs in pdfs/ directory through the complete pipeline

set -e

# Parse arguments
FORCE_FLAG=""
if [[ "$1" == "--force" ]] || [[ "$1" == "-f" ]]; then
    FORCE_FLAG="--force"
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${RED}Error: Virtual environment not found${NC}"
    echo "Run ./setup.sh first"
    exit 1
fi

# Find all PDFs
PDF_FILES=(pdfs/*.pdf)

if [ ! -e "${PDF_FILES[0]}" ]; then
    echo -e "${RED}Error: No PDF files found in pdfs/ directory${NC}"
    exit 1
fi

PDF_COUNT=${#PDF_FILES[@]}

echo
echo "================================================================================"
echo -e "${BLUE}Process All Bills${NC}"
echo "================================================================================"
echo -e "Found ${CYAN}${PDF_COUNT}${NC} PDF files in pdfs/ directory"
if [ -n "$FORCE_FLAG" ]; then
    echo -e "${YELLOW}Force mode: will reprocess all files${NC}"
fi
echo
echo "Each bill will be processed through:"
echo "  1. PDF → Docling JSON (OCR + structure extraction)"
echo "  2. Docling JSON → Bill JSON (section extraction)"
echo "  3. Bill JSON → Categorized (LLM categorization)"
echo "  4. Categorized → Summarized (plain language summaries)"
echo "  5. Summarized → Executive Summary (bill overview)"
echo "  6. Executive Summary → Impact Assessed (topic-specific impact levels)"
echo "  7. Impact Assessed → Impact Analyses (topic-level analyses)"
echo "  8. Impact Analyses → Key Concerns (critical issues)"
echo "  9. Key Concerns → Metadata Enriched (add publication info, etc.)"
echo " 10. Metadata → Web App (transformed and copied to src/data/bills)"
echo
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
fi
echo

SUCCESS_COUNT=0
ERROR_COUNT=0
FAILED_FILES=()

# Temporarily excluded files (already processed)
EXCLUDED_FILES=(
    # "11. Data Protection Commission (Amendment) Bill.pdf"
#    '3. Postal, Courier & Logistics Services Commission (Amendment) Bill.pdf'
)

# Process each PDF
for PDF_FILE in "${PDF_FILES[@]}"; do
    PDF_BASENAME=$(basename "$PDF_FILE")

    # Skip excluded files
    if [[ " ${EXCLUDED_FILES[@]} " =~ " ${PDF_BASENAME} " ]]; then
        echo -e "${BLUE}⊘ Skipping (excluded): $PDF_BASENAME${NC}"
        continue
    fi

    echo
    echo "================================================================================"
    echo -e "${CYAN}[${SUCCESS_COUNT}+${ERROR_COUNT}+1/${PDF_COUNT}]${NC} Processing: ${YELLOW}$PDF_BASENAME${NC}"
    echo "================================================================================"
    echo

    # Call process_bill.sh for this file with force flag if set
    if ./process_bill.sh "$PDF_FILE" $FORCE_FLAG; then
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
        echo -e "${GREEN}✓ Successfully processed: $PDF_BASENAME${NC}"
    else
        ERROR_COUNT=$((ERROR_COUNT + 1))
        FAILED_FILES+=("$PDF_BASENAME")
        echo -e "${RED}✗ Failed to process: $PDF_BASENAME${NC}"
    fi
done

# Final summary
echo
echo
echo "================================================================================"
echo -e "${BLUE}Processing Complete${NC}"
echo "================================================================================"
echo

if [ $SUCCESS_COUNT -eq $PDF_COUNT ]; then
    echo -e "${GREEN}✓ Successfully processed all ${PDF_COUNT} bills!${NC}"
else
    echo -e "${GREEN}Successfully processed: ${SUCCESS_COUNT}/${PDF_COUNT} bills${NC}"

    if [ $ERROR_COUNT -gt 0 ]; then
        echo -e "${RED}Failed: ${ERROR_COUNT} bills${NC}"
        echo
        echo "Failed files:"
        for failed in "${FAILED_FILES[@]}"; do
            echo -e "  ${RED}✗${NC} $failed"
        done
    fi
fi

echo
