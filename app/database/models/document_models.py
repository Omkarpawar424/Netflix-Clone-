"""
Document processing and FRA claim database models
"""

from sqlalchemy import String, DateTime, Boolean, Integer, Float, Text, JSON, ForeignKey, LargeBinary
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from geoalchemy2 import Geometry
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any

from app.core.database import Base

class DocumentType(str, Enum):
    """Document type enumeration"""
    FRA_CLAIM = "fra_claim"
    TITLE_DEED = "title_deed"
    SURVEY_SETTLEMENT = "survey_settlement"
    REVENUE_RECORD = "revenue_record"
    IDENTITY_PROOF = "identity_proof"
    COMMUNITY_CERTIFICATE = "community_certificate"
    FOREST_CLEARANCE = "forest_clearance"
    OTHER = "other"

class DocumentStatus(str, Enum):
    """Document processing status"""
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    VERIFIED = "verified"
    REJECTED = "rejected"
    ARCHIVED = "archived"

class ClaimStatus(str, Enum):
    """FRA claim status"""
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    FIELD_VERIFICATION = "field_verification"
    COMMITTEE_REVIEW = "committee_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    TITLE_DISTRIBUTED = "title_distributed"

class Document(Base):
    """Document storage and metadata"""
    
    __tablename__ = "documents"
    
    # Basic Information
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Classification
    document_type: Mapped[DocumentType] = mapped_column(String(50), nullable=False)
    status: Mapped[DocumentStatus] = mapped_column(String(50), default=DocumentStatus.UPLOADED)
    
    # Processing Information
    ocr_text: Mapped[Optional[str]] = mapped_column(Text)
    extracted_entities: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float)
    processing_errors: Mapped[Optional[List[str]]] = mapped_column(JSON)
    
    # Metadata
    language: Mapped[Optional[str]] = mapped_column(String(10))
    page_count: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Location Information
    state: Mapped[Optional[str]] = mapped_column(String(50))
    district: Mapped[Optional[str]] = mapped_column(String(100))
    block: Mapped[Optional[str]] = mapped_column(String(100))
    village: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Audit
    uploaded_by: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    processed_by: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    verified_by: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    # Timestamps
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Relationships
    fra_claims: Mapped[List["FRAClaim"]] = relationship("FRAClaim", back_populates="documents")
    
    def __repr__(self):
        return f"<Document(filename='{self.filename}', type='{self.document_type}', status='{self.status}')>"

class FRAClaim(Base):
    """Forest Rights Act claims"""
    
    __tablename__ = "fra_claims"
    
    # Claim Information
    claim_number: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    claim_type: Mapped[str] = mapped_column(String(50), nullable=False)  # individual, community, community_forest_resource
    status: Mapped[ClaimStatus] = mapped_column(String(50), default=ClaimStatus.SUBMITTED)
    
    # Claimant Information
    claimant_name: Mapped[str] = mapped_column(String(200), nullable=False)
    father_husband_name: Mapped[Optional[str]] = mapped_column(String(200))
    caste_tribe: Mapped[Optional[str]] = mapped_column(String(100))
    family_members: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Contact Information
    address: Mapped[Optional[str]] = mapped_column(Text)
    phone_number: Mapped[Optional[str]] = mapped_column(String(15))
    
    # Location Details
    state: Mapped[str] = mapped_column(String(50), nullable=False)
    district: Mapped[str] = mapped_column(String(100), nullable=False)
    block: Mapped[str] = mapped_column(String(100), nullable=False)
    village: Mapped[str] = mapped_column(String(100), nullable=False)
    forest_division: Mapped[Optional[str]] = mapped_column(String(100))
    forest_range: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Land Details
    survey_number: Mapped[Optional[str]] = mapped_column(String(50))
    area_claimed_hectares: Mapped[Optional[float]] = mapped_column(Float)
    area_verified_hectares: Mapped[Optional[float]] = mapped_column(Float)
    area_approved_hectares: Mapped[Optional[float]] = mapped_column(Float)
    
    # Geographic Information
    boundary_coordinates: Mapped[Optional[str]] = mapped_column(Geometry('POLYGON', srid=4326))
    centroid: Mapped[Optional[str]] = mapped_column(Geometry('POINT', srid=4326))
    
    # Processing Information
    submission_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    verification_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    approval_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    title_distribution_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Committee Information
    gram_sabha_resolution_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    sdlc_recommendation: Mapped[Optional[str]] = mapped_column(Text)
    dlc_decision: Mapped[Optional[str]] = mapped_column(Text)
    
    # Additional Information
    livelihood_activities: Mapped[Optional[List[str]]] = mapped_column(JSON)
    community_assets: Mapped[Optional[List[str]]] = mapped_column(JSON)
    remarks: Mapped[Optional[str]] = mapped_column(Text)
    
    # References
    title_number: Mapped[Optional[str]] = mapped_column(String(50), unique=True)
    patatta_number: Mapped[Optional[str]] = mapped_column(String(50))
    
    # Relationships
    documents: Mapped[List["Document"]] = relationship("Document", back_populates="fra_claims")
    field_verifications: Mapped[List["FieldVerification"]] = relationship("FieldVerification", back_populates="fra_claim")
    
    def __repr__(self):
        return f"<FRAClaim(claim_number='{self.claim_number}', claimant='{self.claimant_name}', status='{self.status}')>"

class FieldVerification(Base):
    """Field verification records"""
    
    __tablename__ = "field_verifications"
    
    fra_claim_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("fra_claims.id"), nullable=False)
    
    # Verification Details
    verification_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    verified_by: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    verification_method: Mapped[str] = mapped_column(String(50), nullable=False)  # physical, satellite, drone
    
    # GPS Coordinates
    gps_coordinates: Mapped[Optional[str]] = mapped_column(Geometry('MULTIPOINT', srid=4326))
    boundary_marked: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Measurements
    measured_area_hectares: Mapped[Optional[float]] = mapped_column(Float)
    discrepancy_area_hectares: Mapped[Optional[float]] = mapped_column(Float)
    
    # Observations
    land_use_observed: Mapped[Optional[str]] = mapped_column(String(100))
    vegetation_type: Mapped[Optional[str]] = mapped_column(String(100))
    soil_type: Mapped[Optional[str]] = mapped_column(String(100))
    water_sources: Mapped[Optional[List[str]]] = mapped_column(JSON)
    
    # Assets Found
    structures_found: Mapped[Optional[List[str]]] = mapped_column(JSON)
    crops_found: Mapped[Optional[List[str]]] = mapped_column(JSON)
    trees_found: Mapped[Optional[List[str]]] = mapped_column(JSON)
    
    # Verification Result
    verification_result: Mapped[str] = mapped_column(String(50), nullable=False)  # verified, partially_verified, not_verified
    remarks: Mapped[Optional[str]] = mapped_column(Text)
    recommendations: Mapped[Optional[str]] = mapped_column(Text)
    
    # Evidence
    photos: Mapped[Optional[List[str]]] = mapped_column(JSON)  # File paths
    videos: Mapped[Optional[List[str]]] = mapped_column(JSON)  # File paths
    documents: Mapped[Optional[List[str]]] = mapped_column(JSON)  # File paths
    
    # Weather and Conditions
    weather_conditions: Mapped[Optional[str]] = mapped_column(String(100))
    visibility: Mapped[Optional[str]] = mapped_column(String(50))
    
    # Team Information
    verification_team: Mapped[Optional[List[str]]] = mapped_column(JSON)  # Team member names/IDs
    local_witnesses: Mapped[Optional[List[str]]] = mapped_column(JSON)  # Witness names
    
    # Relationships
    fra_claim: Mapped["FRAClaim"] = relationship("FRAClaim", back_populates="field_verifications")

class DocumentTemplate(Base):
    """Templates for document generation"""
    
    __tablename__ = "document_templates"
    
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    template_type: Mapped[str] = mapped_column(String(50), nullable=False)  # title_deed, certificate, notice
    language: Mapped[str] = mapped_column(String(10), nullable=False)
    state: Mapped[Optional[str]] = mapped_column(String(50))
    
    # Template Content
    template_content: Mapped[str] = mapped_column(Text, nullable=False)
    template_variables: Mapped[List[str]] = mapped_column(JSON, nullable=False)
    
    # Formatting
    page_size: Mapped[str] = mapped_column(String(20), default="A4")
    orientation: Mapped[str] = mapped_column(String(20), default="portrait")
    
    # Status
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    version: Mapped[str] = mapped_column(String(10), default="1.0")

class ProcessingQueue(Base):
    """Queue for document processing jobs"""
    
    __tablename__ = "processing_queue"
    
    document_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
    
    # Job Information
    job_type: Mapped[str] = mapped_column(String(50), nullable=False)  # ocr, ner, classification
    priority: Mapped[int] = mapped_column(Integer, default=5)  # 1=highest, 10=lowest
    status: Mapped[str] = mapped_column(String(50), default="pending")  # pending, processing, completed, failed
    
    # Processing Details
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    processing_time_seconds: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Results
    result_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Worker Information
    worker_id: Mapped[Optional[str]] = mapped_column(String(100))
    worker_hostname: Mapped[Optional[str]] = mapped_column(String(100))