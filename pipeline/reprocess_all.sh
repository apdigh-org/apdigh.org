#!/bin/bash
# Reprocess all Docling JSON files to extract provisions

set -e

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

# Activate virtual environment
source venv/bin/activate

# Find all Docling JSON files
DOCLING_FILES=(output/*.docling.json)

if [ ! -e "${DOCLING_FILES[0]}" ]; then
    echo -e "${RED}Error: No .docling.json files found in output/ directory${NC}"
    echo
    echo "Run ./process_bill.sh first to generate Docling JSON files"
    exit 1
fi

FILE_COUNT=${#DOCLING_FILES[@]}

echo
echo "================================================================================"
echo -e "${BLUE}Reprocessing All Bills${NC}"
echo "================================================================================"
echo -e "Found ${CYAN}${FILE_COUNT}${NC} Docling JSON files to process"
echo
echo "This will regenerate all bill JSON files with updated extraction logic."
echo
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
fi
echo

# Track results using temporary file
RESULTS_FILE=$(mktemp)
TOTAL_PROVISIONS=0

# Process each file
for DOCLING_FILE in "${DOCLING_FILES[@]}"; do
    BASENAME=$(basename "$DOCLING_FILE")
    BILL_NAME="${BASENAME%.docling.json}"

    echo -e "${YELLOW}Processing:${NC} $BILL_NAME"

    # Run the extraction script and capture output
    OUTPUT=$(python scripts/2_docling_to_json.py "$DOCLING_FILE" 2>&1)

    # Extract provision count from output
    if echo "$OUTPUT" | grep -q "EXTRACTED.*PROVISIONS"; then
        COUNT=$(echo "$OUTPUT" | grep "EXTRACTED" | grep "PROVISIONS" | awk '{print $2}')
        echo "$COUNT|$BILL_NAME" >> "$RESULTS_FILE"
        TOTAL_PROVISIONS=$((TOTAL_PROVISIONS + COUNT))
        echo -e "  ${GREEN}✓${NC} $COUNT provisions extracted"
    else
        echo "ERROR|$BILL_NAME" >> "$RESULTS_FILE"
        echo -e "  ${RED}✗${NC} Extraction failed"
    fi

    echo
done

# Print summary
echo "================================================================================"
echo -e "${BLUE}Summary${NC}"
echo "================================================================================"
echo

# Sort and print results
sort -t'|' -k2 "$RESULTS_FILE" | while IFS='|' read -r COUNT BILL_NAME; do
    if [[ "$COUNT" == "ERROR" ]]; then
        echo -e "  ${RED}ERROR${NC}     - $BILL_NAME"
    else
        printf "  ${GREEN}%4s${NC} provisions - %s\n" "$COUNT" "$BILL_NAME"
    fi
done

# Clean up temp file
rm -f "$RESULTS_FILE"

echo
echo "================================================================================"
echo -e "Total: ${CYAN}${TOTAL_PROVISIONS}${NC} provisions across ${CYAN}${FILE_COUNT}${NC} bills"
echo "================================================================================"
echo
echo -e "${GREEN}All bill JSON files have been regenerated in output/ directory${NC}"
echo
