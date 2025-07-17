import os
import json
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import PyPDF2
import pdfplumber
import fitz
from openai import OpenAI
from dataclasses import dataclass
import hashlib
import pickle
from datetime import datetime
from tqdm import tqdm
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class BookKnowledge:
    """Represents processed knowledge from a marketing book"""
    filename: str
    title: str
    content: str
    summary: str
    key_concepts: List[str]
    frameworks: List[str]
    processed_at: datetime
    content_hash: str

class MarketingAgent:
    """
    AI Marketing Consultant Agent that processes marketing books and provides
    expert consultation on business ideas.
    """
    
    def __init__(self, 
                 openai_api_key: str = os.getenv("OPENAI_API_KEY"),
                 books_folder: str = "Legal_Marketing_Agents/books",
                 model: str = "gpt-4o-mini",
                 cache_file: str = "marketing_knowledge_cache.pkl"):
        """
        Initialize the Marketing Consultant Agent
        
        Args:
            openai_api_key: OpenAI API key
            books_folder: Path to folder containing PDF marketing books
            model: OpenAI model to use
            cache_file: Path to cache file for processed books
        """
        self.client = OpenAI(api_key=openai_api_key)
        self.books_folder = Path(books_folder)
        self.model = model
        self.cache_file = cache_file
        self.knowledge_base: List[BookKnowledge] = []
        
        # Load cached knowledge if available
        self._load_cache()
        
        # Process any new books
        self._process_new_books()
    
    def _check_dependencies(self):
        """Check if required PDF processing libraries are installed"""
        missing_deps = []
        
        try:
            import fitz
        except ImportError:
            missing_deps.append("PyMuPDF")
        
        try:
            import pdfplumber
        except ImportError:
            missing_deps.append("pdfplumber")
        
        if missing_deps:
            logger.warning(f"Missing optional dependencies: {', '.join(missing_deps)}")
            logger.warning("For better PDF processing, install with: pip install PyMuPDF pdfplumber")
            logger.warning("Currently using PyPDF2 only, which may fail on some PDF formats")
    
    def _load_cache(self):
        """Load previously processed book knowledge from cache"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'rb') as f:
                    self.knowledge_base = pickle.load(f)
                logger.info(f"Loaded {len(self.knowledge_base)} books from cache")
            except Exception as e:
                logger.error(f"Error loading cache: {e}")
                self.knowledge_base = []
    
    def _save_cache(self):
        """Save processed book knowledge to cache"""
        try:
            with open(self.cache_file, 'wb') as f:
                pickle.dump(self.knowledge_base, f)
            logger.info(f"Saved {len(self.knowledge_base)} books to cache")
        except Exception as e:
            logger.error(f"Error saving cache: {e}")
    
    def _extract_text_from_pdf(self, pdf_path: Path) -> str:
        """Extract text content from PDF file using multiple methods"""
        text = ""
        
        # Method 1: Try PyMuPDF (most reliable)
        try:
            doc = fitz.open(pdf_path)
            for page_num in range(len(doc)):
                page = doc[page_num]
                text += page.get_text() + "\n"
            doc.close()
            if text.strip():
                logger.info(f"Successfully extracted text using PyMuPDF from {pdf_path.name}")
                return text.strip()
        except Exception as e:
            logger.warning(f"PyMuPDF failed for {pdf_path.name}: {e}")
        
        # Method 2: Try pdfplumber (good for tables and complex layouts)
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            if text.strip():
                logger.info(f"Successfully extracted text using pdfplumber from {pdf_path.name}")
                return text.strip()
        except Exception as e:
            logger.warning(f"pdfplumber failed for {pdf_path.name}: {e}")
        
        # Method 3: Try PyPDF2 (original method)
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
                    except Exception as page_error:
                        logger.warning(f"Error extracting page from {pdf_path.name}: {page_error}")
                        continue
            if text.strip():
                logger.info(f"Successfully extracted text using PyPDF2 from {pdf_path.name}")
                return text.strip()
        except Exception as e:
            logger.warning(f"PyPDF2 failed for {pdf_path.name}: {e}")
        
        # Method 4: Try PyPDF2 with error handling per page
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file, strict=False)  # Less strict parsing
                for i, page in enumerate(pdf_reader.pages):
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
                    except Exception as page_error:
                        logger.warning(f"Skipping page {i+1} of {pdf_path.name}: {page_error}")
                        continue
            if text.strip():
                logger.info(f"Successfully extracted partial text using PyPDF2 (non-strict) from {pdf_path.name}")
                return text.strip()
        except Exception as e:
            logger.warning(f"PyPDF2 (non-strict) failed for {pdf_path.name}: {e}")
        
        logger.error(f"All PDF extraction methods failed for {pdf_path.name}")
        return ""
    
    def _get_content_hash(self, content: str) -> str:
        """Generate hash for content to detect changes"""
        return hashlib.md5(content.encode()).hexdigest()
    
    def _extract_json_from_response(self, response_text: str) -> Dict[str, Any]:
        """Extract JSON from OpenAI response, handling cases where it's wrapped in text"""
        # Try to parse as direct JSON first
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass
        
        # Look for JSON wrapped in code blocks or other text
        import re
        
        # Try to find JSON between triple backticks
        json_match = re.search(r'```(?:json)?\s*({.*?})\s*```', response_text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Try to find JSON-like structure in the text
        json_match = re.search(r'({.*?})', response_text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # If all else fails, return a default structure
        logger.warning(f"Could not parse JSON from response: {response_text[:200]}...")
        return {
            "key_concepts": [],
            "frameworks": [],
            "strategies": [],
            "case_studies": [],
            "insights": []
        }
    
    def _process_book_with_ai(self, content: str, filename: str) -> Dict[str, Any]:
        """Process book content using OpenAI to extract key information"""
        
        
        max_chunk_size = 100000 
        chunks = [content[i:i+max_chunk_size] for i in tqdm(range(0, len(content), max_chunk_size))]
        
        processed_chunks = []
        
        for i, chunk in enumerate(chunks):
            prompt = f"""
            You are a marketing expert analyzing a section of the book "{filename}".
            
            Please analyze this content and extract:
            1. Key marketing concepts and principles
            2. Frameworks, models, or methodologies mentioned
            3. Actionable strategies or tactics
            4. Case studies or examples (brief summaries)
            5. Important insights or takeaways
            
            Book content section {i+1}/{len(chunks)}:
            {chunk}
            
            IMPORTANT: Respond with ONLY a valid JSON object in this exact format:
            {{
                "key_concepts": ["concept1", "concept2"],
                "frameworks": ["framework1", "framework2"],
                "strategies": ["strategy1", "strategy2"],
                "case_studies": ["case1", "case2"],
                "insights": ["insight1", "insight2"]
            }}

            Do not include any explanatory text before or after the JSON.
            """
            
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a marketing expert. Always respond with a valid JSON object."},
                        {"role": "user", "content": prompt}],
                    temperature=0.3
                )

                response_text = response.choices[0].message.content.strip()
                
                # Parse JSON response
                chunk_analysis = self._extract_json_from_response(response_text)
                # chunk_analysis = json.loads(response.choices[0].message.content)
                processed_chunks.append(chunk_analysis)
                
            except Exception as e:
                logger.error(f"Error processing chunk {i+1} of {filename}: {e}")
                processed_chunks.append({
                    "key_concepts": [],
                    "frameworks": [],
                    "strategies": [],
                    "case_studies": [],
                    "insights": []
                })
                continue
        
        # Combine all chunks
        combined_analysis = {
            "key_concepts": [],
            "frameworks": [],
            "strategies": [],
            "case_studies": [],
            "insights": []
        }
        
        for chunk in processed_chunks:
            for key in combined_analysis:
                combined_analysis[key].extend(chunk.get(key, []))
        
        # Remove duplicates
        for key in combined_analysis:
            combined_analysis[key] = list(set(combined_analysis[key]))
        
        # Generate overall summary
        summary_prompt = f"""
        Based on the analysis of the marketing book "{filename}", create a comprehensive summary.
        
        Key concepts found: {combined_analysis['key_concepts']}
        Frameworks found: {combined_analysis['frameworks']}
        Strategies found: {combined_analysis['strategies']}
        
        Please provide a 2-3 paragraph summary of the book's main marketing insights and value. Focus on the most impactful concepts and frameworks that can be applied in real-world marketing scenarios.
        """
        
        try:
            summary_response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a marketing expert. Provide clear, concise summary."},
                    {"role": "user", "content": summary_prompt}],
                temperature=0.3
            )
            summary = summary_response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error generating summary for {filename}: {e}")
            summary = "Summary generation failed"
        
        return {
            "summary": summary,
            "key_concepts": combined_analysis["key_concepts"],
            "frameworks": combined_analysis["frameworks"],
            "all_insights": combined_analysis
        }
    
    def _process_new_books(self):
        """Process any new PDF books in the books folder"""
        if not self.books_folder.exists():
            logger.warning(f"Books folder {self.books_folder} does not exist")
            return
        
        # Get list of existing processed books
        processed_files = {book.filename for book in self.knowledge_base}
        
        # Find new PDF files
        pdf_files = list(self.books_folder.glob("*.pdf"))
        new_files = [f for f in pdf_files if f.name not in processed_files]
        
        if not new_files:
            logger.info("No new books to process")
            return
        
        logger.info(f"Processing {len(new_files)} new books...")
        
        for pdf_file in tqdm(new_files):
            logger.info(f"Processing: {pdf_file.name}")
            
            # Extract text
            content = self._extract_text_from_pdf(pdf_file)
            if not content:
                logger.warning(f"No content extracted from {pdf_file.name}")
                continue

            if len(content.strip()) < 500:
                logger.warning(f"Very little content extracted from {pdf_file.name}: {len(content)} chars - may be a problematic PDF")
                continue
            
            # Process with AI
            try:
                analysis = self._process_book_with_ai(content, pdf_file.name)
                
                # Create BookKnowledge object
                book_knowledge = BookKnowledge(
                    filename=pdf_file.name,
                    title=pdf_file.stem,
                    content=content[:10000],  # Store first 10000 chars for reference
                    summary=analysis["summary"],
                    key_concepts=analysis["key_concepts"],
                    frameworks=analysis["frameworks"],
                    processed_at=datetime.now(),
                    content_hash=self._get_content_hash(content)
                )
                
                self.knowledge_base.append(book_knowledge)
                logger.info(f"Successfully processed: {pdf_file.name}")
                
            except Exception as e:
                logger.error(f"Error processing {pdf_file.name}: {e}")
                continue
        
        # Save updated cache
        self._save_cache()
        logger.info(f"Knowledge base now contains {len(self.knowledge_base)} books")
    
    def get_consultation(self, business_idea: str, specific_questions: Optional[List[str]] = None) -> str:
        """
        Provide marketing consultation on a business idea
        
        Args:
            business_idea: Description of the business idea
            specific_questions: Optional list of specific questions to address
            
        Returns:
            Comprehensive marketing consultation response
        """
        
        if not self.knowledge_base:
            return "No marketing books have been processed yet. Please add PDF books to the books folder."
        print(agent.knowledge_base)
        
        # Compile knowledge base summary
        knowledge_summary = self._compile_knowledge_summary()
        
        # Build consultation prompt
        prompt = self._build_consultation_prompt(business_idea, specific_questions, knowledge_summary)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a world-class marketing consultant with deep expertise from leading marketing textbooks. Provide comprehensive, actionalbe advice."},
                    {"role": "user", "content": prompt}],
                temperature=0.4,
                max_tokens=3000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error generating consultation: {e}")
            return f"Error generating consultation: {str(e)}"
    
    def _compile_knowledge_summary(self) -> str:
        """Compile a summary of all knowledge from processed books"""
        
        all_concepts = []
        all_frameworks = []
        book_summaries = []
        
        for book in self.knowledge_base:
            book_summaries.append(f"**{book.title}**: {book.summary}")
            all_concepts.extend(book.key_concepts)
            all_frameworks.extend(book.frameworks)
        
        # Remove duplicates and get top concepts/frameworks
        unique_concepts = list(set(all_concepts))[:20]  # Top 20 concepts
        unique_frameworks = list(set(all_frameworks))[:15]  # Top 15 frameworks
        
        knowledge_summary = f"""
        MARKETING KNOWLEDGE BASE SUMMARY:
        
        Books Processed: {len(self.knowledge_base)}
        
        Key Marketing Concepts Available:
        {', '.join(unique_concepts)}
        
        Marketing Frameworks Available:
        {', '.join(unique_frameworks)}
        
        Book Summaries:
        {"\n".join(book_summaries)}
        """
        
        return knowledge_summary
    
    def _build_consultation_prompt(self, business_idea: str, specific_questions: Optional[List[str]], knowledge_summary: str) -> str:
        """Build the consultation prompt for OpenAI"""
        
        questions_section = ""
        if specific_questions:
            questions_section = f"""
            
            Specific Questions to Address:
            {"\n".join(f"- {q}" for q in specific_questions)}
            """
        
        prompt = f"""
        You are a world-class marketing consultant with deep expertise drawn from multiple authoritative marketing books. 
        You have access to comprehensive marketing knowledge and frameworks.
        
        {knowledge_summary}
        
        BUSINESS IDEA TO ANALYZE:
        {business_idea}
        {questions_section}
        
        Please provide a comprehensive marketing consultation that includes:
        
        1. MARKET ANALYSIS & OPPORTUNITY ASSESSMENT
        - Market size and growth potential
        - Target audience identification and segmentation
        - Competitive landscape analysis
        - Market entry barriers and opportunities
        
        2. POSITIONING & BRANDING STRATEGY
        - Unique value proposition development
        - Brand positioning recommendations
        - Messaging framework
        - Differentiation strategy
        
        3. MARKETING STRATEGY & TACTICS
        - Customer acquisition strategy
        - Channel strategy (digital, traditional, partnerships)
        - Content marketing approach
        - Pricing strategy considerations
        
        4. IMPLEMENTATION ROADMAP
        - Priority marketing initiatives
        - Resource requirements
        - Success metrics and KPIs
        - Timeline and milestones
        
        5. RISK ASSESSMENT & MITIGATION
        - Potential challenges and obstacles
        - Risk mitigation strategies
        - Alternative scenarios
        
        Base your recommendations on proven marketing frameworks and principles from your knowledge base.
        Provide specific, actionable advice rather than generic suggestions.
        Reference relevant frameworks, concepts, or strategies from the processed books where applicable.
        
        Make your consultation comprehensive but concise, focusing on the most impactful recommendations.
        """
        
        return prompt
    
    def get_knowledge_base_info(self) -> Dict[str, Any]:
        """Get information about the current knowledge base"""
        
        if not self.knowledge_base:
            return {"status": "empty", "message": "No books processed yet"}
        
        return {
            "status": "loaded",
            "total_books": len(self.knowledge_base),
            "books": [
                {
                    "title": book.title,
                    "filename": book.filename,
                    "processed_at": book.processed_at.isoformat(),
                    "key_concepts_count": len(book.key_concepts),
                    "frameworks_count": len(book.frameworks)
                }
                for book in self.knowledge_base
            ],
            "total_concepts": len(set(concept for book in self.knowledge_base for concept in book.key_concepts)),
            "total_frameworks": len(set(framework for book in self.knowledge_base for framework in book.frameworks))
        }

# Example usage
if __name__ == "__main__":
    # Initialize the agent
    agent = MarketingAgent(
        openai_api_key=str(os.getenv("OPENAI_API_KEY")),
        books_folder="Legal_Marketing_Agents/books"
    )
    
    # Check knowledge base status
    kb_info = agent.get_knowledge_base_info()
    print("Knowledge Base Status:")
    print(json.dumps(kb_info, indent=2))
    
    # Example business idea consultation
    business_idea = """
    I want to launch a subscription-based meal kit service that focuses on healthy, 
    plant-based meals for busy professionals. The meals would be pre-prepped and 
    ready to cook in under 15 minutes. I'm targeting health-conscious millennials 
    and Gen Z professionals in urban areas who value convenience and sustainability.
    """
    
    specific_questions = [
        "What's the best customer acquisition strategy for this market?",
        "How should I price my subscription tiers?",
        "What marketing channels should I prioritize?",
        "How can I differentiate from existing meal kit services?"
    ]
    
    # Get consultation
    consultation = agent.get_consultation(business_idea, specific_questions)
    print("\n" + "="*80)
    print("MARKETING CONSULTATION")
    print("="*80)
    print(consultation)

def get_agent():
    """Get an instance of the MarketingAgent"""
    return MarketingAgent(
        openai_api_key=str(os.getenv("OPENAI_API_KEY")),
        books_folder="Legal_Marketing_Agents/books"
    )
def set_knowledge_base(agent):
    with open("E:/Moccet/marketing_knowledge_cache.pkl", 'r') as f:
        knowledge = pickle.load(f)
        print(knowledge)
        agent.knowledge_base = knowledge
    agent.knowledge_base = knowledge
    return agent