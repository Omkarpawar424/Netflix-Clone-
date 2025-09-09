"""
Core configuration settings for the FRA Decision Support System
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List, Optional
import os
from pathlib import Path

class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    APP_NAME: str = "FRA Decision Support System"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    DEBUG: bool = Field(default=True, env="DEBUG")
    
    # Database
    DATABASE_URL: str = Field(
        default="postgresql://fra_user:fra_password@localhost/fra_database",
        env="DATABASE_URL"
    )
    
    # Security
    SECRET_KEY: str = Field(
        default="your-secret-key-change-in-production",
        env="SECRET_KEY"
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, env="REFRESH_TOKEN_EXPIRE_DAYS")
    
    # CORS
    ALLOWED_HOSTS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000", "*"],
        env="ALLOWED_HOSTS"
    )
    
    # File Storage
    UPLOAD_DIR: str = Field(default="data/uploads", env="UPLOAD_DIR")
    MAX_FILE_SIZE: int = Field(default=100 * 1024 * 1024, env="MAX_FILE_SIZE")  # 100MB
    ALLOWED_EXTENSIONS: List[str] = Field(
        default=["pdf", "doc", "docx", "jpg", "jpeg", "png", "tiff", "tif"],
        env="ALLOWED_EXTENSIONS"
    )
    
    # AI Models
    MODELS_DIR: str = Field(default="app/ai_models/trained_models", env="MODELS_DIR")
    SPACY_MODEL: str = Field(default="en_core_web_sm", env="SPACY_MODEL")
    
    # Satellite Imagery
    SATELLITE_DATA_DIR: str = Field(default="data/satellite_images", env="SATELLITE_DATA_DIR")
    SUPPORTED_SATELLITES: List[str] = Field(
        default=["Landsat-8", "Landsat-9", "Sentinel-2"],
        env="SUPPORTED_SATELLITES"
    )
    
    # GIS Configuration
    DEFAULT_CRS: str = Field(default="EPSG:4326", env="DEFAULT_CRS")  # WGS84
    INDIA_CRS: str = Field(default="EPSG:32643", env="INDIA_CRS")  # WGS 84 / UTM zone 43N
    
    # States Configuration
    SUPPORTED_STATES: List[str] = Field(
        default=["Madhya Pradesh", "Tripura", "Odisha", "Telangana"],
        env="SUPPORTED_STATES"
    )
    
    # External APIs
    GOVERNMENT_API_BASE_URL: Optional[str] = Field(default=None, env="GOVERNMENT_API_BASE_URL")
    SATELLITE_API_KEY: Optional[str] = Field(default=None, env="SATELLITE_API_KEY")
    
    # Performance Settings
    MAX_CONCURRENT_REQUESTS: int = Field(default=100, env="MAX_CONCURRENT_REQUESTS")
    CACHE_TTL: int = Field(default=3600, env="CACHE_TTL")  # 1 hour
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FILE: str = Field(default="logs/fra_dss.log", env="LOG_FILE")
    
    # ML Model Configuration
    DOCUMENT_PROCESSING_MODEL_PATH: str = Field(
        default="app/ai_models/trained_models/document_ner_model",
        env="DOCUMENT_PROCESSING_MODEL_PATH"
    )
    LAND_CLASSIFICATION_MODEL_PATH: str = Field(
        default="app/ai_models/trained_models/land_classifier_model",
        env="LAND_CLASSIFICATION_MODEL_PATH"
    )
    ASSET_DETECTION_MODEL_PATH: str = Field(
        default="app/ai_models/trained_models/asset_detector_model",
        env="ASSET_DETECTION_MODEL_PATH"
    )
    
    # Classification Labels
    LAND_USE_CLASSES: List[str] = Field(
        default=[
            "Forest",
            "Agricultural Land",
            "Water Body",
            "Built-up Area",
            "Barren Land",
            "Grassland",
            "Wetland"
        ],
        env="LAND_USE_CLASSES"
    )
    
    ASSET_CLASSES: List[str] = Field(
        default=[
            "Houses",
            "Wells",
            "Ponds",
            "Agricultural Fields",
            "Community Buildings",
            "Roads",
            "Temples",
            "Schools"
        ],
        env="ASSET_CLASSES"
    )
    
    # Document Processing
    OCR_LANGUAGES: List[str] = Field(
        default=["eng", "hin", "ben", "ori", "tel"],
        env="OCR_LANGUAGES"
    )
    
    # Performance Thresholds
    DOCUMENT_ACCURACY_THRESHOLD: float = Field(default=0.95, env="DOCUMENT_ACCURACY_THRESHOLD")
    CLASSIFICATION_CONFIDENCE_THRESHOLD: float = Field(default=0.85, env="CLASSIFICATION_CONFIDENCE_THRESHOLD")
    
    class Config:
        env_file = ".env"
        case_sensitive = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Create necessary directories
        self._create_directories()
    
    def _create_directories(self):
        """Create necessary directories if they don't exist"""
        directories = [
            self.UPLOAD_DIR,
            self.MODELS_DIR,
            self.SATELLITE_DATA_DIR,
            Path(self.LOG_FILE).parent,
            "data/processed",
            "data/temp"
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)

# Create global settings instance
settings = Settings()

# State-specific configuration
STATE_CONFIG = {
    "Madhya Pradesh": {
        "code": "MP",
        "capital": "Bhopal",
        "districts": 52,
        "forest_cover_percent": 25.11,
        "tribal_population_percent": 21.1,
        "priority_districts": ["Balaghat", "Mandla", "Dindori", "Seoni", "Chhindwara"]
    },
    "Tripura": {
        "code": "TR",
        "capital": "Agartala", 
        "districts": 8,
        "forest_cover_percent": 73.68,
        "tribal_population_percent": 31.8,
        "priority_districts": ["Dhalai", "Khowai", "Gomati", "South Tripura"]
    },
    "Odisha": {
        "code": "OR",
        "capital": "Bhubaneswar",
        "districts": 30,
        "forest_cover_percent": 33.16,
        "tribal_population_percent": 22.8,
        "priority_districts": ["Mayurbhanj", "Keonjhar", "Sundargarh", "Kandhamal", "Rayagada"]
    },
    "Telangana": {
        "code": "TS", 
        "capital": "Hyderabad",
        "districts": 33,
        "forest_cover_percent": 24.03,
        "tribal_population_percent": 12.9,
        "priority_districts": ["Adilabad", "Kumuram Bheem", "Mancherial", "Jayashankar"]
    }
}

# Central Sector Schemes mapping
CENTRAL_SCHEMES = {
    "MGNREGA": {
        "full_name": "Mahatma Gandhi National Rural Employment Guarantee Act",
        "ministry": "Ministry of Rural Development",
        "eligibility_criteria": ["rural_household", "adult_member", "unskilled_work"]
    },
    "PM-KISAN": {
        "full_name": "Pradhan Mantri Kisan Samman Nidhi",
        "ministry": "Ministry of Agriculture and Farmers Welfare", 
        "eligibility_criteria": ["small_marginal_farmer", "landholding_upto_2ha"]
    },
    "PMAY": {
        "full_name": "Pradhan Mantri Awas Yojana",
        "ministry": "Ministry of Housing and Urban Affairs",
        "eligibility_criteria": ["below_poverty_line", "no_pucca_house"]
    },
    "PMJDY": {
        "full_name": "Pradhan Mantri Jan Dhan Yojana",
        "ministry": "Ministry of Finance",
        "eligibility_criteria": ["no_bank_account", "indian_citizen"]
    },
    "Ayushman Bharat": {
        "full_name": "Pradhan Mantri Jan Arogya Yojana",
        "ministry": "Ministry of Health and Family Welfare",
        "eligibility_criteria": ["below_poverty_line", "rural_household"]
    }
}