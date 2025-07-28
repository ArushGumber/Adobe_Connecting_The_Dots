import os
import json
import re
from pathlib import Path
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.output import text_from_rendered

class MarkerPDFExtractor:
    def __init__(self):
        # Initialize marker converter
        self.converter = PdfConverter(
            artifact_dict=create_model_dict(),
        )
    
    def extract_title_and_outline(self, pdf_path):
        """Extract title and outline using marker-pdf"""
        try:
            # Convert PDF using marker
            rendered = self.converter(str(pdf_path))
            
            # Extract title from metadata
            title = ""
            if rendered.metadata and hasattr(rendered.metadata, 'title'):
                title = rendered.metadata.title or ""
            
            # If no title in metadata, try to extract from first heading
            if not title and rendered.children:
                for child in rendered.children[:3]:  # Check first 3 blocks
                    if hasattr(child, 'block_type') and 'Header' in str(child.block_type):
                        if hasattr(child, 'html'):
                            # Extract text from HTML
                            import re
                            text = re.sub(r'<[^>]+>', '', child.html).strip()
                            if len(text) > 3 and len(text) < 200:
                                title = text
                                break
            
            # Extract headings from the document structure
            outline = self.extract_headings_from_rendered(rendered)
            
            return {
                "title": title.strip(),
                "outline": outline
            }
            
        except Exception as e:
            print(f"Error processing {pdf_path}: {e}")
            return {"title": "", "outline": []}
    
    def extract_headings_from_rendered(self, rendered):
        """Extract headings from marker's rendered output"""
        headings = []
        
        def process_block(block, page_num=1):
            """Recursively process blocks to find headings"""
            if not hasattr(block, 'block_type'):
                return
            
            block_type = str(block.block_type)
            
            # Check if this is a heading block
            if 'Header' in block_type or 'SectionHeader' in block_type:
                # Extract text from HTML
                text = ""
                if hasattr(block, 'html'):
                    text = re.sub(r'<[^>]+>', '', block.html).strip()
                elif hasattr(block, 'text'):
                    text = block.text.strip()
                
                if text and len(text) > 2:
                    # Determine heading level from HTML tags or block type
                    level = self.determine_heading_level(block)
                    
                    headings.append({
                        "level": level,
                        "text": text,
                        "page": page_num
                    })
            
            # Process children recursively
            if hasattr(block, 'children') and block.children:
                for child in block.children:
                    process_block(child, page_num)
        
        # Process all pages
        if hasattr(rendered, 'children'):
            for page_idx, page in enumerate(rendered.children, 1):
                process_block(page, page_idx)
        
        return headings
    
    def determine_heading_level(self, block):
        """Determine heading level from marker's block"""
        # Check HTML tags first
        if hasattr(block, 'html'):
            html = block.html.lower()
            if '<h1' in html:
                return "H1"
            elif '<h2' in html:
                return "H2"
            elif '<h3' in html:
                return "H3"
            elif '<h4' in html:
                return "H3"  # Map H4+ to H3
        
        # Check section hierarchy
        if hasattr(block, 'section_hierarchy'):
            hierarchy = block.section_hierarchy
            if isinstance(hierarchy, dict):
                levels = list(hierarchy.keys())
                if levels:
                    level = min(int(k) for k in levels if k.isdigit())
                    if level == 1:
                        return "H1"
                    elif level == 2:
                        return "H2"
                    else:
                        return "H3"
        
        # Fallback: analyze text patterns
        if hasattr(block, 'html'):
            text = re.sub(r'<[^>]+>', '', block.html).strip()
        elif hasattr(block, 'text'):
            text = block.text.strip()
        else:
            return "H2"  # Default
        
        # Pattern-based classification
        if re.match(r'^\d+\.\s+', text):  # "1. Introduction"
            return "H1"
        elif re.match(r'^\d+\.\d+\s+', text):  # "1.1 Background"
            return "H2"
        elif re.match(r'^\d+\.\d+\.\d+\s+', text):  # "1.1.1 Details"
            return "H3"
        
        # Default based on text characteristics
        if text.isupper() or len(text.split()) <= 3:
            return "H1"
        else:
            return "H2"

def main():
    """Main processing function"""
    input_dir = "/app/input"
    output_dir = "/app/output"
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialize extractor
    extractor = MarkerPDFExtractor()
    
    # Process all PDFs in input directory
    for pdf_file in Path(input_dir).glob("*.pdf"):
        try:
            print(f"Processing {pdf_file.name}...")
            result = extractor.extract_title_and_outline(pdf_file)
            
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