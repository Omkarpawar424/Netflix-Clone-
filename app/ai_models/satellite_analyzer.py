"""
Computer Vision models for satellite imagery analysis and land-use classification
"""

import os
import cv2
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, Union
from pathlib import Path
import asyncio
import logging
from datetime import datetime
import json

# Deep Learning
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision import transforms, models
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix

# Geospatial
import rasterio
from rasterio.windows import Window
from rasterio.features import shapes
import geopandas as gpd
from shapely.geometry import shape, Point, Polygon
import folium

# Image Processing
from skimage import filters, morphology, measure, segmentation
from skimage.feature import local_binary_pattern
from scipy import ndimage
import matplotlib.pyplot as plt

from app.core.config import settings

logger = logging.getLogger(__name__)

class SatelliteImageProcessor:
    """Process satellite imagery for analysis"""
    
    def __init__(self):
        self.supported_formats = ['.tif', '.tiff', '.jp2', '.img']
        self.target_size = (256, 256)
    
    def load_satellite_image(self, image_path: str) -> Dict[str, Any]:
        """Load satellite image with metadata"""
        try:
            with rasterio.open(image_path) as src:
                # Read image data
                image_data = src.read()
                
                # Get metadata
                metadata = {
                    'bounds': src.bounds,
                    'crs': src.crs,
                    'transform': src.transform,
                    'width': src.width,
                    'height': src.height,
                    'count': src.count,
                    'dtype': src.dtypes[0],
                    'nodata': src.nodata
                }
                
                return {
                    'data': image_data,
                    'metadata': metadata,
                    'profile': src.profile
                }
                
        except Exception as e:
            logger.error(f"Error loading satellite image {image_path}: {e}")
            raise
    
    def preprocess_for_classification(self, image_data: np.ndarray) -> np.ndarray:
        """Preprocess satellite image for land-use classification"""
        try:
            # Handle different band configurations
            if len(image_data.shape) == 3 and image_data.shape[0] > 3:
                # Multi-spectral image - select RGB bands or create false color composite
                if image_data.shape[0] >= 4:
                    # Use NIR, Red, Green for vegetation analysis
                    processed = np.stack([
                        image_data[3],  # NIR
                        image_data[2],  # Red  
                        image_data[1]   # Green
                    ], axis=0)
                else:
                    processed = image_data[:3]
            else:
                processed = image_data
            
            # Normalize pixel values
            processed = self.normalize_bands(processed)
            
            # Calculate vegetation indices
            ndvi = self.calculate_ndvi(processed)
            ndwi = self.calculate_ndwi(processed)
            
            # Stack with original bands
            if len(processed.shape) == 3:
                # Add indices as additional bands
                enhanced = np.concatenate([
                    processed,
                    ndvi[np.newaxis, :, :],
                    ndwi[np.newaxis, :, :]
                ], axis=0)
            else:
                enhanced = processed
            
            return enhanced
            
        except Exception as e:
            logger.error(f"Error preprocessing satellite image: {e}")
            raise
    
    def normalize_bands(self, image_data: np.ndarray) -> np.ndarray:
        """Normalize satellite image bands"""
        normalized = np.zeros_like(image_data, dtype=np.float32)
        
        for i in range(image_data.shape[0]):
            band = image_data[i].astype(np.float32)
            
            # Remove outliers (2% and 98% percentiles)
            p2, p98 = np.percentile(band[band > 0], [2, 98])
            band = np.clip(band, p2, p98)
            
            # Normalize to 0-1
            band_min, band_max = band.min(), band.max()
            if band_max > band_min:
                normalized[i] = (band - band_min) / (band_max - band_min)
            else:
                normalized[i] = band
        
        return normalized
    
    def calculate_ndvi(self, image_data: np.ndarray) -> np.ndarray:
        """Calculate Normalized Difference Vegetation Index"""
        try:
            if image_data.shape[0] >= 4:
                nir = image_data[3].astype(np.float32)  # Near Infrared
                red = image_data[2].astype(np.float32)  # Red
            elif image_data.shape[0] >= 3:
                # Assume RGB format, use green as proxy for NIR
                nir = image_data[1].astype(np.float32)  # Green
                red = image_data[0].astype(np.float32)  # Red
            else:
                return np.zeros(image_data.shape[1:], dtype=np.float32)
            
            # Calculate NDVI
            denominator = nir + red
            ndvi = np.divide(
                nir - red,
                denominator,
                out=np.zeros_like(denominator),
                where=denominator != 0
            )
            
            return np.clip(ndvi, -1, 1)
            
        except Exception as e:
            logger.error(f"Error calculating NDVI: {e}")
            return np.zeros(image_data.shape[1:], dtype=np.float32)
    
    def calculate_ndwi(self, image_data: np.ndarray) -> np.ndarray:
        """Calculate Normalized Difference Water Index"""
        try:
            if image_data.shape[0] >= 4:
                green = image_data[1].astype(np.float32)  # Green
                nir = image_data[3].astype(np.float32)    # Near Infrared
            elif image_data.shape[0] >= 3:
                green = image_data[1].astype(np.float32)  # Green
                nir = image_data[2].astype(np.float32)    # Red as proxy
            else:
                return np.zeros(image_data.shape[1:], dtype=np.float32)
            
            # Calculate NDWI
            denominator = green + nir
            ndwi = np.divide(
                green - nir,
                denominator,
                out=np.zeros_like(denominator),
                where=denominator != 0
            )
            
            return np.clip(ndwi, -1, 1)
            
        except Exception as e:
            logger.error(f"Error calculating NDWI: {e}")
            return np.zeros(image_data.shape[1:], dtype=np.float32)
    
    def create_image_patches(self, image_data: np.ndarray, patch_size: int = 256, overlap: int = 32) -> List[np.ndarray]:
        """Create overlapping patches from large satellite image"""
        patches = []
        h, w = image_data.shape[-2:]
        
        for y in range(0, h - patch_size + 1, patch_size - overlap):
            for x in range(0, w - patch_size + 1, patch_size - overlap):
                if len(image_data.shape) == 3:
                    patch = image_data[:, y:y+patch_size, x:x+patch_size]
                else:
                    patch = image_data[y:y+patch_size, x:x+patch_size]
                patches.append(patch)
        
        return patches

class LandUseClassifier:
    """Land use classification using deep learning and traditional ML"""
    
    def __init__(self):
        self.cnn_model = None
        self.rf_model = None
        self.class_names = settings.LAND_USE_CLASSES
        self.num_classes = len(self.class_names)
        self.initialize_models()
    
    def initialize_models(self):
        """Initialize classification models"""
        try:
            self.cnn_model = self.build_cnn_model()
            self.rf_model = RandomForestClassifier(n_estimators=100, random_state=42)
            logger.info("Land use classification models initialized")
        except Exception as e:
            logger.error(f"Error initializing classification models: {e}")
            raise
    
    def build_cnn_model(self) -> keras.Model:
        """Build CNN model for land use classification"""
        model = keras.Sequential([
            # Input layer
            layers.Input(shape=(256, 256, 5)),  # RGB + NDVI + NDWI
            
            # First convolutional block
            layers.Conv2D(32, (3, 3), activation='relu', padding='same'),
            layers.BatchNormalization(),
            layers.Conv2D(32, (3, 3), activation='relu', padding='same'),
            layers.MaxPooling2D((2, 2)),
            layers.Dropout(0.25),
            
            # Second convolutional block
            layers.Conv2D(64, (3, 3), activation='relu', padding='same'),
            layers.BatchNormalization(),
            layers.Conv2D(64, (3, 3), activation='relu', padding='same'),
            layers.MaxPooling2D((2, 2)),
            layers.Dropout(0.25),
            
            # Third convolutional block
            layers.Conv2D(128, (3, 3), activation='relu', padding='same'),
            layers.BatchNormalization(),
            layers.Conv2D(128, (3, 3), activation='relu', padding='same'),
            layers.MaxPooling2D((2, 2)),
            layers.Dropout(0.25),
            
            # Fourth convolutional block
            layers.Conv2D(256, (3, 3), activation='relu', padding='same'),
            layers.BatchNormalization(),
            layers.Conv2D(256, (3, 3), activation='relu', padding='same'),
            layers.GlobalAveragePooling2D(),
            layers.Dropout(0.5),
            
            # Dense layers
            layers.Dense(512, activation='relu'),
            layers.BatchNormalization(),
            layers.Dropout(0.5),
            layers.Dense(256, activation='relu'),
            layers.BatchNormalization(),
            layers.Dropout(0.5),
            
            # Output layer
            layers.Dense(self.num_classes, activation='softmax')
        ])
        
        model.compile(
            optimizer='adam',
            loss='categorical_crossentropy',
            metrics=['accuracy']
        )
        
        return model
    
    def extract_features(self, image_patch: np.ndarray) -> np.ndarray:
        """Extract features for traditional ML classification"""
        try:
            features = []
            
            # Convert to appropriate format
            if len(image_patch.shape) == 3 and image_patch.shape[0] <= 5:
                # Channel first to channel last
                image_patch = np.transpose(image_patch, (1, 2, 0))
            
            # Statistical features for each band
            for i in range(image_patch.shape[2]):
                band = image_patch[:, :, i]
                features.extend([
                    np.mean(band),
                    np.std(band),
                    np.median(band),
                    np.percentile(band, 25),
                    np.percentile(band, 75),
                    np.min(band),
                    np.max(band)
                ])
            
            # Texture features using Local Binary Pattern
            if image_patch.shape[2] >= 3:
                gray = np.mean(image_patch[:, :, :3], axis=2)
                lbp = local_binary_pattern(gray, 24, 8, method='uniform')
                lbp_hist, _ = np.histogram(lbp.ravel(), bins=26, range=(0, 26))
                features.extend(lbp_hist / np.sum(lbp_hist))  # Normalize
            
            # Edge features
            if image_patch.shape[2] >= 3:
                gray = np.mean(image_patch[:, :, :3], axis=2)
                edges = filters.sobel(gray)
                features.extend([
                    np.mean(edges),
                    np.std(edges),
                    np.sum(edges > 0.1) / edges.size  # Edge density
                ])
            
            return np.array(features)
            
        except Exception as e:
            logger.error(f"Error extracting features: {e}")
            return np.array([])
    
    def classify_patch_cnn(self, image_patch: np.ndarray) -> Dict[str, Any]:
        """Classify image patch using CNN"""
        try:
            # Prepare input
            if len(image_patch.shape) == 3 and image_patch.shape[0] <= 5:
                # Channel first to channel last
                input_patch = np.transpose(image_patch, (1, 2, 0))
            else:
                input_patch = image_patch
            
            # Resize if needed
            if input_patch.shape[:2] != (256, 256):
                input_patch = cv2.resize(input_patch, (256, 256))
            
            # Ensure 5 channels (RGB + NDVI + NDWI)
            if input_patch.shape[2] < 5:
                # Pad with zeros if missing channels
                padding = np.zeros((256, 256, 5 - input_patch.shape[2]))
                input_patch = np.concatenate([input_patch, padding], axis=2)
            elif input_patch.shape[2] > 5:
                input_patch = input_patch[:, :, :5]
            
            # Add batch dimension
            input_batch = np.expand_dims(input_patch, axis=0)
            
            # Predict
            predictions = self.cnn_model.predict(input_batch, verbose=0)
            probabilities = predictions[0]
            
            # Get predicted class
            predicted_class_idx = np.argmax(probabilities)
            predicted_class = self.class_names[predicted_class_idx]
            confidence = probabilities[predicted_class_idx]
            
            return {
                'predicted_class': predicted_class,
                'confidence': float(confidence),
                'probabilities': {
                    class_name: float(prob) 
                    for class_name, prob in zip(self.class_names, probabilities)
                }
            }
            
        except Exception as e:
            logger.error(f"Error in CNN classification: {e}")
            return {
                'predicted_class': 'unknown',
                'confidence': 0.0,
                'probabilities': {}
            }
    
    def classify_patch_rf(self, image_patch: np.ndarray) -> Dict[str, Any]:
        """Classify image patch using Random Forest"""
        try:
            # Extract features
            features = self.extract_features(image_patch)
            
            if len(features) == 0:
                return {
                    'predicted_class': 'unknown',
                    'confidence': 0.0,
                    'probabilities': {}
                }
            
            # Predict
            features_reshaped = features.reshape(1, -1)
            prediction = self.rf_model.predict(features_reshaped)[0]
            probabilities = self.rf_model.predict_proba(features_reshaped)[0]
            
            # Get predicted class name
            predicted_class = self.class_names[prediction]
            confidence = probabilities[prediction]
            
            return {
                'predicted_class': predicted_class,
                'confidence': float(confidence),
                'probabilities': {
                    class_name: float(prob) 
                    for class_name, prob in zip(self.class_names, probabilities)
                }
            }
            
        except Exception as e:
            logger.error(f"Error in RF classification: {e}")
            return {
                'predicted_class': 'unknown',
                'confidence': 0.0,
                'probabilities': {}
            }
    
    def ensemble_classify(self, image_patch: np.ndarray) -> Dict[str, Any]:
        """Ensemble classification using both CNN and RF"""
        try:
            cnn_result = self.classify_patch_cnn(image_patch)
            rf_result = self.classify_patch_rf(image_patch)
            
            # Weighted ensemble (CNN gets higher weight)
            cnn_weight = 0.7
            rf_weight = 0.3
            
            # Combine probabilities
            combined_probs = {}
            for class_name in self.class_names:
                cnn_prob = cnn_result['probabilities'].get(class_name, 0.0)
                rf_prob = rf_result['probabilities'].get(class_name, 0.0)
                combined_probs[class_name] = (cnn_weight * cnn_prob + rf_weight * rf_prob)
            
            # Get final prediction
            predicted_class = max(combined_probs, key=combined_probs.get)
            confidence = combined_probs[predicted_class]
            
            return {
                'predicted_class': predicted_class,
                'confidence': float(confidence),
                'probabilities': combined_probs,
                'individual_results': {
                    'cnn': cnn_result,
                    'rf': rf_result
                }
            }
            
        except Exception as e:
            logger.error(f"Error in ensemble classification: {e}")
            return {
                'predicted_class': 'unknown',
                'confidence': 0.0,
                'probabilities': {}
            }

class AssetDetector:
    """Detect community assets from satellite imagery using computer vision"""
    
    def __init__(self):
        self.asset_classes = settings.ASSET_CLASSES
        self.detection_model = None
        self.initialize_detector()
    
    def initialize_detector(self):
        """Initialize asset detection model"""
        try:
            # In a real implementation, this would load a trained object detection model
            # For now, we'll use traditional computer vision techniques
            logger.info("Asset detector initialized")
        except Exception as e:
            logger.error(f"Error initializing asset detector: {e}")
            raise
    
    def detect_houses(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """Detect houses/buildings in satellite image"""
        try:
            detections = []
            
            # Convert to grayscale if needed
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
            else:
                gray = image
            
            # Apply Gaussian blur
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            
            # Edge detection
            edges = cv2.Canny(blurred, 50, 150)
            
            # Morphological operations to close gaps
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
            closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
            
            # Find contours
            contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                # Filter by area
                area = cv2.contourArea(contour)
                if 100 < area < 5000:  # Reasonable size for houses
                    # Get bounding rectangle
                    x, y, w, h = cv2.boundingRect(contour)
                    
                    # Check aspect ratio (houses are usually rectangular)
                    aspect_ratio = w / h
                    if 0.5 < aspect_ratio < 3.0:
                        # Calculate confidence based on shape regularity
                        hull = cv2.convexHull(contour)
                        hull_area = cv2.contourArea(hull)
                        solidity = area / hull_area if hull_area > 0 else 0
                        
                        if solidity > 0.6:  # Reasonably solid shape
                            detections.append({
                                'asset_type': 'house',
                                'bbox': [x, y, w, h],
                                'center': [x + w//2, y + h//2],
                                'area': area,
                                'confidence': min(solidity, 0.9)
                            })
            
            return detections
            
        except Exception as e:
            logger.error(f"Error detecting houses: {e}")
            return []
    
    def detect_water_bodies(self, image: np.ndarray, ndwi: np.ndarray = None) -> List[Dict[str, Any]]:
        """Detect water bodies using NDWI and morphological operations"""
        try:
            detections = []
            
            if ndwi is not None:
                # Use NDWI for water detection
                water_mask = ndwi > 0.3  # Threshold for water
            else:
                # Use blue channel intensity
                if len(image.shape) == 3:
                    blue_channel = image[:, :, 2] if image.shape[2] >= 3 else image[:, :, 0]
                else:
                    blue_channel = image
                
                # Normalize and threshold
                normalized = (blue_channel - blue_channel.min()) / (blue_channel.max() - blue_channel.min())
                water_mask = normalized > 0.6
            
            # Morphological operations to clean up
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            water_mask = cv2.morphologyEx(water_mask.astype(np.uint8), cv2.MORPH_CLOSE, kernel)
            water_mask = cv2.morphologyEx(water_mask, cv2.MORPH_OPEN, kernel)
            
            # Find connected components
            labeled_mask, num_labels = ndimage.label(water_mask)
            
            for i in range(1, num_labels + 1):
                component = (labeled_mask == i)
                area = np.sum(component)
                
                if area > 50:  # Minimum area for water body
                    # Get bounding box
                    coords = np.where(component)
                    y_min, y_max = coords[0].min(), coords[0].max()
                    x_min, x_max = coords[1].min(), coords[1].max()
                    
                    # Calculate center
                    center_y = int(np.mean(coords[0]))
                    center_x = int(np.mean(coords[1]))
                    
                    detections.append({
                        'asset_type': 'water_body',
                        'bbox': [x_min, y_min, x_max - x_min, y_max - y_min],
                        'center': [center_x, center_y],
                        'area': area,
                        'confidence': min(0.8, area / 1000)  # Higher confidence for larger bodies
                    })
            
            return detections
            
        except Exception as e:
            logger.error(f"Error detecting water bodies: {e}")
            return []
    
    def detect_agricultural_fields(self, image: np.ndarray, ndvi: np.ndarray = None) -> List[Dict[str, Any]]:
        """Detect agricultural fields using NDVI and texture analysis"""
        try:
            detections = []
            
            if ndvi is not None:
                # Use NDVI for vegetation detection
                vegetation_mask = (ndvi > 0.2) & (ndvi < 0.8)  # Agricultural vegetation range
            else:
                # Use green channel
                if len(image.shape) == 3:
                    green_channel = image[:, :, 1] if image.shape[2] >= 2 else image[:, :, 0]
                else:
                    green_channel = image
                
                normalized = (green_channel - green_channel.min()) / (green_channel.max() - green_channel.min())
                vegetation_mask = (normalized > 0.3) & (normalized < 0.8)
            
            # Apply morphological operations
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (10, 10))
            vegetation_mask = cv2.morphologyEx(vegetation_mask.astype(np.uint8), cv2.MORPH_CLOSE, kernel)
            
            # Find contours for field boundaries
            contours, _ = cv2.findContours(vegetation_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                area = cv2.contourArea(contour)
                if area > 500:  # Minimum area for agricultural field
                    # Get bounding rectangle
                    x, y, w, h = cv2.boundingRect(contour)
                    
                    # Check if it looks like a field (rectangular-ish)
                    rect_area = w * h
                    rectangularity = area / rect_area if rect_area > 0 else 0
                    
                    if rectangularity > 0.3:  # Reasonably rectangular
                        detections.append({
                            'asset_type': 'agricultural_field',
                            'bbox': [x, y, w, h],
                            'center': [x + w//2, y + h//2],
                            'area': area,
                            'confidence': min(rectangularity, 0.8)
                        })
            
            return detections
            
        except Exception as e:
            logger.error(f"Error detecting agricultural fields: {e}")
            return []
    
    def detect_all_assets(self, image: np.ndarray, ndvi: np.ndarray = None, ndwi: np.ndarray = None) -> List[Dict[str, Any]]:
        """Detect all types of assets in the image"""
        try:
            all_detections = []
            
            # Detect different asset types
            houses = self.detect_houses(image)
            water_bodies = self.detect_water_bodies(image, ndwi)
            agricultural_fields = self.detect_agricultural_fields(image, ndvi)
            
            # Combine all detections
            all_detections.extend(houses)
            all_detections.extend(water_bodies)
            all_detections.extend(agricultural_fields)
            
            # Add detection timestamp and method
            for detection in all_detections:
                detection['detected_at'] = datetime.utcnow().isoformat()
                detection['detection_method'] = 'computer_vision'
            
            return all_detections
            
        except Exception as e:
            logger.error(f"Error detecting assets: {e}")
            return []

class SatelliteAnalyzer:
    """Main satellite imagery analysis orchestrator"""
    
    def __init__(self):
        self.image_processor = SatelliteImageProcessor()
        self.land_classifier = LandUseClassifier()
        self.asset_detector = AssetDetector()
    
    async def analyze_satellite_image(self, image_path: str, analysis_type: str = "full") -> Dict[str, Any]:
        """Perform complete analysis of satellite image"""
        try:
            # Load image
            image_data = self.image_processor.load_satellite_image(image_path)
            raw_image = image_data['data']
            metadata = image_data['metadata']
            
            # Preprocess
            processed_image = self.image_processor.preprocess_for_classification(raw_image)
            
            # Create patches for analysis
            patches = self.image_processor.create_image_patches(processed_image)
            
            results = {
                'image_path': image_path,
                'metadata': metadata,
                'analysis_timestamp': datetime.utcnow().isoformat(),
                'patch_count': len(patches),
                'analysis_type': analysis_type
            }
            
            if analysis_type in ["full", "classification"]:
                # Land use classification
                classification_results = []
                for i, patch in enumerate(patches):
                    patch_result = self.land_classifier.ensemble_classify(patch)
                    patch_result['patch_id'] = i
                    classification_results.append(patch_result)
                
                results['land_use_classification'] = classification_results
            
            if analysis_type in ["full", "assets"]:
                # Asset detection
                asset_results = []
                
                # For asset detection, work with full image or larger patches
                if len(processed_image.shape) == 3:
                    # Get RGB representation
                    rgb_image = processed_image[:3].transpose(1, 2, 0)
                    ndvi = processed_image[3] if processed_image.shape[0] > 3 else None
                    ndwi = processed_image[4] if processed_image.shape[0] > 4 else None
                else:
                    rgb_image = processed_image
                    ndvi = None
                    ndwi = None
                
                assets = self.asset_detector.detect_all_assets(rgb_image, ndvi, ndwi)
                results['community_assets'] = assets
            
            # Calculate summary statistics
            if 'land_use_classification' in results:
                results['land_use_summary'] = self._calculate_land_use_summary(results['land_use_classification'])
            
            if 'community_assets' in results:
                results['asset_summary'] = self._calculate_asset_summary(results['community_assets'])
            
            return results
            
        except Exception as e:
            logger.error(f"Error analyzing satellite image {image_path}: {e}")
            return {
                'image_path': image_path,
                'error': str(e),
                'analysis_timestamp': datetime.utcnow().isoformat(),
                'status': 'failed'
            }
    
    def _calculate_land_use_summary(self, classification_results: List[Dict]) -> Dict[str, Any]:
        """Calculate summary statistics for land use classification"""
        try:
            class_counts = {}
            total_patches = len(classification_results)
            confidence_sum = 0
            
            for result in classification_results:
                predicted_class = result.get('predicted_class', 'unknown')
                confidence = result.get('confidence', 0.0)
                
                class_counts[predicted_class] = class_counts.get(predicted_class, 0) + 1
                confidence_sum += confidence
            
            # Calculate percentages
            class_percentages = {
                class_name: (count / total_patches) * 100
                for class_name, count in class_counts.items()
            }
            
            avg_confidence = confidence_sum / total_patches if total_patches > 0 else 0.0
            
            return {
                'class_counts': class_counts,
                'class_percentages': class_percentages,
                'total_patches': total_patches,
                'average_confidence': avg_confidence,
                'dominant_class': max(class_counts, key=class_counts.get) if class_counts else 'unknown'
            }
            
        except Exception as e:
            logger.error(f"Error calculating land use summary: {e}")
            return {}
    
    def _calculate_asset_summary(self, assets: List[Dict]) -> Dict[str, Any]:
        """Calculate summary statistics for detected assets"""
        try:
            asset_counts = {}
            total_area = 0
            confidence_sum = 0
            
            for asset in assets:
                asset_type = asset.get('asset_type', 'unknown')
                area = asset.get('area', 0)
                confidence = asset.get('confidence', 0.0)
                
                asset_counts[asset_type] = asset_counts.get(asset_type, 0) + 1
                total_area += area
                confidence_sum += confidence
            
            total_assets = len(assets)
            avg_confidence = confidence_sum / total_assets if total_assets > 0 else 0.0
            
            return {
                'asset_counts': asset_counts,
                'total_assets': total_assets,
                'total_area': total_area,
                'average_confidence': avg_confidence
            }
            
        except Exception as e:
            logger.error(f"Error calculating asset summary: {e}")
            return {}
    
    async def batch_analyze_images(self, image_paths: List[str], analysis_type: str = "full") -> List[Dict[str, Any]]:
        """Analyze multiple satellite images in batch"""
        tasks = [self.analyze_satellite_image(path, analysis_type) for path in image_paths]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    'image_path': image_paths[i],
                    'error': str(result),
                    'status': 'failed',
                    'analysis_timestamp': datetime.utcnow().isoformat()
                })
            else:
                processed_results.append(result)
        
        return processed_results