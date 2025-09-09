"""
Database models package initialization
"""

from app.database.models import (
    user_models,
    document_models, 
    gis_models,
    analytics_models,
    scheme_models
)

# Export all models for easy importing
from app.database.models.user_models import (
    User, UserSession, AuditLog, Permission, RolePermission, UserNotification
)

from app.database.models.document_models import (
    Document, FRAClaim, FieldVerification, DocumentTemplate, ProcessingQueue
)

from app.database.models.gis_models import (
    GISLayer, GISFeature, SatelliteImage, LandUseClassification, 
    CommunityAsset, VillageBoundary, ChangeDetection
)

from app.database.models.analytics_models import (
    AnalyticsReport, PerformanceMetric, Dashboard, DataExport, 
    SystemAlert, APIUsageLog, GeospatialAnalysis, ComplianceReport, DataQualityMetric
)

from app.database.models.scheme_models import (
    GovernmentScheme, FRAHolderProfile, SchemeEligibilityAssessment,
    SchemeApplication, SchemeRecommendation, SchemePerformanceMetric
)

__all__ = [
    # User models
    "User", "UserSession", "AuditLog", "Permission", "RolePermission", "UserNotification",
    
    # Document models  
    "Document", "FRAClaim", "FieldVerification", "DocumentTemplate", "ProcessingQueue",
    
    # GIS models
    "GISLayer", "GISFeature", "SatelliteImage", "LandUseClassification", 
    "CommunityAsset", "VillageBoundary", "ChangeDetection",
    
    # Analytics models
    "AnalyticsReport", "PerformanceMetric", "Dashboard", "DataExport", 
    "SystemAlert", "APIUsageLog", "GeospatialAnalysis", "ComplianceReport", "DataQualityMetric",
    
    # Scheme models
    "GovernmentScheme", "FRAHolderProfile", "SchemeEligibilityAssessment",
    "SchemeApplication", "SchemeRecommendation", "SchemePerformanceMetric"
]