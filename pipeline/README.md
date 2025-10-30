# Bill Processing Pipeline

This pipeline converts bill PDFs into structured JSON data for the website.

## Directory Structure

```
pipeline/
├── pdfs/           # Place bill PDF files here
├── output/         # Intermediate outputs (markdown, structured text)
├── scripts/        # Processing scripts
│   ├── 1_pdf_to_text.py      # Convert PDF to structured text using Docling
│   └── 2_text_to_json.py     # Convert structured text to JSON
└── README.md       # This file
```

## Setup

1. Create a Python virtual environment:
```bash
cd pipeline
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install docling
```

## Usage

### Quick Start (Automated Pipeline)

Process a bill PDF in one command:

```bash
./process_bill.sh pdfs/your-bill.pdf
```

This will automatically:
1. Convert the PDF to structured markdown
2. Generate a JSON template
3. Display next steps

### Manual Step-by-Step

If you prefer to run each step individually:

#### Step 1: Convert PDF to Structured Text

Place your bill PDF in the `pdfs/` directory, then run:

```bash
source venv/bin/activate
python scripts/1_pdf_to_text.py pdfs/your-bill.pdf
```

This will create a structured markdown file in `output/your-bill.md`

#### Step 2: Generate Bill JSON

Review the structured text, then generate the JSON:

```bash
python scripts/2_text_to_json.py output/your-bill.md
```

This will create `../src/data/bills/your-bill.json`

#### Step 3: Manual Review

Review and edit the generated JSON to:
- Add impact analysis
- Add key concerns
- Add key provisions with plain language explanations
- Set deadline and submission method
- Link related bills

## Notes

- The pipeline extracts structure but requires manual analysis for impacts and concerns
- Always review generated content for accuracy
- Consider using LLMs (Claude, GPT-4) to help with analysis in step 2
