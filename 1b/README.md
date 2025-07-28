# Round 1B: Persona-Driven Document Intelligence

## Overview
This solution extracts and prioritizes the most relevant sections from a collection of documents based on a specific persona and their job-to-be-done.

## Approach
- **Multi-factor relevance scoring** combining keyword analysis, persona context, and job alignment
- **Intelligent heading detection** using font analysis and structural patterns
- **Domain-adaptive keyword extraction** for different persona types
- **Content quality filtering** to ensure meaningful section extraction

## Libraries Used
- **pdfplumber**: PDF text extraction with formatting metadata
- **NLTK**: Natural language processing for tokenization and preprocessing
- **numpy**: Numerical computations for scoring algorithms

## File Structure
```
/
├── Dockerfile
├── requirements.txt
├── main.py
├── approach_explanation.md
└── README.md
```

## Build and Run

### Building the Docker Image
```bash
docker build --platform linux/amd64 -t persona-doc-analyzer .
```

### Running the Solution
```bash
docker run --rm -v $(pwd)/input:/app/input -v $(pwd)/output:/app/output --network none persona-doc-analyzer
```

## Input Format
The solution expects an `input.json` file in the input directory with the following structure:
```json
{
    "documents": [
        {"filename": "document1.pdf"},
        {"filename": "document2.pdf"}
    ],
    "persona": {
        "role": "PhD Researcher in Computational Biology"
    },
    "job_to_be_done": {
        "task": "Prepare a comprehensive literature review"
    }
}
```

## Output Format
The solution generates an `output.json` file with:
- **Metadata**: Input documents, persona, and job description
- **Extracted Sections**: Top 5 relevant sections with importance rankings
- **Subsection Analysis**: Detailed content analysis for top 3 sections

## Performance
- **Processing Time**: ≤ 60 seconds for 3-5 documents
- **Model Size**: ≤ 1GB (uses lightweight NLP models)
- **CPU Only**: No GPU dependencies
- **Offline Operation**: No internet access required