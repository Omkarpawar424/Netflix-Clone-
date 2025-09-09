"""
AI-powered document processing for FRA claims and legacy documents
"""

import os
import cv2
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import asyncio
import logging
from datetime import datetime

# OCR and Text Processing
import pytesseract
from pdf2image import convert_from_path
import pdfplumber
from PIL import Image, ImageEnhance, ImageFilter

# NLP and NER
import spacy
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize, sent_tokenize

# ML Models
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import joblib

from app.core.config import settings

logger = logging.getLogger(__name__)

class DocumentPreprocessor:
    """Preprocesses documents for OCR and analysis"""
    
    def __init__(self):
        self.supported_formats = ['.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.tif']
    
    def preprocess_image(self, image_path: str) -> np.ndarray:
        """Preprocess image for better OCR results"""
        try:
            # Read image
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"Could not read image: {image_path}")
            
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Apply Gaussian blur to reduce noise
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            
            # Apply adaptive thresholding
            thresh = cv2.adaptiveThreshold(
                blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )
            
            # Morphological operations to clean up
            kernel = np.ones((2, 2), np.uint8)
            cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
            cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel)
            
            return cleaned
            
        except Exception as e:
            logger.error(f"Error preprocessing image {image_path}: {e}")
            raise
    
    def pdf_to_images(self, pdf_path: str, dpi: int = 300) -> List[np.ndarray]:
        """Convert PDF to images for OCR processing"""
        try:
            images = convert_from_path(pdf_path, dpi=dpi)
            processed_images = []
            
            for i, image in enumerate(images):
                # Convert PIL to OpenCV format
                opencv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
                
                # Preprocess
                processed = self.preprocess_image_array(opencv_image)
                processed_images.append(processed)
            
            return processed_images
            
        except Exception as e:
            logger.error(f"Error converting PDF to images {pdf_path}: {e}")
            raise
    
    def preprocess_image_array(self, image: np.ndarray) -> np.ndarray:
        """Preprocess numpy image array"""
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # Apply preprocessing steps
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        thresh = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        
        kernel = np.ones((2, 2), np.uint8)
        cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel)
        
        return cleaned

class OCREngine:
    """Optical Character Recognition engine with multi-language support"""
    
    def __init__(self):
        self.languages = '+'.join(settings.OCR_LANGUAGES)
        self.config = '--oem 3 --psm 6'  # LSTM OCR Engine Mode, Uniform block of text
    
    def extract_text_from_image(self, image: np.ndarray, confidence_threshold: float = 60.0) -> Dict[str, Any]:
        """Extract text from preprocessed image"""
        try:
            # Get detailed OCR data
            data = pytesseract.image_to_data(
                image, 
                lang=self.languages, 
                config=self.config,
                output_type=pytesseract.Output.DICT
            )
            
            # Filter by confidence
            filtered_text = []
            word_confidences = []
            
            for i, confidence in enumerate(data['conf']):
                if int(confidence) > confidence_threshold:
                    text = data['text'][i].strip()
                    if text:
                        filtered_text.append(text)
                        word_confidences.append(confidence)
            
            # Combine text
            extracted_text = ' '.join(filtered_text)
            avg_confidence = np.mean(word_confidences) if word_confidences else 0.0
            
            return {
                'text': extracted_text,
                'confidence': avg_confidence,
                'word_count': len(filtered_text),
                'raw_data': data
            }
            
        except Exception as e:
            logger.error(f"Error extracting text from image: {e}")
            return {'text': '', 'confidence': 0.0, 'word_count': 0, 'raw_data': None}
    
    def extract_text_from_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """Extract text from PDF using both text extraction and OCR"""
        try:
            all_text = []
            total_confidence = []
            
            # First, try direct text extraction
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text and text.strip():
                        all_text.append(text)
                        total_confidence.append(95.0)  # High confidence for direct extraction
            
            # If no text found or low quality, use OCR
            if not all_text or len(' '.join(all_text).strip()) < 100:
                preprocessor = DocumentPreprocessor()
                images = preprocessor.pdf_to_images(pdf_path)
                
                for image in images:
                    ocr_result = self.extract_text_from_image(image)
                    if ocr_result['text'].strip():
                        all_text.append(ocr_result['text'])
                        total_confidence.append(ocr_result['confidence'])
            
            combined_text = '\n\n'.join(all_text)
            avg_confidence = np.mean(total_confidence) if total_confidence else 0.0
            
            return {
                'text': combined_text,
                'confidence': avg_confidence,
                'page_count': len(all_text),
                'extraction_method': 'hybrid'
            }
            
        except Exception as e:
            logger.error(f"Error extracting text from PDF {pdf_path}: {e}")
            return {'text': '', 'confidence': 0.0, 'page_count': 0, 'extraction_method': 'failed'}

class FRAEntityRecognizer:
    """Named Entity Recognition specifically for FRA documents"""
    
    def __init__(self):
        self.nlp = None
        self.custom_ner = None
        self.initialize_models()
    
    def initialize_models(self):
        """Initialize NLP models"""
        try:
            # Load spaCy model
            self.nlp = spacy.load(settings.SPACY_MODEL)
            
            # Add custom FRA entity patterns
            self.add_fra_patterns()
            
            logger.info("FRA Entity Recognizer initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing FRA Entity Recognizer: {e}")
            raise
    
    def add_fra_patterns(self):
        """Add custom patterns for FRA-specific entities"""
        from spacy.matcher import Matcher
        
        matcher = Matcher(self.nlp.vocab)
        
        # Claim number patterns
        claim_patterns = [
            [{"TEXT": {"REGEX": r"^[A-Z]{2}/\d{4}/\d+$"}}],  # State/Year/Number format
            [{"TEXT": {"REGEX": r"^FRA/\d{4}/\d+$"}}],      # FRA/Year/Number format
            [{"LOWER": "claim"}, {"LOWER": "no"}, {"TEXT": {"REGEX": r"\d+"}}]
        ]
        matcher.add("CLAIM_NUMBER", claim_patterns)
        
        # Survey number patterns
        survey_patterns = [
            [{"LOWER": "survey"}, {"LOWER": "no"}, {"TEXT": {"REGEX": r"\d+(/\d+)?"}}],
            [{"LOWER": "sy"}, {"LOWER": "no"}, {"TEXT": {"REGEX": r"\d+(/\d+)?"}}]
        ]
        matcher.add("SURVEY_NUMBER", survey_patterns)
        
        # Area patterns
        area_patterns = [
            [{"TEXT": {"REGEX": r"\d+(\.\d+)?"}}, {"LOWER": {"IN": ["hectare", "hectares", "acre", "acres"]}}],
            [{"TEXT": {"REGEX": r"\d+(\.\d+)?"}}, {"LOWER": "ha"}]
        ]
        matcher.add("AREA", area_patterns)
        
        self.matcher = matcher
    
    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract FRA-specific entities from text"""
        try:
            doc = self.nlp(text)
            entities = {
                'PERSON': [],
                'LOCATION': [],
                'CLAIM_NUMBER': [],
                'SURVEY_NUMBER': [],
                'AREA': [],
                'DATE': [],
                'ORGANIZATION': []
            }
            
            # Standard spaCy entities
            for ent in doc.ents:
                if ent.label_ in ['PERSON', 'GPE', 'LOC', 'ORG', 'DATE']:
                    label = 'LOCATION' if ent.label_ in ['GPE', 'LOC'] else ent.label_
                    label = 'ORGANIZATION' if ent.label_ == 'ORG' else label
                    
                    if ent.text.strip() and ent.text not in entities[label]:
                        entities[label].append(ent.text.strip())
            
            # Custom pattern matches
            matches = self.matcher(doc)
            for match_id, start, end in matches:
                label = self.nlp.vocab.strings[match_id]
                span = doc[start:end]
                if span.text.strip() and span.text not in entities[label]:
                    entities[label].append(span.text.strip())
            
            return entities
            
        except Exception as e:
            logger.error(f"Error extracting entities: {e}")
            return {}
    
    def extract_structured_data(self, text: str) -> Dict[str, Any]:
        """Extract structured data specific to FRA claims"""
        try:
            entities = self.extract_entities(text)
            
            # Extract specific FRA information
            structured_data = {
                'claimant_name': self._extract_claimant_name(text, entities),
                'father_husband_name': self._extract_father_husband_name(text),
                'claim_number': entities.get('CLAIM_NUMBER', []),
                'survey_numbers': entities.get('SURVEY_NUMBER', []),
                'area_claimed': self._extract_area_claimed(text, entities),
                'village': self._extract_village(text, entities),
                'district': self._extract_district(text, entities),
                'state': self._extract_state(text, entities),
                'dates': entities.get('DATE', []),
                'land_type': self._extract_land_type(text),
                'claim_type': self._extract_claim_type(text)
            }
            
            return structured_data
            
        except Exception as e:
            logger.error(f"Error extracting structured data: {e}")
            return {}
    
    def _extract_claimant_name(self, text: str, entities: Dict) -> Optional[str]:
        """Extract claimant name from text"""
        persons = entities.get('PERSON', [])
        if persons:
            # Usually the first person mentioned is the claimant
            return persons[0]
        return None
    
    def _extract_father_husband_name(self, text: str) -> Optional[str]:
        """Extract father/husband name"""
        import re
        patterns = [
            r"s/o\s+([A-Za-z\s]+)",
            r"son of\s+([A-Za-z\s]+)",
            r"w/o\s+([A-Za-z\s]+)",
            r"wife of\s+([A-Za-z\s]+)",
            r"d/o\s+([A-Za-z\s]+)",
            r"daughter of\s+([A-Za-z\s]+)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _extract_area_claimed(self, text: str, entities: Dict) -> Optional[float]:
        """Extract area claimed in hectares"""
        areas = entities.get('AREA', [])
        if areas:
            import re
            for area_text in areas:
                # Extract numeric value
                match = re.search(r'(\d+(?:\.\d+)?)', area_text)
                if match:
                    value = float(match.group(1))
                    # Convert to hectares if needed
                    if 'acre' in area_text.lower():
                        value = value * 0.4047  # Convert acres to hectares
                    return value
        return None
    
    def _extract_village(self, text: str, entities: Dict) -> Optional[str]:
        """Extract village name"""
        locations = entities.get('LOCATION', [])
        # Simple heuristic: look for "village" keyword
        import re
        village_pattern = r"village[:\s]+([A-Za-z\s]+)"
        match = re.search(village_pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        # Fallback to first location if no specific village found
        if locations:
            return locations[0]
        return None
    
    def _extract_district(self, text: str, entities: Dict) -> Optional[str]:
        """Extract district name"""
        import re
        district_pattern = r"district[:\s]+([A-Za-z\s]+)"
        match = re.search(district_pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None
    
    def _extract_state(self, text: str, entities: Dict) -> Optional[str]:
        """Extract state name"""
        # Check against supported states
        for state in settings.SUPPORTED_STATES:
            if state.lower() in text.lower():
                return state
        return None
    
    def _extract_land_type(self, text: str) -> Optional[str]:
        """Extract type of land claimed"""
        land_types = ['forest land', 'agricultural land', 'grazing land', 'water body']
        for land_type in land_types:
            if land_type in text.lower():
                return land_type
        return None
    
    def _extract_claim_type(self, text: str) -> Optional[str]:
        """Extract type of FRA claim"""
        claim_types = ['individual', 'community', 'community forest resource']
        for claim_type in claim_types:
            if claim_type in text.lower():
                return claim_type
        return 'individual'  # Default

class DocumentClassifier:
    """Classify documents into different types"""
    
    def __init__(self):
        self.model = None
        self.vectorizer = None
        self.initialize_classifier()
    
    def initialize_classifier(self):
        """Initialize document classification model"""
        try:
            # Create a simple classification pipeline
            self.vectorizer = TfidfVectorizer(max_features=5000, stop_words='english')
            self.model = MultinomialNB()
            
            # In a real implementation, you would train this on labeled data
            # For now, we'll use a rule-based approach combined with keywords
            self.document_keywords = {
                'fra_claim': ['forest rights', 'claim', 'title', 'patatta', 'gram sabha'],
                'title_deed': ['title deed', 'ownership', 'property', 'deed'],
                'survey_settlement': ['survey', 'settlement', 'revenue', 'survey number'],
                'identity_proof': ['aadhar', 'voter id', 'driving license', 'passport'],
                'community_certificate': ['community certificate', 'caste certificate', 'tribe'],
                'forest_clearance': ['forest clearance', 'clearance', 'permission', 'forest department']
            }
            
            logger.info("Document classifier initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing document classifier: {e}")
            raise
    
    def classify_document(self, text: str) -> Dict[str, Any]:
        """Classify document based on content"""
        try:
            text_lower = text.lower()
            scores = {}
            
            # Calculate keyword-based scores
            for doc_type, keywords in self.document_keywords.items():
                score = 0
                for keyword in keywords:
                    if keyword in text_lower:
                        score += text_lower.count(keyword)
                scores[doc_type] = score
            
            # Get the document type with highest score
            if scores:
                predicted_type = max(scores, key=scores.get)
                confidence = scores[predicted_type] / max(1, len(text.split()) / 100)
                confidence = min(confidence, 1.0)  # Cap at 1.0
            else:
                predicted_type = 'other'
                confidence = 0.0
            
            return {
                'document_type': predicted_type,
                'confidence': confidence,
                'scores': scores
            }
            
        except Exception as e:
            logger.error(f"Error classifying document: {e}")
            return {'document_type': 'other', 'confidence': 0.0, 'scores': {}}

class DocumentProcessor:
    """Main document processing orchestrator"""
    
    def __init__(self):
        self.ocr_engine = OCREngine()
        self.entity_recognizer = FRAEntityRecognizer()
        self.classifier = DocumentClassifier()
        self.preprocessor = DocumentPreprocessor()
    
    async def process_document(self, file_path: str) -> Dict[str, Any]:
        """Process a document completely"""
        try:
            file_ext = Path(file_path).suffix.lower()
            
            # Extract text based on file type
            if file_ext == '.pdf':
                ocr_result = self.ocr_engine.extract_text_from_pdf(file_path)
            elif file_ext in ['.jpg', '.jpeg', '.png', '.tiff', '.tif']:
                processed_image = self.preprocessor.preprocess_image(file_path)
                ocr_result = self.ocr_engine.extract_text_from_image(processed_image)
            else:
                raise ValueError(f"Unsupported file format: {file_ext}")
            
            extracted_text = ocr_result['text']
            
            if not extracted_text.strip():
                return {
                    'status': 'failed',
                    'error': 'No text could be extracted from document',
                    'confidence': 0.0
                }
            
            # Classify document
            classification_result = self.classifier.classify_document(extracted_text)
            
            # Extract entities and structured data
            structured_data = self.entity_recognizer.extract_structured_data(extracted_text)
            
            # Compile results
            result = {
                'status': 'success',
                'extracted_text': extracted_text,
                'ocr_confidence': ocr_result['confidence'],
                'document_type': classification_result['document_type'],
                'classification_confidence': classification_result['confidence'],
                'structured_data': structured_data,
                'processing_timestamp': datetime.utcnow().isoformat(),
                'file_info': {
                    'filename': Path(file_path).name,
                    'file_size': Path(file_path).stat().st_size,
                    'file_type': file_ext
                }
            }
            
            # Calculate overall confidence
            overall_confidence = (
                ocr_result['confidence'] * 0.6 + 
                classification_result['confidence'] * 100 * 0.4
            ) / 100
            result['overall_confidence'] = overall_confidence
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing document {file_path}: {e}")
            return {
                'status': 'failed',
                'error': str(e),
                'confidence': 0.0,
                'processing_timestamp': datetime.utcnow().isoformat()
            }
    
    async def batch_process_documents(self, file_paths: List[str]) -> List[Dict[str, Any]]:
        """Process multiple documents in batch"""
        tasks = [self.process_document(file_path) for file_path in file_paths]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    'status': 'failed',
                    'error': str(result),
                    'file_path': file_paths[i],
                    'confidence': 0.0
                })
            else:
                processed_results.append(result)
        
        return processed_results