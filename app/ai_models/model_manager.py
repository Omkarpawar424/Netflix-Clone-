"""
AI Model Manager for coordinating all AI/ML models in the FRA system
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
import joblib
import numpy as np
from datetime import datetime
import json

from app.ai_models.document_processor import DocumentProcessor
from app.ai_models.satellite_analyzer import SatelliteAnalyzer
from app.core.config import settings

logger = logging.getLogger(__name__)

class ModelManager:
    """Central manager for all AI/ML models"""
    
    def __init__(self):
        self.models = {}
        self.model_status = {}
        self.models_loaded = False
        
        # Initialize processors
        self.document_processor = None
        self.satellite_analyzer = None
        
    async def initialize_models(self):
        """Initialize all AI/ML models"""
        try:
            logger.info("🤖 Initializing AI models...")
            
            # Initialize document processing models
            await self._initialize_document_models()
            
            # Initialize satellite analysis models
            await self._initialize_satellite_models()
            
            # Initialize additional models
            await self._initialize_additional_models()
            
            self.models_loaded = True
            logger.info("✅ All AI models initialized successfully!")
            
        except Exception as e:
            logger.error(f"❌ Error initializing AI models: {e}")
            raise
    
    async def _initialize_document_models(self):
        """Initialize document processing models"""
        try:
            logger.info("📄 Initializing document processing models...")
            
            # Initialize document processor
            self.document_processor = DocumentProcessor()
            self.model_status['document_processor'] = 'loaded'
            
            # Check for pre-trained models
            model_path = Path(settings.DOCUMENT_PROCESSING_MODEL_PATH)
            if model_path.exists():
                logger.info(f"📁 Loading pre-trained document NER model from {model_path}")
                # In a real implementation, load the trained model here
                self.model_status['document_ner'] = 'loaded'
            else:
                logger.warning(f"⚠️ Pre-trained document NER model not found at {model_path}")
                self.model_status['document_ner'] = 'not_found'
            
            logger.info("✅ Document processing models initialized")
            
        except Exception as e:
            logger.error(f"❌ Error initializing document models: {e}")
            self.model_status['document_processor'] = 'error'
            raise
    
    async def _initialize_satellite_models(self):
        """Initialize satellite analysis models"""
        try:
            logger.info("🛰️ Initializing satellite analysis models...")
            
            # Initialize satellite analyzer
            self.satellite_analyzer = SatelliteAnalyzer()
            self.model_status['satellite_analyzer'] = 'loaded'
            
            # Check for pre-trained land classification model
            land_model_path = Path(settings.LAND_CLASSIFICATION_MODEL_PATH)
            if land_model_path.exists():
                logger.info(f"📁 Loading pre-trained land classification model from {land_model_path}")
                # In a real implementation, load the trained model here
                self.model_status['land_classifier'] = 'loaded'
            else:
                logger.warning(f"⚠️ Pre-trained land classification model not found at {land_model_path}")
                self.model_status['land_classifier'] = 'not_found'
            
            # Check for pre-trained asset detection model
            asset_model_path = Path(settings.ASSET_DETECTION_MODEL_PATH)
            if asset_model_path.exists():
                logger.info(f"📁 Loading pre-trained asset detection model from {asset_model_path}")
                # In a real implementation, load the trained model here
                self.model_status['asset_detector'] = 'loaded'
            else:
                logger.warning(f"⚠️ Pre-trained asset detection model not found at {asset_model_path}")
                self.model_status['asset_detector'] = 'not_found'
            
            logger.info("✅ Satellite analysis models initialized")
            
        except Exception as e:
            logger.error(f"❌ Error initializing satellite models: {e}")
            self.model_status['satellite_analyzer'] = 'error'
            raise
    
    async def _initialize_additional_models(self):
        """Initialize additional AI models"""
        try:
            logger.info("🔧 Initializing additional models...")
            
            # Scheme recommendation model (rule-based for now)
            self.models['scheme_recommender'] = SchemeRecommender()
            self.model_status['scheme_recommender'] = 'loaded'
            
            # Change detection model (placeholder)
            self.model_status['change_detector'] = 'placeholder'
            
            logger.info("✅ Additional models initialized")
            
        except Exception as e:
            logger.error(f"❌ Error initializing additional models: {e}")
            raise
    
    def is_model_loaded(self, model_name: str) -> bool:
        """Check if a specific model is loaded"""
        return self.model_status.get(model_name) == 'loaded'
    
    def get_model_status(self) -> Dict[str, str]:
        """Get status of all models"""
        return self.model_status.copy()
    
    async def process_document(self, file_path: str) -> Dict[str, Any]:
        """Process a document using the document processor"""
        if not self.document_processor:
            raise RuntimeError("Document processor not initialized")
        
        return await self.document_processor.process_document(file_path)
    
    async def analyze_satellite_image(self, image_path: str, analysis_type: str = "full") -> Dict[str, Any]:
        """Analyze satellite image"""
        if not self.satellite_analyzer:
            raise RuntimeError("Satellite analyzer not initialized")
        
        return await self.satellite_analyzer.analyze_satellite_image(image_path, analysis_type)
    
    async def recommend_schemes(self, fra_holder_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Recommend government schemes for FRA holder"""
        if 'scheme_recommender' not in self.models:
            raise RuntimeError("Scheme recommender not initialized")
        
        return self.models['scheme_recommender'].recommend_schemes(fra_holder_data)
    
    async def cleanup(self):
        """Clean up models and resources"""
        try:
            logger.info("🧹 Cleaning up AI models...")
            
            # Clean up document processor
            if self.document_processor:
                # Any cleanup needed
                pass
            
            # Clean up satellite analyzer
            if self.satellite_analyzer:
                # Any cleanup needed
                pass
            
            # Clear models
            self.models.clear()
            self.model_status.clear()
            self.models_loaded = False
            
            logger.info("✅ AI models cleanup complete")
            
        except Exception as e:
            logger.error(f"❌ Error during cleanup: {e}")
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get comprehensive system information"""
        return {
            'models_loaded': self.models_loaded,
            'model_status': self.model_status,
            'available_models': list(self.models.keys()),
            'document_processor_ready': self.document_processor is not None,
            'satellite_analyzer_ready': self.satellite_analyzer is not None,
            'supported_document_types': ['pdf', 'jpg', 'jpeg', 'png', 'tiff', 'tif'],
            'supported_satellite_formats': ['tif', 'tiff', 'jp2', 'img'],
            'land_use_classes': settings.LAND_USE_CLASSES,
            'asset_classes': settings.ASSET_CLASSES,
            'supported_languages': settings.OCR_LANGUAGES
        }

class SchemeRecommender:
    """Rule-based scheme recommendation system"""
    
    def __init__(self):
        self.scheme_rules = self._initialize_scheme_rules()
    
    def _initialize_scheme_rules(self) -> Dict[str, Dict]:
        """Initialize scheme eligibility rules"""
        return {
            'MGNREGA': {
                'eligibility_criteria': {
                    'rural_household': True,
                    'adult_member': True,
                    'employment_demanded': True
                },
                'priority_score': lambda data: self._calculate_mgnrega_score(data)
            },
            'PM-KISAN': {
                'eligibility_criteria': {
                    'farmer': True,
                    'landholding_upto_2ha': True
                },
                'priority_score': lambda data: self._calculate_pmkisan_score(data)
            },
            'PMAY': {
                'eligibility_criteria': {
                    'below_poverty_line': True,
                    'no_pucca_house': True
                },
                'priority_score': lambda data: self._calculate_pmay_score(data)
            },
            'PMJDY': {
                'eligibility_criteria': {
                    'no_bank_account': True,
                    'indian_citizen': True
                },
                'priority_score': lambda data: self._calculate_pmjdy_score(data)
            },
            'Ayushman Bharat': {
                'eligibility_criteria': {
                    'below_poverty_line': True,
                    'rural_household': True
                },
                'priority_score': lambda data: self._calculate_ayushman_score(data)
            }
        }
    
    def recommend_schemes(self, fra_holder_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Recommend schemes based on FRA holder profile"""
        try:
            recommendations = []
            
            for scheme_name, scheme_info in self.scheme_rules.items():
                # Check eligibility
                eligible = self._check_eligibility(fra_holder_data, scheme_info['eligibility_criteria'])
                
                if eligible:
                    # Calculate priority score
                    priority_score = scheme_info['priority_score'](fra_holder_data)
                    
                    recommendations.append({
                        'scheme_name': scheme_name,
                        'eligible': True,
                        'priority_score': priority_score,
                        'recommendation_reason': self._get_recommendation_reason(scheme_name, fra_holder_data),
                        'next_steps': self._get_next_steps(scheme_name),
                        'estimated_benefit': self._get_estimated_benefit(scheme_name, fra_holder_data)
                    })
            
            # Sort by priority score
            recommendations.sort(key=lambda x: x['priority_score'], reverse=True)
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error recommending schemes: {e}")
            return []
    
    def _check_eligibility(self, data: Dict[str, Any], criteria: Dict[str, bool]) -> bool:
        """Check if FRA holder meets eligibility criteria"""
        for criterion, required in criteria.items():
            if required and not data.get(criterion, False):
                return False
        return True
    
    def _calculate_mgnrega_score(self, data: Dict[str, Any]) -> float:
        """Calculate MGNREGA priority score"""
        score = 0.5  # Base score
        
        # Higher score for tribal households
        if data.get('is_tribal', False):
            score += 0.3
        
        # Higher score for women-headed households
        if data.get('woman_headed_household', False):
            score += 0.2
        
        # Higher score for lower income
        income = data.get('annual_income', 50000)
        if income < 20000:
            score += 0.3
        elif income < 50000:
            score += 0.2
        
        return min(score, 1.0)
    
    def _calculate_pmkisan_score(self, data: Dict[str, Any]) -> float:
        """Calculate PM-KISAN priority score"""
        score = 0.4  # Base score
        
        # Higher score for small farmers
        landholding = data.get('landholding_hectares', 0)
        if landholding <= 1:
            score += 0.4
        elif landholding <= 2:
            score += 0.3
        
        # Higher score for tribal farmers
        if data.get('is_tribal', False):
            score += 0.2
        
        return min(score, 1.0)
    
    def _calculate_pmay_score(self, data: Dict[str, Any]) -> float:
        """Calculate PMAY priority score"""
        score = 0.3  # Base score
        
        # Higher score for homeless/kutcha house
        housing_type = data.get('housing_type', 'kutcha')
        if housing_type == 'homeless':
            score += 0.5
        elif housing_type == 'kutcha':
            score += 0.3
        
        # Higher score for women ownership
        if data.get('woman_ownership', False):
            score += 0.2
        
        return min(score, 1.0)
    
    def _calculate_pmjdy_score(self, data: Dict[str, Any]) -> float:
        """Calculate PMJDY priority score"""
        score = 0.6  # Base score
        
        # Higher score for women
        if data.get('gender', '') == 'female':
            score += 0.2
        
        # Higher score for tribal population
        if data.get('is_tribal', False):
            score += 0.2
        
        return min(score, 1.0)
    
    def _calculate_ayushman_score(self, data: Dict[str, Any]) -> float:
        """Calculate Ayushman Bharat priority score"""
        score = 0.4  # Base score
        
        # Higher score for elderly or disabled members
        if data.get('elderly_members', 0) > 0:
            score += 0.2
        
        if data.get('disabled_members', 0) > 0:
            score += 0.2
        
        # Higher score for larger families
        family_size = data.get('family_size', 1)
        if family_size >= 5:
            score += 0.2
        
        return min(score, 1.0)
    
    def _get_recommendation_reason(self, scheme_name: str, data: Dict[str, Any]) -> str:
        """Get reason for recommendation"""
        reasons = {
            'MGNREGA': "Guaranteed employment opportunity for rural household",
            'PM-KISAN': "Direct income support for small and marginal farmers",
            'PMAY': "Housing assistance for homeless/inadequate housing",
            'PMJDY': "Financial inclusion through bank account opening",
            'Ayushman Bharat': "Health insurance coverage for medical emergencies"
        }
        return reasons.get(scheme_name, "Eligible for this government scheme")
    
    def _get_next_steps(self, scheme_name: str) -> List[str]:
        """Get next steps for scheme application"""
        steps = {
            'MGNREGA': [
                "Apply for job card at Gram Panchayat",
                "Demand work in writing",
                "Get work within 15 days or unemployment allowance"
            ],
            'PM-KISAN': [
                "Visit nearest Common Service Center",
                "Carry land documents and Aadhar card",
                "Complete online registration"
            ],
            'PMAY': [
                "Apply through PMAY portal or CSC",
                "Submit required documents",
                "Wait for beneficiary selection"
            ],
            'PMJDY': [
                "Visit nearest bank branch",
                "Carry Aadhar card",
                "Open zero-balance account"
            ],
            'Ayushman Bharat': [
                "Check eligibility on official website",
                "Visit nearest empaneled hospital",
                "Generate e-card using Aadhar"
            ]
        }
        return steps.get(scheme_name, ["Contact local government office"])
    
    def _get_estimated_benefit(self, scheme_name: str, data: Dict[str, Any]) -> str:
        """Get estimated benefit amount"""
        benefits = {
            'MGNREGA': "₹200-300 per day for guaranteed work days",
            'PM-KISAN': "₹6,000 per year in three installments",
            'PMAY': "₹1.2-2.5 lakhs for house construction",
            'PMJDY': "Free bank account with insurance benefits",
            'Ayushman Bharat': "₹5 lakhs health insurance coverage per family"
        }
        return benefits.get(scheme_name, "Benefit amount varies")