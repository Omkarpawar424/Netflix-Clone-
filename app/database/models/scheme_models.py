"""
Government scheme integration and recommendation database models
"""

from sqlalchemy import String, DateTime, Boolean, Integer, Float, Text, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any

from app.core.database import Base

class SchemeType(str, Enum):
    """Government scheme types"""
    CENTRAL_SECTOR = "central_sector"
    CENTRALLY_SPONSORED = "centrally_sponsored"
    STATE_SCHEME = "state_scheme"
    DISTRICT_SCHEME = "district_scheme"

class EligibilityStatus(str, Enum):
    """Eligibility assessment status"""
    ELIGIBLE = "eligible"
    NOT_ELIGIBLE = "not_eligible"
    CONDITIONALLY_ELIGIBLE = "conditionally_eligible"
    UNDER_REVIEW = "under_review"

class ApplicationStatus(str, Enum):
    """Scheme application status"""
    NOT_APPLIED = "not_applied"
    APPLIED = "applied"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    DISBURSED = "disbursed"
    COMPLETED = "completed"

class GovernmentScheme(Base):
    """Government schemes and programs"""
    
    __tablename__ = "government_schemes"
    
    # Basic Information
    scheme_name: Mapped[str] = mapped_column(String(200), nullable=False)
    scheme_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    scheme_type: Mapped[SchemeType] = mapped_column(String(30), nullable=False)
    
    # Description
    description: Mapped[str] = mapped_column(Text, nullable=False)
    objectives: Mapped[List[str]] = mapped_column(JSON, nullable=False)
    key_features: Mapped[List[str]] = mapped_column(JSON, nullable=False)
    
    # Administrative Details
    implementing_ministry: Mapped[str] = mapped_column(String(200), nullable=False)
    implementing_agency: Mapped[Optional[str]] = mapped_column(String(200))
    nodal_department: Mapped[Optional[str]] = mapped_column(String(200))
    
    # Geographical Coverage
    coverage_type: Mapped[str] = mapped_column(String(20), nullable=False)  # national, state_specific, district_specific
    covered_states: Mapped[Optional[List[str]]] = mapped_column(JSON)
    covered_districts: Mapped[Optional[List[str]]] = mapped_column(JSON)
    
    # Eligibility Criteria
    eligibility_criteria: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    target_beneficiaries: Mapped[List[str]] = mapped_column(JSON, nullable=False)
    income_criteria: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    
    # Financial Information
    budget_allocation: Mapped[Optional[float]] = mapped_column(Float)
    benefit_amount: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    funding_pattern: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)  # Central:State ratio
    
    # Timeline
    launch_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    application_deadline: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Application Process
    application_process: Mapped[List[str]] = mapped_column(JSON, nullable=False)
    required_documents: Mapped[List[str]] = mapped_column(JSON, nullable=False)
    application_channels: Mapped[List[str]] = mapped_column(JSON, nullable=False)  # online, offline, csc
    
    # Contact Information
    helpline_number: Mapped[Optional[str]] = mapped_column(String(20))
    website_url: Mapped[Optional[str]] = mapped_column(String(500))
    email_contact: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_updated: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    eligibility_assessments: Mapped[List["SchemeEligibilityAssessment"]] = relationship(
        "SchemeEligibilityAssessment", back_populates="scheme"
    )
    applications: Mapped[List["SchemeApplication"]] = relationship(
        "SchemeApplication", back_populates="scheme"
    )

class FRAHolderProfile(Base):
    """FRA holder profiles for scheme eligibility assessment"""
    
    __tablename__ = "fra_holder_profiles"
    
    # Basic Information
    holder_name: Mapped[str] = mapped_column(String(200), nullable=False)
    father_husband_name: Mapped[Optional[str]] = mapped_column(String(200))
    date_of_birth: Mapped[Optional[datetime]] = mapped_column(DateTime)
    gender: Mapped[Optional[str]] = mapped_column(String(10))
    
    # Identity Information
    aadhar_number: Mapped[Optional[str]] = mapped_column(String(12))
    voter_id: Mapped[Optional[str]] = mapped_column(String(20))
    ration_card_number: Mapped[Optional[str]] = mapped_column(String(20))
    
    # Contact Information
    phone_number: Mapped[Optional[str]] = mapped_column(String(15))
    email: Mapped[Optional[str]] = mapped_column(String(100))
    address: Mapped[Optional[str]] = mapped_column(Text)
    
    # Location
    state: Mapped[str] = mapped_column(String(50), nullable=False)
    district: Mapped[str] = mapped_column(String(100), nullable=False)
    block: Mapped[str] = mapped_column(String(100), nullable=False)
    village: Mapped[str] = mapped_column(String(100), nullable=False)
    pincode: Mapped[Optional[str]] = mapped_column(String(6))
    
    # Social Information
    caste_category: Mapped[Optional[str]] = mapped_column(String(50))
    tribe_name: Mapped[Optional[str]] = mapped_column(String(100))
    is_tribal: Mapped[bool] = mapped_column(Boolean, default=False)
    religion: Mapped[Optional[str]] = mapped_column(String(50))
    
    # Family Information
    family_size: Mapped[Optional[int]] = mapped_column(Integer)
    male_members: Mapped[Optional[int]] = mapped_column(Integer)
    female_members: Mapped[Optional[int]] = mapped_column(Integer)
    children_count: Mapped[Optional[int]] = mapped_column(Integer)
    elderly_members: Mapped[Optional[int]] = mapped_column(Integer)
    disabled_members: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Economic Information
    occupation: Mapped[Optional[str]] = mapped_column(String(100))
    annual_income: Mapped[Optional[float]] = mapped_column(Float)
    income_sources: Mapped[Optional[List[str]]] = mapped_column(JSON)
    bpl_status: Mapped[Optional[bool]] = mapped_column(Boolean)
    
    # Land and Assets
    landholding_hectares: Mapped[Optional[float]] = mapped_column(Float)
    land_type: Mapped[Optional[str]] = mapped_column(String(50))
    irrigation_facility: Mapped[Optional[bool]] = mapped_column(Boolean)
    livestock_count: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Housing Information
    housing_type: Mapped[Optional[str]] = mapped_column(String(50))  # pucca, semi_pucca, kutcha, homeless
    house_ownership: Mapped[Optional[str]] = mapped_column(String(50))
    electricity_connection: Mapped[Optional[bool]] = mapped_column(Boolean)
    water_source: Mapped[Optional[str]] = mapped_column(String(50))
    toilet_facility: Mapped[Optional[bool]] = mapped_column(Boolean)
    
    # Financial Inclusion
    bank_account: Mapped[Optional[bool]] = mapped_column(Boolean)
    bank_name: Mapped[Optional[str]] = mapped_column(String(100))
    account_number: Mapped[Optional[str]] = mapped_column(String(20))
    ifsc_code: Mapped[Optional[str]] = mapped_column(String(11))
    
    # FRA Information
    fra_claim_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=True), ForeignKey("fra_claims.id"))
    title_holder: Mapped[Optional[bool]] = mapped_column(Boolean)
    title_area_hectares: Mapped[Optional[float]] = mapped_column(Float)
    
    # Additional Information
    additional_details: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    
    # Data Source and Quality
    data_source: Mapped[str] = mapped_column(String(100), default="manual_entry")
    data_quality_score: Mapped[Optional[float]] = mapped_column(Float)
    last_verified: Mapped[Optional[datetime]] = mapped_column(DateTime)
    verified_by: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    # Relationships
    eligibility_assessments: Mapped[List["SchemeEligibilityAssessment"]] = relationship(
        "SchemeEligibilityAssessment", back_populates="fra_holder"
    )
    applications: Mapped[List["SchemeApplication"]] = relationship(
        "SchemeApplication", back_populates="fra_holder"
    )

class SchemeEligibilityAssessment(Base):
    """Scheme eligibility assessments for FRA holders"""
    
    __tablename__ = "scheme_eligibility_assessments"
    
    fra_holder_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("fra_holder_profiles.id"), nullable=False)
    scheme_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("government_schemes.id"), nullable=False)
    
    # Assessment Results
    eligibility_status: Mapped[EligibilityStatus] = mapped_column(String(30), nullable=False)
    eligibility_score: Mapped[float] = mapped_column(Float, nullable=False)  # 0-100
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)  # 0-1
    
    # Detailed Assessment
    criteria_evaluation: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    met_criteria: Mapped[List[str]] = mapped_column(JSON, nullable=False)
    unmet_criteria: Mapped[List[str]] = mapped_column(JSON, nullable=False)
    
    # Recommendations
    recommendation_priority: Mapped[str] = mapped_column(String(20), nullable=False)  # high, medium, low
    recommendation_reason: Mapped[str] = mapped_column(Text, nullable=False)
    next_steps: Mapped[List[str]] = mapped_column(JSON, nullable=False)
    estimated_benefit: Mapped[Optional[str]] = mapped_column(String(200))
    
    # Assessment Information
    assessment_method: Mapped[str] = mapped_column(String(50), default="ai_assisted")  # manual, ai_assisted, automated
    assessed_by: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    assessment_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Review and Validation
    reviewed_by: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    review_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    review_comments: Mapped[Optional[str]] = mapped_column(Text)
    
    # Conditional Eligibility
    conditions_to_meet: Mapped[Optional[List[str]]] = mapped_column(JSON)
    supporting_documents_needed: Mapped[Optional[List[str]]] = mapped_column(JSON)
    
    # Status Tracking
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Relationships
    fra_holder: Mapped["FRAHolderProfile"] = relationship(
        "FRAHolderProfile", back_populates="eligibility_assessments"
    )
    scheme: Mapped["GovernmentScheme"] = relationship(
        "GovernmentScheme", back_populates="eligibility_assessments"
    )

class SchemeApplication(Base):
    """Scheme applications submitted by FRA holders"""
    
    __tablename__ = "scheme_applications"
    
    fra_holder_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("fra_holder_profiles.id"), nullable=False)
    scheme_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("government_schemes.id"), nullable=False)
    
    # Application Information
    application_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    application_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    application_channel: Mapped[str] = mapped_column(String(50), nullable=False)  # online, offline, csc
    
    # Status Tracking
    status: Mapped[ApplicationStatus] = mapped_column(String(30), nullable=False, default=ApplicationStatus.APPLIED)
    status_updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    status_updated_by: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    # Application Data
    application_data: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    submitted_documents: Mapped[List[str]] = mapped_column(JSON, nullable=False)
    document_verification_status: Mapped[Optional[Dict[str, str]]] = mapped_column(JSON)
    
    # Processing Information
    assigned_officer: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    processing_office: Mapped[Optional[str]] = mapped_column(String(200))
    expected_processing_time: Mapped[Optional[int]] = mapped_column(Integer)  # Days
    
    # Decision Information
    decision_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    decision_maker: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    decision_remarks: Mapped[Optional[str]] = mapped_column(Text)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text)
    
    # Benefit Information
    approved_amount: Mapped[Optional[float]] = mapped_column(Float)
    disbursement_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    disbursement_method: Mapped[Optional[str]] = mapped_column(String(50))
    transaction_reference: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Communication
    notifications_sent: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    communication_preferences: Mapped[Optional[Dict[str, str]]] = mapped_column(JSON)
    
    # Quality and Compliance
    data_quality_score: Mapped[Optional[float]] = mapped_column(Float)
    compliance_check_status: Mapped[Optional[str]] = mapped_column(String(20))
    audit_trail: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    
    # Relationships
    fra_holder: Mapped["FRAHolderProfile"] = relationship(
        "FRAHolderProfile", back_populates="applications"
    )
    scheme: Mapped["GovernmentScheme"] = relationship(
        "GovernmentScheme", back_populates="applications"
    )

class SchemeRecommendation(Base):
    """AI-generated scheme recommendations"""
    
    __tablename__ = "scheme_recommendations"
    
    fra_holder_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("fra_holder_profiles.id"), nullable=False)
    
    # Recommendation Information
    recommendation_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    recommendation_method: Mapped[str] = mapped_column(String(50), default="ai_ml_model")
    model_version: Mapped[Optional[str]] = mapped_column(String(20))
    
    # Recommended Schemes
    recommended_schemes: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, nullable=False)
    priority_ranking: Mapped[List[str]] = mapped_column(JSON, nullable=False)  # Scheme IDs in priority order
    
    # Recommendation Context
    holder_profile_snapshot: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    recommendation_factors: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    
    # Quality Metrics
    overall_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    recommendation_quality_score: Mapped[Optional[float]] = mapped_column(Float)
    
    # User Interaction
    viewed_by_holder: Mapped[bool] = mapped_column(Boolean, default=False)
    viewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    feedback_rating: Mapped[Optional[int]] = mapped_column(Integer)  # 1-5 stars
    feedback_comments: Mapped[Optional[str]] = mapped_column(Text)
    
    # Follow-up Actions
    schemes_applied: Mapped[Optional[List[str]]] = mapped_column(JSON)
    application_success_rate: Mapped[Optional[float]] = mapped_column(Float)
    
    # Validity
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    superseded_by: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=True))

class SchemePerformanceMetric(Base):
    """Performance metrics for government schemes"""
    
    __tablename__ = "scheme_performance_metrics"
    
    scheme_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("government_schemes.id"), nullable=False)
    
    # Time Period
    measurement_period: Mapped[str] = mapped_column(String(20), nullable=False)  # monthly, quarterly, yearly
    period_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    
    # Geographic Scope
    state: Mapped[Optional[str]] = mapped_column(String(50))
    district: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Application Metrics
    total_applications: Mapped[int] = mapped_column(Integer, default=0)
    approved_applications: Mapped[int] = mapped_column(Integer, default=0)
    rejected_applications: Mapped[int] = mapped_column(Integer, default=0)
    pending_applications: Mapped[int] = mapped_column(Integer, default=0)
    
    # Processing Metrics
    average_processing_time_days: Mapped[Optional[float]] = mapped_column(Float)
    approval_rate: Mapped[Optional[float]] = mapped_column(Float)
    rejection_rate: Mapped[Optional[float]] = mapped_column(Float)
    
    # Financial Metrics
    total_budget_allocated: Mapped[Optional[float]] = mapped_column(Float)
    total_amount_disbursed: Mapped[Optional[float]] = mapped_column(Float)
    budget_utilization_percentage: Mapped[Optional[float]] = mapped_column(Float)
    
    # Beneficiary Metrics
    total_beneficiaries: Mapped[int] = mapped_column(Integer, default=0)
    tribal_beneficiaries: Mapped[Optional[int]] = mapped_column(Integer)
    female_beneficiaries: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Quality Metrics
    beneficiary_satisfaction_score: Mapped[Optional[float]] = mapped_column(Float)
    complaint_count: Mapped[Optional[int]] = mapped_column(Integer)
    grievance_resolution_rate: Mapped[Optional[float]] = mapped_column(Float)
    
    # Digital Adoption
    online_applications_percentage: Mapped[Optional[float]] = mapped_column(Float)
    digital_document_submission_rate: Mapped[Optional[float]] = mapped_column(Float)
    
    # Calculated Fields
    calculated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    data_sources: Mapped[List[str]] = mapped_column(JSON, nullable=False)
    calculation_method: Mapped[str] = mapped_column(Text, nullable=False)