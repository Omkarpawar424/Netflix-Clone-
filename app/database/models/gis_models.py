"""
GIS and geospatial database models
"""

from sqlalchemy import String, DateTime, Boolean, Integer, Float, Text, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from geoalchemy2 import Geometry
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any

from app.core.database import Base

class LayerType(str, Enum):
    """GIS layer types"""
    VECTOR = "vector"
    RASTER = "raster"
    TILE = "tile"
    WMS = "wms"
    WFS = "wfs"

class DataSource(str, Enum):
    """Data source types"""
    SATELLITE = "satellite"
    SURVEY = "survey"
    GOVERNMENT = "government"
    COMMUNITY = "community"
    FIELD_COLLECTION = "field_collection"
    THIRD_PARTY = "third_party"

class LandUseClass(str, Enum):
    """Land use classification"""
    FOREST = "forest"
    AGRICULTURAL_LAND = "agricultural_land"
    WATER_BODY = "water_body"
    BUILT_UP_AREA = "built_up_area"
    BARREN_LAND = "barren_land"
    GRASSLAND = "grassland"
    WETLAND = "wetland"
    SCRUBLAND = "scrubland"
    PLANTATION = "plantation"

class GISLayer(Base):
    """GIS layer definitions"""
    
    __tablename__ = "gis_layers"
    
    # Basic Information
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    
    # Layer Configuration
    layer_type: Mapped[LayerType] = mapped_column(String(20), nullable=False)
    data_source: Mapped[DataSource] = mapped_column(String(30), nullable=False)
    source_url: Mapped[Optional[str]] = mapped_column(String(500))
    
    # Spatial Information
    geometry_type: Mapped[Optional[str]] = mapped_column(String(50))  # POINT, LINESTRING, POLYGON, etc.
    srid: Mapped[int] = mapped_column(Integer, default=4326)
    bounding_box: Mapped[Optional[str]] = mapped_column(Geometry('POLYGON', srid=4326))
    
    # Data Information
    table_name: Mapped[Optional[str]] = mapped_column(String(100))
    primary_key_field: Mapped[Optional[str]] = mapped_column(String(50))
    geometry_field: Mapped[str] = mapped_column(String(50), default="geom")
    
    # Display Properties
    default_style: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    min_zoom: Mapped[Optional[int]] = mapped_column(Integer)
    max_zoom: Mapped[Optional[int]] = mapped_column(Integer)
    opacity: Mapped[float] = mapped_column(Float, default=1.0)
    
    # Access Control
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    allowed_roles: Mapped[Optional[List[str]]] = mapped_column(JSON)
    
    # Metadata
    data_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    resolution: Mapped[Optional[str]] = mapped_column(String(50))
    accuracy: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Status
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    processing_status: Mapped[str] = mapped_column(String(50), default="ready")
    
    # Relationships
    features: Mapped[List["GISFeature"]] = relationship("GISFeature", back_populates="layer")

class GISFeature(Base):
    """Individual GIS features/geometries"""
    
    __tablename__ = "gis_features"
    
    layer_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("gis_layers.id"), nullable=False)
    
    # Geometry
    geometry: Mapped[str] = mapped_column(Geometry(srid=4326), nullable=False)
    
    # Properties
    properties: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    
    # Identification
    feature_id: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    name: Mapped[Optional[str]] = mapped_column(String(200))
    
    # Location Context
    state: Mapped[Optional[str]] = mapped_column(String(50))
    district: Mapped[Optional[str]] = mapped_column(String(100))
    block: Mapped[Optional[str]] = mapped_column(String(100))
    village: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Data Quality
    confidence_score: Mapped[Optional[float]] = mapped_column(Float)
    data_source: Mapped[Optional[str]] = mapped_column(String(100))
    collection_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Relationships
    layer: Mapped["GISLayer"] = relationship("GISLayer", back_populates="features")

class SatelliteImage(Base):
    """Satellite imagery metadata"""
    
    __tablename__ = "satellite_images"
    
    # Image Information
    image_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    satellite_name: Mapped[str] = mapped_column(String(50), nullable=False)
    sensor: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Spatial Information
    footprint: Mapped[str] = mapped_column(Geometry('POLYGON', srid=4326), nullable=False)
    center_point: Mapped[str] = mapped_column(Geometry('POINT', srid=4326), nullable=False)
    
    # Temporal Information
    acquisition_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    processing_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Image Properties
    cloud_cover_percentage: Mapped[Optional[float]] = mapped_column(Float)
    resolution_meters: Mapped[float] = mapped_column(Float, nullable=False)
    bands: Mapped[List[str]] = mapped_column(JSON, nullable=False)
    
    # File Information
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size_mb: Mapped[Optional[float]] = mapped_column(Float)
    file_format: Mapped[str] = mapped_column(String(20), nullable=False)
    
    # Processing Status
    processing_level: Mapped[str] = mapped_column(String(20), nullable=False)  # L1, L2, L3, etc.
    quality_score: Mapped[Optional[float]] = mapped_column(Float)
    
    # Location Context
    states_covered: Mapped[List[str]] = mapped_column(JSON)
    districts_covered: Mapped[List[str]] = mapped_column(JSON)
    
    # Analysis Results
    land_use_analysis: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    change_detection_results: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    
    # Relationships
    land_use_classifications: Mapped[List["LandUseClassification"]] = relationship("LandUseClassification", back_populates="satellite_image")

class LandUseClassification(Base):
    """Land use classification results"""
    
    __tablename__ = "land_use_classifications"
    
    satellite_image_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("satellite_images.id"), nullable=False)
    
    # Classification Information
    classification_method: Mapped[str] = mapped_column(String(50), nullable=False)  # supervised, unsupervised, deep_learning
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    model_version: Mapped[str] = mapped_column(String(20), nullable=False)
    
    # Geometry and Classification
    geometry: Mapped[str] = mapped_column(Geometry('POLYGON', srid=4326), nullable=False)
    land_use_class: Mapped[LandUseClass] = mapped_column(String(50), nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    
    # Area Information
    area_hectares: Mapped[float] = mapped_column(Float, nullable=False)
    area_percentage: Mapped[Optional[float]] = mapped_column(Float)
    
    # Processing Information
    processed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    processing_time_seconds: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Location Context
    state: Mapped[Optional[str]] = mapped_column(String(50))
    district: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Quality Metrics
    accuracy_metrics: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    
    # Relationships
    satellite_image: Mapped["SatelliteImage"] = relationship("SatelliteImage", back_populates="land_use_classifications")

class CommunityAsset(Base):
    """Community assets identified through AI analysis"""
    
    __tablename__ = "community_assets"
    
    # Basic Information
    asset_name: Mapped[str] = mapped_column(String(200), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(50), nullable=False)  # house, well, pond, temple, school, etc.
    description: Mapped[Optional[str]] = mapped_column(Text)
    
    # Location
    geometry: Mapped[str] = mapped_column(Geometry('POINT', srid=4326), nullable=False)
    state: Mapped[str] = mapped_column(String(50), nullable=False)
    district: Mapped[str] = mapped_column(String(100), nullable=False)
    block: Mapped[str] = mapped_column(String(100), nullable=False)
    village: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Detection Information
    detection_method: Mapped[str] = mapped_column(String(50), nullable=False)  # satellite_analysis, field_survey, community_mapping
    detection_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Asset Properties
    estimated_area_sqm: Mapped[Optional[float]] = mapped_column(Float)
    construction_material: Mapped[Optional[str]] = mapped_column(String(100))
    condition_assessment: Mapped[Optional[str]] = mapped_column(String(50))  # good, fair, poor
    
    # Ownership and Usage
    ownership_type: Mapped[Optional[str]] = mapped_column(String(50))  # individual, community, government
    usage_pattern: Mapped[Optional[str]] = mapped_column(String(100))
    beneficiaries_count: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Verification Status
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verified_by: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    verification_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    verification_notes: Mapped[Optional[str]] = mapped_column(Text)
    
    # Associated Claims
    related_fra_claims: Mapped[Optional[List[str]]] = mapped_column(JSON)
    
    # Images and Documentation
    images: Mapped[Optional[List[str]]] = mapped_column(JSON)  # File paths
    documents: Mapped[Optional[List[str]]] = mapped_column(JSON)  # File paths

class VillageBoundary(Base):
    """Village administrative boundaries"""
    
    __tablename__ = "village_boundaries"
    
    # Administrative Information
    village_name: Mapped[str] = mapped_column(String(100), nullable=False)
    village_code: Mapped[Optional[str]] = mapped_column(String(20), unique=True)
    block_name: Mapped[str] = mapped_column(String(100), nullable=False)
    district_name: Mapped[str] = mapped_column(String(100), nullable=False)
    state_name: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Geographic Information
    boundary: Mapped[str] = mapped_column(Geometry('POLYGON', srid=4326), nullable=False)
    centroid: Mapped[str] = mapped_column(Geometry('POINT', srid=4326), nullable=False)
    area_hectares: Mapped[float] = mapped_column(Float, nullable=False)
    perimeter_km: Mapped[Optional[float]] = mapped_column(Float)
    
    # Demographics
    population: Mapped[Optional[int]] = mapped_column(Integer)
    households: Mapped[Optional[int]] = mapped_column(Integer)
    tribal_population: Mapped[Optional[int]] = mapped_column(Integer)
    tribal_households: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Forest Rights Information
    total_fra_claims: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    approved_fra_claims: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    total_fra_area_hectares: Mapped[Optional[float]] = mapped_column(Float, default=0.0)
    
    # Land Use Statistics
    forest_area_hectares: Mapped[Optional[float]] = mapped_column(Float)
    agricultural_area_hectares: Mapped[Optional[float]] = mapped_column(Float)
    water_body_area_hectares: Mapped[Optional[float]] = mapped_column(Float)
    
    # Data Source
    data_source: Mapped[str] = mapped_column(String(100), nullable=False)
    survey_year: Mapped[Optional[int]] = mapped_column(Integer)
    last_updated: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class ChangeDetection(Base):
    """Land use change detection results"""
    
    __tablename__ = "change_detections"
    
    # Time Period
    start_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    
    # Location
    geometry: Mapped[str] = mapped_column(Geometry('POLYGON', srid=4326), nullable=False)
    state: Mapped[str] = mapped_column(String(50), nullable=False)
    district: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Change Information
    change_type: Mapped[str] = mapped_column(String(50), nullable=False)  # deforestation, afforestation, urbanization, etc.
    from_land_use: Mapped[str] = mapped_column(String(50), nullable=False)
    to_land_use: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Quantitative Data
    area_changed_hectares: Mapped[float] = mapped_column(Float, nullable=False)
    change_percentage: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    
    # Detection Method
    detection_method: Mapped[str] = mapped_column(String(100), nullable=False)
    algorithm_used: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Satellite Images Used
    before_image_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("satellite_images.id"), nullable=False)
    after_image_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("satellite_images.id"), nullable=False)
    
    # Analysis Results
    change_drivers: Mapped[Optional[List[str]]] = mapped_column(JSON)
    impact_assessment: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    recommendations: Mapped[Optional[str]] = mapped_column(Text)
    
    # Processing Information
    processed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    processing_time_seconds: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Verification
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verified_by: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    verification_notes: Mapped[Optional[str]] = mapped_column(Text)