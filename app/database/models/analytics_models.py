"""
Analytics and reporting database models
"""

from sqlalchemy import String, DateTime, Boolean, Integer, Float, Text, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any

from app.core.database import Base

class ReportType(str, Enum):
    """Report type enumeration"""
    CLAIM_SUMMARY = "claim_summary"
    VERIFICATION_STATUS = "verification_status"
    LAND_USE_ANALYSIS = "land_use_analysis"
    SCHEME_ELIGIBILITY = "scheme_eligibility"
    PERFORMANCE_METRICS = "performance_metrics"
    CUSTOM = "custom"

class AnalyticsReport(Base):
    """Analytics reports and dashboards"""
    
    __tablename__ = "analytics_reports"
    
    # Basic Information
    report_name: Mapped[str] = mapped_column(String(200), nullable=False)
    report_type: Mapped[ReportType] = mapped_column(String(50), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    
    # Report Configuration
    parameters: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    filters: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    
    # Data and Results
    data: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    summary_statistics: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    visualizations: Mapped[Optional[List[str]]] = mapped_column(JSON)  # Chart configurations
    
    # Generation Information
    generated_by: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    generation_time_seconds: Mapped[Optional[float]] = mapped_column(Float)
    
    # Scope
    scope_level: Mapped[str] = mapped_column(String(20), nullable=False)  # national, state, district, block, village
    scope_values: Mapped[List[str]] = mapped_column(JSON, nullable=False)  # Specific locations
    
    # Time Period
    report_period_start: Mapped[Optional[datetime]] = mapped_column(DateTime)
    report_period_end: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Status
    is_scheduled: Mapped[bool] = mapped_column(Boolean, default=False)
    schedule_frequency: Mapped[Optional[str]] = mapped_column(String(20))  # daily, weekly, monthly
    next_generation: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Access Control
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    shared_with: Mapped[Optional[List[str]]] = mapped_column(JSON)  # User IDs

class PerformanceMetric(Base):
    """System performance metrics and KPIs"""
    
    __tablename__ = "performance_metrics"
    
    # Metric Information
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)
    metric_type: Mapped[str] = mapped_column(String(50), nullable=False)  # count, percentage, average, etc.
    category: Mapped[str] = mapped_column(String(50), nullable=False)  # claims, documents, verification, etc.
    
    # Value
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    target_value: Mapped[Optional[float]] = mapped_column(Float)
    unit: Mapped[Optional[str]] = mapped_column(String(20))
    
    # Context
    state: Mapped[Optional[str]] = mapped_column(String(50))
    district: Mapped[Optional[str]] = mapped_column(String(100))
    time_period: Mapped[str] = mapped_column(String(20), nullable=False)  # daily, weekly, monthly, yearly
    
    # Metadata
    calculation_method: Mapped[Optional[str]] = mapped_column(Text)
    data_sources: Mapped[Optional[List[str]]] = mapped_column(JSON)
    
    # Timestamps
    measurement_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    calculation_timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Dashboard(Base):
    """User dashboards and widgets"""
    
    __tablename__ = "dashboards"
    
    # Basic Information
    dashboard_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    
    # Owner and Access
    owner_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    is_shared: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Layout and Configuration
    layout: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)  # Grid layout configuration
    widgets: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, nullable=False)  # Widget configurations
    
    # Filters and Settings
    default_filters: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    refresh_interval: Mapped[Optional[int]] = mapped_column(Integer)  # Seconds
    
    # Access Control
    allowed_roles: Mapped[Optional[List[str]]] = mapped_column(JSON)
    shared_with_users: Mapped[Optional[List[str]]] = mapped_column(JSON)

class DataExport(Base):
    """Data export requests and history"""
    
    __tablename__ = "data_exports"
    
    # Export Information
    export_name: Mapped[str] = mapped_column(String(200), nullable=False)
    export_type: Mapped[str] = mapped_column(String(50), nullable=False)  # csv, excel, pdf, json
    data_type: Mapped[str] = mapped_column(String(50), nullable=False)  # claims, documents, analytics
    
    # Request Details
    requested_by: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    request_parameters: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    filters: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    
    # Processing Status
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, processing, completed, failed
    progress_percentage: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    
    # Results
    file_path: Mapped[Optional[str]] = mapped_column(String(500))
    file_size_bytes: Mapped[Optional[int]] = mapped_column(Integer)
    record_count: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Timestamps
    requested_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Error Information
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    
    # Download Information
    download_count: Mapped[int] = mapped_column(Integer, default=0)
    last_downloaded: Mapped[Optional[datetime]] = mapped_column(DateTime)

class SystemAlert(Base):
    """System alerts and notifications"""
    
    __tablename__ = "system_alerts"
    
    # Alert Information
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)  # error, warning, info, success
    severity: Mapped[str] = mapped_column(String(20), nullable=False)  # low, medium, high, critical
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Source Information
    source_component: Mapped[str] = mapped_column(String(100), nullable=False)
    source_function: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Context
    context_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    affected_users: Mapped[Optional[List[str]]] = mapped_column(JSON)
    affected_resources: Mapped[Optional[List[str]]] = mapped_column(JSON)
    
    # Status
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    resolved_by: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text)
    
    # Acknowledgment
    acknowledged_by: Mapped[Optional[List[str]]] = mapped_column(JSON)  # User IDs
    acknowledgment_required: Mapped[bool] = mapped_column(Boolean, default=False)

class APIUsageLog(Base):
    """API usage tracking and analytics"""
    
    __tablename__ = "api_usage_logs"
    
    # Request Information
    endpoint: Mapped[str] = mapped_column(String(200), nullable=False)
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    user_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    # Request Details
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    user_agent: Mapped[Optional[str]] = mapped_column(Text)
    request_size_bytes: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Response Information
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    response_size_bytes: Mapped[Optional[int]] = mapped_column(Integer)
    response_time_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Timestamps
    request_timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Error Information
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    error_type: Mapped[Optional[str]] = mapped_column(String(100))

class GeospatialAnalysis(Base):
    """Geospatial analysis results and statistics"""
    
    __tablename__ = "geospatial_analyses"
    
    # Analysis Information
    analysis_name: Mapped[str] = mapped_column(String(200), nullable=False)
    analysis_type: Mapped[str] = mapped_column(String(50), nullable=False)  # land_use, change_detection, proximity, etc.
    description: Mapped[Optional[str]] = mapped_column(Text)
    
    # Input Parameters
    input_parameters: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    data_sources: Mapped[List[str]] = mapped_column(JSON, nullable=False)
    
    # Geographic Scope
    study_area_bounds: Mapped[Optional[str]] = mapped_column(String(200))  # Bounding box coordinates
    states_covered: Mapped[List[str]] = mapped_column(JSON, nullable=False)
    districts_covered: Mapped[Optional[List[str]]] = mapped_column(JSON)
    
    # Results
    results_summary: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    detailed_results: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    result_files: Mapped[Optional[List[str]]] = mapped_column(JSON)  # File paths
    
    # Processing Information
    processed_by: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    processing_start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    processing_end_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    processing_duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Quality Metrics
    accuracy_metrics: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float)
    
    # Status
    status: Mapped[str] = mapped_column(String(20), default="completed")  # completed, failed, in_progress
    error_message: Mapped[Optional[str]] = mapped_column(Text)

class ComplianceReport(Base):
    """Compliance and regulatory reports"""
    
    __tablename__ = "compliance_reports"
    
    # Report Information
    report_title: Mapped[str] = mapped_column(String(200), nullable=False)
    compliance_type: Mapped[str] = mapped_column(String(50), nullable=False)  # fra_compliance, data_privacy, etc.
    regulation_reference: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Scope
    assessment_period_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    assessment_period_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    geographical_scope: Mapped[List[str]] = mapped_column(JSON, nullable=False)
    
    # Assessment Results
    compliance_score: Mapped[float] = mapped_column(Float, nullable=False)  # 0-100
    compliance_status: Mapped[str] = mapped_column(String(20), nullable=False)  # compliant, non_compliant, partial
    
    # Findings
    findings: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, nullable=False)
    recommendations: Mapped[List[str]] = mapped_column(JSON, nullable=False)
    action_items: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON)
    
    # Assessment Details
    assessed_by: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    assessment_methodology: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_files: Mapped[Optional[List[str]]] = mapped_column(JSON)
    
    # Review and Approval
    reviewed_by: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    review_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    review_comments: Mapped[Optional[str]] = mapped_column(Text)
    
    approved_by: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    approval_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Publication
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    publication_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    distribution_list: Mapped[Optional[List[str]]] = mapped_column(JSON)

class DataQualityMetric(Base):
    """Data quality assessment metrics"""
    
    __tablename__ = "data_quality_metrics"
    
    # Metric Information
    table_name: Mapped[str] = mapped_column(String(100), nullable=False)
    column_name: Mapped[Optional[str]] = mapped_column(String(100))
    metric_type: Mapped[str] = mapped_column(String(50), nullable=False)  # completeness, accuracy, consistency, etc.
    
    # Quality Score
    quality_score: Mapped[float] = mapped_column(Float, nullable=False)  # 0-100
    threshold_score: Mapped[float] = mapped_column(Float, default=80.0)
    is_passing: Mapped[bool] = mapped_column(Boolean, nullable=False)
    
    # Details
    total_records: Mapped[int] = mapped_column(Integer, nullable=False)
    issues_found: Mapped[int] = mapped_column(Integer, default=0)
    issue_details: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON)
    
    # Assessment Information
    assessment_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    assessment_method: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Trend Information
    previous_score: Mapped[Optional[float]] = mapped_column(Float)
    trend_direction: Mapped[Optional[str]] = mapped_column(String(20))  # improving, declining, stable
    
    # Remediation
    remediation_suggested: Mapped[Optional[str]] = mapped_column(Text)
    remediation_priority: Mapped[str] = mapped_column(String(20), default="medium")  # low, medium, high, critical