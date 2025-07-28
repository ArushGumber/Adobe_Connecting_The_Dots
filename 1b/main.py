import os
import json
import re
import pdfplumber
from collections import Counter, defaultdict
from datetime import datetime
import math
from pathlib import Path
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.stem import PorterStemmer
import numpy as np

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

class PersonaDrivenDocumentAnalyzer:
    def __init__(self):
        self.stemmer = PorterStemmer()
        self.stop_words = set(stopwords.words('english'))
        
        # Keywords for different domains/personas
        self.persona_keywords = {
            'researcher': ['methodology', 'analysis', 'results', 'conclusion', 'literature', 'study', 'research', 'hypothesis', 'experiment', 'data', 'findings', 'review', 'survey'],
            'student': ['concept', 'definition', 'example', 'problem', 'solution', 'exercise', 'theory', 'principle', 'formula', 'equation', 'practice', 'learn'],
            'analyst': ['trend', 'performance', 'metric', 'revenue', 'growth', 'profit', 'market', 'strategy', 'forecast', 'benchmark', 'comparison', 'financial'],
            'investment': ['revenue', 'profit', 'growth', 'market', 'competition', 'strategy', 'risk', 'return', 'valuation', 'investment', 'portfolio'],
            'business': ['strategy', 'market', 'revenue', 'profit', 'growth', 'customer', 'product', 'service', 'competition', 'opportunity'],
            'technical': ['implementation', 'architecture', 'design', 'system', 'algorithm', 'performance', 'optimization', 'technology', 'framework'],
            'academic': ['theory', 'concept', 'principle', 'methodology', 'analysis', 'study', 'research', 'literature', 'review', 'hypothesis'],
            'chemistry': ['reaction', 'mechanism', 'kinetics', 'thermodynamics', 'equilibrium', 'catalyst', 'synthesis', 'molecule', 'compound', 'bond'],
            'biology': ['cell', 'protein', 'gene', 'organism', 'metabolism', 'pathway', 'structure', 'function', 'evolution', 'ecology'],
            'physics': ['force', 'energy', 'momentum', 'wave', 'particle', 'field', 'quantum', 'relativity', 'mechanics', 'thermodynamics']
        }
    
    def preprocess_text(self, text):
        """Clean and preprocess text"""
        # Convert to lowercase and remove special characters
        text = re.sub(r'[^a-zA-Z0-9\s]', ' ', text.lower())
        # Tokenize
        tokens = word_tokenize(text)
        # Remove stopwords and stem
        tokens = [self.stemmer.stem(token) for token in tokens if token not in self.stop_words and len(token) > 2]
        return tokens
    
    def extract_keywords_from_persona_job(self, persona, job_to_be_done):
        """Extract relevant keywords from persona and job description"""
        persona_lower = persona.lower()
        job_lower = job_to_be_done.lower()
        
        # Identify persona type
        persona_type = 'general'
        for p_type, keywords in self.persona_keywords.items():
            if p_type in persona_lower or any(keyword in persona_lower for keyword in keywords[:3]):
                persona_type = p_type
                break
        
        # Extract keywords from job description
        job_tokens = self.preprocess_text(job_to_be_done)
        
        # Combine persona keywords with job keywords
        relevant_keywords = set(self.persona_keywords.get(persona_type, []))
        relevant_keywords.update(job_tokens[:20])  # Top 20 job keywords
        
        # Add specific keywords based on job content
        if 'literature review' in job_lower:
            relevant_keywords.update(['methodology', 'results', 'conclusion', 'analysis', 'comparison'])
        if 'exam' in job_lower or 'study' in job_lower:
            relevant_keywords.update(['concept', 'definition', 'example', 'theory', 'practice'])
        if 'financial' in job_lower or 'revenue' in job_lower:
            relevant_keywords.update(['revenue', 'profit', 'growth', 'market', 'financial'])
        
        return list(relevant_keywords)
    
    def extract_document_structure(self, pdf_path):
        """Extract structured content from PDF"""
        sections = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    chars = page.chars
                    if not chars:
                        continue
                    
                    # Calculate font statistics
                    font_sizes = [char.get('size', 12) for char in chars if char.get('size')]
                    if not font_sizes:
                        continue
                    
                    avg_font_size = sum(font_sizes) / len(font_sizes)
                    max_font_size = max(font_sizes)
                    
                    # Group characters into lines
                    lines = defaultdict(list)
                    for char in chars:
                        y = round(char.get('top', 0), 1)
                        lines[y].append(char)
                    
                    # Process each line
                    for y, line_chars in lines.items():
                        line_chars.sort(key=lambda x: x.get('x0', 0))
                        text = ''.join([char.get('text', '') for char in line_chars]).strip()
                        
                        if not text or len(text) < 10:
                            continue
                        
                        # Get line properties
                        line_font_sizes = [char.get('size', 12) for char in line_chars if char.get('size')]
                        if not line_font_sizes:
                            continue
                        
                        line_font_size = max(line_font_sizes)
                        
                        # Check if it's a potential heading
                        is_heading = (
                            line_font_size > avg_font_size * 1.1 and
                            len(text) < 200 and
                            not text.endswith('.') and
                            len(text.split()) <= 15
                        )
                        
                        # Determine section level
                        if is_heading:
                            if line_font_size >= max_font_size * 0.9:
                                level = "H1"
                            elif line_font_size >= avg_font_size * 1.3:
                                level = "H2"
                            else:
                                level = "H3"
                        else:
                            level = "content"
                        
                        sections.append({
                            'text': text,
                            'level': level,
                            'page': page_num,
                            'font_size': line_font_size,
                            'is_heading': is_heading
                        })
        
        except Exception as e:
            print(f"Error processing {pdf_path}: {e}")
        
        return sections
    
    def calculate_relevance_score(self, text, keywords, persona, job_to_be_done):
        """Calculate relevance score based on keyword matching and context"""
        text_tokens = self.preprocess_text(text)
        if not text_tokens:
            return 0
        
        # Keyword matching score
        keyword_matches = sum(1 for token in text_tokens if any(kw in token or token in kw for kw in keywords))
        keyword_score = keyword_matches / len(text_tokens) if text_tokens else 0
        
        # Persona-specific scoring
        persona_lower = persona.lower()
        job_lower = job_to_be_done.lower()
        text_lower = text.lower()
        
        context_score = 0
        
        # Research context
        if 'research' in persona_lower:
            if any(word in text_lower for word in ['methodology', 'results', 'analysis', 'conclusion', 'study']):
                context_score += 0.3
        
        # Student context
        if 'student' in persona_lower:
            if any(word in text_lower for word in ['concept', 'definition', 'example', 'theory', 'principle']):
                context_score += 0.3
        
        # Business/Analyst context
        if any(word in persona_lower for word in ['analyst', 'business', 'investment']):
            if any(word in text_lower for word in ['revenue', 'profit', 'market', 'growth', 'financial']):
                context_score += 0.3
        
        # Job-specific scoring
        if 'literature review' in job_lower and any(word in text_lower for word in ['methodology', 'approach', 'results']):
            context_score += 0.2
        if 'exam' in job_lower and any(word in text_lower for word in ['concept', 'definition', 'example']):
            context_score += 0.2
        if 'financial' in job_lower and any(word in text_lower for word in ['revenue', 'profit', 'financial']):
            context_score += 0.2
        
        # Length penalty for very short or very long sections
        length_score = min(1.0, len(text) / 100) * (1 - max(0, len(text) - 1000) / 2000)
        
        return (keyword_score * 0.5 + context_score * 0.4 + length_score * 0.1)
    
    def extract_relevant_sections(self, documents, persona, job_to_be_done):
        """Extract and rank relevant sections from documents"""
        keywords = self.extract_keywords_from_persona_job(persona, job_to_be_done)
        
        all_sections = []
        subsection_analysis = []
        
        for doc_name in documents:
            doc_path = f"/app/input/{doc_name}"
            if not os.path.exists(doc_path):
                continue
            
            sections = self.extract_document_structure(doc_path)
            
            # Group content under headings
            current_heading = None
            current_content = []
            
            for section in sections:
                if section['is_heading']:
                    # Save previous section if exists
                    if current_heading and current_content:
                        content_text = ' '.join([s['text'] for s in current_content])
                        if len(content_text.strip()) > 50:  # Minimum content length
                            score = self.calculate_relevance_score(
                                current_heading['text'] + ' ' + content_text,
                                keywords, persona, job_to_be_done
                            )
                            
                            all_sections.append({
                                'document': doc_name,
                                'section_title': current_heading['text'],
                                'page_number': current_heading['page'],
                                'score': score,
                                'content': content_text
                            })
                    
                    current_heading = section
                    current_content = []
                else:
                    current_content.append(section)
            
            # Handle last section
            if current_heading and current_content:
                content_text = ' '.join([s['text'] for s in current_content])
                if len(content_text.strip()) > 50:
                    score = self.calculate_relevance_score(
                        current_heading['text'] + ' ' + content_text,
                        keywords, persona, job_to_be_done
                    )
                    
                    all_sections.append({
                        'document': doc_name,
                        'section_title': current_heading['text'],
                        'page_number': current_heading['page'],
                        'score': score,
                        'content': content_text
                    })
        
        # Sort by relevance score
        all_sections.sort(key=lambda x: x['score'], reverse=True)
        
        # Select top 5 sections
        top_sections = all_sections[:5]
        
        # Create extracted sections output
        extracted_sections = []
        for i, section in enumerate(top_sections, 1):
            extracted_sections.append({
                'document': section['document'],
                'section_title': section['section_title'],
                'importance_rank': i,
                'page_number': section['page_number']
            })
        
        # Create subsection analysis for top sections
        for section in top_sections[:3]:  # Top 3 for detailed analysis
            # Split content into meaningful chunks
            sentences = sent_tokenize(section['content'])
            if len(sentences) > 3:
                # Take most relevant sentences
                chunk_size = min(5, len(sentences))
                chunk = ' '.join(sentences[:chunk_size])
            else:
                chunk = section['content']
            
            # Limit text length
            if len(chunk) > 500:
                chunk = chunk[:500] + "..."
            
            subsection_analysis.append({
                'document': section['document'],
                'refined_text': chunk,
                'page_number': section['page_number']
            })
        
        return extracted_sections, subsection_analysis
    
    def process_documents(self, input_dir="/app/input", output_dir="/app/output"):
        """Process all document collections"""
        os.makedirs(output_dir, exist_ok=True)
        
        # Look for input.json file
        input_file = os.path.join(input_dir, "input.json")
        if not os.path.exists(input_file):
            print("No input.json found")
            return
        
        with open(input_file, 'r') as f:
            input_data = json.load(f)
        
        documents = [doc['filename'] for doc in input_data['documents']]
        persona = input_data['persona']['role']
        job_to_be_done = input_data['job_to_be_done']['task']
        
        extracted_sections, subsection_analysis = self.extract_relevant_sections(
            documents, persona, job_to_be_done
        )
        
        # Create output
        output = {
            "metadata": {
                "input_documents": documents,
                "persona": persona,
                "job_to_be_done": job_to_be_done,
                "processing_timestamp": datetime.now().isoformat()
            },
            "extracted_sections": extracted_sections,
            "subsection_analysis": subsection_analysis
        }
        
        # Save output
        output_file = os.path.join(output_dir, "output.json")
        with open(output_file, 'w') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print(f"Processed {len(documents)} documents")
        print(f"Output saved to {output_file}")

def main():
    analyzer = PersonaDrivenDocumentAnalyzer()
    analyzer.process_documents()

if __name__ == "__main__":
    main()