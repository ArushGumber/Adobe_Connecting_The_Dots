# Adobe India Hackathon Round 1A - PDF Outline Extractor

## Solution Overview
Advanced PDF outline extraction using marker-pdf's ML-powered document understanding.

## Key Features
- Uses marker-pdf's deep learning models for layout detection
- Automatic heading hierarchy detection (H1/H2/H3)
- Robust title extraction from metadata and content
- High accuracy across diverse document formats
- CPU-optimized for performance

## Libraries Used
- `marker-pdf`: ML-powered PDF processing and structure extraction
- `torch`: Deep learning backend

## Build & Run
```bash
docker build --platform linux/amd64 -t pdf-extractor .
docker run --rm -v $(pwd)/input:/app/input -v $(pwd)/output:/app/output --network none pdf-extractor