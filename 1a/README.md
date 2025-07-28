# Adobe India Hackathon Round 1A - PDF Outline Extractor

## Solution Overview
This solution extracts structured outlines (Title + H1/H2/H3 headings) from PDF documents using intelligent heuristics and font analysis.

## Approach
1. **Title Extraction**: PDF metadata → Largest font text on first page
2. **Heading Detection**: Multi-factor analysis (font size, bold, patterns, keywords)
3. **Level Classification**: Font size ratios + numbering patterns → H1/H2/H3

## Libraries Used
- `pdfplumber`: PDF text and layout extraction
- `PyPDF2`: PDF metadata access

## Build & Run
```bash
docker build --platform linux/amd64 -t pdf-extractor .
docker run --rm -v $(pwd)/input:/app/input -v $(pwd)/output:/app/output --network none pdf-extractor