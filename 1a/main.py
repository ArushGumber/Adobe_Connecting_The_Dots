import os
import json
import re
from pathlib import Path
import pdfplumber
from PyPDF2 import PdfReader
from collections import Counter

class PDFOutlineExtractor:
    def __init__(self):
        self.heading_keywords = [
            'introduction', 'background', 'overview', 'summary', 'conclusion',
            'methodology', 'approach', 'requirements', 'specifications', 'goals',
            'objectives', 'timeline', 'milestones', 'deliverables', 'references'
        ]
    
    def extract_title(self, pdf_path):
        """Extract title using multiple strategies"""
        try:
            # Strategy 1: PDF metadata
            with open(pdf_path, 'rb') as file:
                reader = PdfReader(file)
                if reader.metadata and reader.metadata.title:
                    title = reader.metadata.title.strip()
                    if title and len(title) > 3:
                        return title
        except:
            pass
        
        # Strategy 2: First page analysis
        try:
            with pdfplumber.open(pdf_path) as pdf:
                first_page = pdf.pages[0]
                chars = first_page.chars
                
                if not chars:
                    return ""
                
                # Find largest font size text on first page
                font_sizes = [char.get('size', 12) for char in chars if char.get('size')]
                if font_sizes:
                    max_font_size = max(font_sizes)
                    
                    # Get text with largest font size
                    title_chars = [char for char in chars 
                                 if char.get('size', 12) >= max_font_size * 0.9]
                    
                    if title_chars:
                        # Sort by position and extract text
                        title_chars.sort(key=lambda x: (x.get('top', 0), x.get('x0', 0)))
                        title_text = ''.join([char.get('text', '') for char in title_chars])
                        title = re.sub(r'\s+', ' ', title_text).strip()
                        
                        # Clean and validate title
                        if 3 <= len(title) <= 200:
                            return title
        except:
            pass
        
        return ""
    
    def is_likely_heading(self, text, font_size, is_bold, avg_font_size):
        """Determine if text is likely a heading"""
        text_clean = text.strip()
        
        if len(text_clean) < 3 or len(text_clean) > 200:
            return False
        
        score = 0
        
        # Font size analysis
        if font_size > avg_font_size * 1.3:
            score += 4
        elif font_size > avg_font_size * 1.1:
            score += 2
        
        # Bold text
        if is_bold:
            score += 2
        
        # Text patterns
        if re.match(r'^\d+[\.\)]\s+', text_clean):  # Numbered headings
            score += 3
        elif re.match(r'^[A-Z][a-z]+(\s+[A-Z][a-z]+)*:?\s*$', text_clean):  # Title case
            score += 2
        elif text_clean.isupper() and len(text_clean.split()) >= 2:  # ALL CAPS
            score += 1
        
        # Keyword matching
        if any(keyword in text_clean.lower() for keyword in self.heading_keywords):
            score += 1
        
        # Avoid common non-headings
        if re.match(r'^\d+$', text_clean) or text_clean.lower() in ['page', 'continued']:
            score -= 5
        
        return score >= 3
    
    def classify_heading_level(self, text, font_size, max_font_size, avg_font_size):
        """Classify heading level H1/H2/H3"""
        text_clean = text.strip()
        
        # Font size based classification
        size_ratio = font_size / avg_font_size if avg_font_size > 0 else 1
        
        level_score = 0
        
        # Primary: Font size
        if size_ratio >= 1.5:
            level_score += 3
        elif size_ratio >= 1.2:
            level_score += 2
        else:
            level_score += 1
        
        # Numbering patterns
        if re.match(r'^\d+\.\s+', text_clean):  # "1. "
            level_score = max(level_score, 3)
        elif re.match(r'^\d+\.\d+\s+', text_clean):  # "1.1 "
            level_score = min(level_score, 2)
        elif re.match(r'^\d+\.\d+\.\d+\s+', text_clean):  # "1.1.1 "
            level_score = 1
        
        # Map to heading levels
        if level_score >= 3:
            return "H1"
        elif level_score >= 2:
            return "H2"
        else:
            return "H3"
    
    def extract_outline(self, pdf_path):
        """Extract structured outline from PDF"""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                headings = []
                all_chars = []
                
                # Collect all characters for font analysis
                for page_num, page in enumerate(pdf.pages, 1):
                    chars = page.chars
                    for char in chars:
                        char['page'] = page_num
                        all_chars.append(char)
                
                if not all_chars:
                    return []
                
                # Calculate font statistics
                font_sizes = [char.get('size', 12) for char in all_chars if char.get('size')]
                avg_font_size = sum(font_sizes) / len(font_sizes) if font_sizes else 12
                max_font_size = max(font_sizes) if font_sizes else 12
                
                # Group characters into text blocks
                for page_num, page in enumerate(pdf.pages, 1):
                    try:
                        # Get text objects with formatting
                        text_objects = []
                        
                        # Use char-level analysis for better formatting detection
                        chars = page.chars
                        if not chars:
                            continue
                        
                        # Group chars into lines
                        lines = {}
                        for char in chars:
                            y = round(char.get('top', 0), 1)
                            if y not in lines:
                                lines[y] = []
                            lines[y].append(char)
                        
                        # Process each line
                        for y, line_chars in lines.items():
                            line_chars.sort(key=lambda x: x.get('x0', 0))
                            
                            text = ''.join([char.get('text', '') for char in line_chars]).strip()
                            if not text:
                                continue
                            
                            # Get line properties
                            font_sizes_line = [char.get('size', 12) for char in line_chars if char.get('size')]
                            font_size = max(font_sizes_line) if font_sizes_line else 12
                            
                            # Check if bold (simplified)
                            font_names = [char.get('fontname', '') for char in line_chars]
                            is_bold = any('bold' in name.lower() for name in font_names if name)
                            
                            # Check if it's a heading
                            if self.is_likely_heading(text, font_size, is_bold, avg_font_size):
                                level = self.classify_heading_level(text, font_size, max_font_size, avg_font_size)
                                
                                headings.append({
                                    'level': level,
                                    'text': text,
                                    'page': page_num
                                })
                    
                    except Exception as e:
                        continue
                
                # Remove duplicates and sort
                seen = set()
                unique_headings = []
                for h in headings:
                    key = (h['text'].lower().strip(), h['page'])
                    if key not in seen:
                        seen.add(key)
                        unique_headings.append(h)
                
                # Sort by page then by likely document order
                unique_headings.sort(key=lambda x: (x['page'], x['text']))
                
                return unique_headings
        
        except Exception as e:
            return []
    
    def process_pdf(self, pdf_path):
        """Process single PDF and return structured outline"""
        title = self.extract_title(pdf_path)
        outline = self.extract_outline(pdf_path)
        
        return {
            "title": title,
            "outline": outline
        }

def main():
    """Main processing function"""
    input_dir = "/app/input"
    output_dir = "/app/output"
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    extractor = PDFOutlineExtractor()
    
    # Process all PDFs in input directory
    for pdf_file in Path(input_dir).glob("*.pdf"):
        try:
            print(f"Processing {pdf_file.name}...")
            result = extractor.process_pdf(pdf_file)
            
            # Save output
            output_file = Path(output_dir) / f"{pdf_file.stem}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            
            print(f"Completed {pdf_file.name} -> {output_file.name}")
            
        except Exception as e:
            print(f"Error processing {pdf_file.name}: {e}")
            # Create fallback output
            fallback = {"title": "", "outline": []}
            output_file = Path(output_dir) / f"{pdf_file.stem}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(fallback, f, indent=2)

if __name__ == "__main__":
    main()