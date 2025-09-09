"""
Analytics and reporting API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, timedelta
import json

from app.core.config import settings, STATE_CONFIG
from app.core.database import get_db
from app.database.models.user_models import User
from app.database.models.document_models import FRAClaim, Document, ClaimStatus, DocumentStatus
from app.database.models.gis_models import CommunityAsset, LandUseClassification, ChangeDetection
from app.database.models.analytics_models import (
    AnalyticsReport, PerformanceMetric, Dashboard, DataExport, SystemAlert
)
from app.api.auth import get_current_user

router = APIRouter()

# Pydantic models for request/response
class ClaimsSummary(BaseModel):
    total_claims: int
    submitted: int
    under_review: int
    approved: int
    rejected: int
    title_distributed: int
    total_area_claimed: float
    total_area_approved: float

class StateSummary(BaseModel):
    state_name: str
    total_claims: int
    approval_rate: float
    total_area_hectares: float
    tribal_population: int
    forest_cover_percent: float
    priority_districts: List[str]

class PerformanceMetrics(BaseModel):
    document_processing_accuracy: float
    average_claim_processing_time: float
    system_uptime_percentage: float
    user_satisfaction_score: float
    data_quality_score: float

class DashboardData(BaseModel):
    summary_stats: Dict[str, Any]
    recent_activities: List[Dict[str, Any]]
    performance_metrics: PerformanceMetrics
    geographical_distribution: List[Dict[str, Any]]
    trends: Dict[str, Any]

class ReportRequest(BaseModel):
    report_type: str = Field(..., description="Type of report to generate")
    parameters: Dict[str, Any] = Field(default_factory=dict)
    filters: Optional[Dict[str, Any]] = None
    format: str = Field(default="json", description="Output format: json, csv, pdf")

class ReportResponse(BaseModel):
    report_id: str
    status: str
    report_type: str
    generated_at: datetime
    data: Optional[Dict[str, Any]] = None
    download_url: Optional[str] = None

# Utility functions
async def calculate_claims_summary(db: AsyncSession, state: Optional[str] = None, district: Optional[str] = None) -> ClaimsSummary:
    """Calculate claims summary statistics"""
    try:
        query = select(FRAClaim)
        
        if state:
            query = query.where(FRAClaim.state == state)
        if district:
            query = query.where(FRAClaim.district == district)
        
        result = await db.execute(query)
        claims = result.scalars().all()
        
        summary = ClaimsSummary(
            total_claims=len(claims),
            submitted=len([c for c in claims if c.status == ClaimStatus.SUBMITTED]),
            under_review=len([c for c in claims if c.status == ClaimStatus.UNDER_REVIEW]),
            approved=len([c for c in claims if c.status == ClaimStatus.APPROVED]),
            rejected=len([c for c in claims if c.status == ClaimStatus.REJECTED]),
            title_distributed=len([c for c in claims if c.status == ClaimStatus.TITLE_DISTRIBUTED]),
            total_area_claimed=sum(c.area_claimed_hectares or 0 for c in claims),
            total_area_approved=sum(c.area_approved_hectares or 0 for c in claims)
        )
        
        return summary
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate claims summary: {str(e)}"
        )

async def calculate_performance_metrics(db: AsyncSession) -> PerformanceMetrics:
    """Calculate system performance metrics"""
    try:
        # Document processing accuracy
        doc_result = await db.execute(
            select(func.avg(Document.confidence_score)).where(
                Document.status == DocumentStatus.PROCESSED
            )
        )
        doc_accuracy = doc_result.scalar() or 0.0
        
        # Average claim processing time (placeholder calculation)
        processing_time = 45.5  # days
        
        # System metrics (placeholders)
        uptime = 99.8
        satisfaction = 4.2
        data_quality = 92.5
        
        return PerformanceMetrics(
            document_processing_accuracy=doc_accuracy * 100,
            average_claim_processing_time=processing_time,
            system_uptime_percentage=uptime,
            user_satisfaction_score=satisfaction,
            data_quality_score=data_quality
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate performance metrics: {str(e)}"
        )

# API Endpoints
@router.get("/dashboard", response_model=DashboardData)
async def get_dashboard_data(
    state: Optional[str] = None,
    district: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get comprehensive dashboard data"""
    try:
        # Apply role-based filtering
        if current_user.role.value == "government_official" and current_user.state:
            state = current_user.state
        elif current_user.role.value in ["field_worker", "tribal_community"]:
            state = current_user.state
            district = current_user.district
        
        # Get summary statistics
        claims_summary = await calculate_claims_summary(db, state, district)
        performance_metrics = await calculate_performance_metrics(db)
        
        # Get recent activities
        recent_claims_result = await db.execute(
            select(FRAClaim)
            .where(
                and_(
                    FRAClaim.state == state if state else True,
                    FRAClaim.district == district if district else True
                )
            )
            .order_by(desc(FRAClaim.created_at))
            .limit(10)
        )
        recent_claims = recent_claims_result.scalars().all()
        
        recent_activities = [
            {
                "type": "claim_submitted",
                "description": f"New FRA claim {claim.claim_number} submitted by {claim.claimant_name}",
                "timestamp": claim.created_at,
                "location": f"{claim.village}, {claim.district}",
                "status": claim.status.value
            }
            for claim in recent_claims
        ]
        
        # Get geographical distribution
        geo_distribution = []
        for state_name, config in STATE_CONFIG.items():
            if not state or state == state_name:
                state_summary = await calculate_claims_summary(db, state_name)
                geo_distribution.append({
                    "state": state_name,
                    "state_code": config["code"],
                    "total_claims": state_summary.total_claims,
                    "approval_rate": (state_summary.approved / max(state_summary.total_claims, 1)) * 100,
                    "forest_cover": config["forest_cover_percent"],
                    "tribal_population_percent": config["tribal_population_percent"]
                })
        
        # Calculate trends (placeholder data)
        trends = {
            "claims_trend": {
                "current_month": claims_summary.total_claims,
                "previous_month": max(0, claims_summary.total_claims - 15),
                "growth_rate": 12.5
            },
            "approval_trend": {
                "current_rate": (claims_summary.approved / max(claims_summary.total_claims, 1)) * 100,
                "previous_rate": 68.2,
                "improvement": 3.8
            }
        }
        
        return DashboardData(
            summary_stats={
                "claims": claims_summary.dict(),
                "total_users": 1250,  # Placeholder
                "active_sessions": 45,  # Placeholder
                "documents_processed": 890  # Placeholder
            },
            recent_activities=recent_activities,
            performance_metrics=performance_metrics,
            geographical_distribution=geo_distribution,
            trends=trends
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve dashboard data: {str(e)}"
        )

@router.get("/claims-summary", response_model=ClaimsSummary)
async def get_claims_summary(
    state: Optional[str] = None,
    district: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get FRA claims summary statistics"""
    try:
        # Apply role-based filtering
        if current_user.role.value == "government_official" and current_user.state:
            state = current_user.state
        elif current_user.role.value in ["field_worker", "tribal_community"]:
            state = current_user.state
            district = current_user.district
        
        return await calculate_claims_summary(db, state, district)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve claims summary: {str(e)}"
        )

@router.get("/state-wise-summary", response_model=List[StateSummary])
async def get_state_wise_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get state-wise summary of FRA implementation"""
    try:
        summaries = []
        
        states_to_process = settings.SUPPORTED_STATES
        if current_user.role.value == "government_official" and current_user.state:
            states_to_process = [current_user.state]
        
        for state_name in states_to_process:
            claims_summary = await calculate_claims_summary(db, state_name)
            state_config = STATE_CONFIG.get(state_name, {})
            
            approval_rate = 0.0
            if claims_summary.total_claims > 0:
                approval_rate = (claims_summary.approved / claims_summary.total_claims) * 100
            
            summaries.append(StateSummary(
                state_name=state_name,
                total_claims=claims_summary.total_claims,
                approval_rate=approval_rate,
                total_area_hectares=claims_summary.total_area_approved,
                tribal_population=int(state_config.get("tribal_population_percent", 0) * 1000000),  # Placeholder
                forest_cover_percent=state_config.get("forest_cover_percent", 0),
                priority_districts=state_config.get("priority_districts", [])
            ))
        
        return summaries
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve state-wise summary: {str(e)}"
        )

@router.get("/performance-metrics", response_model=PerformanceMetrics)
async def get_performance_metrics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get system performance metrics"""
    try:
        return await calculate_performance_metrics(db)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve performance metrics: {str(e)}"
        )

@router.get("/land-use-statistics")
async def get_land_use_statistics(
    state: Optional[str] = None,
    district: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get land use classification statistics"""
    try:
        query = select(LandUseClassification)
        
        # Apply role-based filtering
        if current_user.role.value == "government_official" and current_user.state:
            state = current_user.state
        elif current_user.role.value in ["field_worker", "tribal_community"]:
            state = current_user.state
            district = current_user.district
        
        if state:
            query = query.where(LandUseClassification.state == state)
        if district:
            query = query.where(LandUseClassification.district == district)
        
        result = await db.execute(query)
        classifications = result.scalars().all()
        
        # Aggregate statistics
        land_use_stats = {}
        total_area = 0
        
        for classification in classifications:
            land_class = classification.land_use_class.value
            area = classification.area_hectares
            
            if land_class not in land_use_stats:
                land_use_stats[land_class] = {
                    "area_hectares": 0,
                    "percentage": 0,
                    "count": 0,
                    "avg_confidence": 0
                }
            
            land_use_stats[land_class]["area_hectares"] += area
            land_use_stats[land_class]["count"] += 1
            land_use_stats[land_class]["avg_confidence"] += classification.confidence_score
            total_area += area
        
        # Calculate percentages and average confidence
        for land_class in land_use_stats:
            stats = land_use_stats[land_class]
            stats["percentage"] = (stats["area_hectares"] / max(total_area, 1)) * 100
            stats["avg_confidence"] = stats["avg_confidence"] / max(stats["count"], 1)
        
        return {
            "total_area_analyzed": total_area,
            "land_use_distribution": land_use_stats,
            "analysis_date": datetime.utcnow(),
            "geographic_scope": {
                "state": state,
                "district": district
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve land use statistics: {str(e)}"
        )

@router.get("/community-assets-summary")
async def get_community_assets_summary(
    state: Optional[str] = None,
    district: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get community assets detection summary"""
    try:
        query = select(CommunityAsset)
        
        # Apply role-based filtering
        if current_user.role.value == "government_official" and current_user.state:
            state = current_user.state
        elif current_user.role.value in ["field_worker", "tribal_community"]:
            state = current_user.state
            district = current_user.district
        
        if state:
            query = query.where(CommunityAsset.state == state)
        if district:
            query = query.where(CommunityAsset.district == district)
        
        result = await db.execute(query)
        assets = result.scalars().all()
        
        # Aggregate by asset type
        asset_summary = {}
        total_assets = len(assets)
        verified_assets = 0
        
        for asset in assets:
            asset_type = asset.asset_type
            
            if asset_type not in asset_summary:
                asset_summary[asset_type] = {
                    "count": 0,
                    "verified_count": 0,
                    "avg_confidence": 0,
                    "total_area": 0
                }
            
            asset_summary[asset_type]["count"] += 1
            asset_summary[asset_type]["avg_confidence"] += asset.detection_confidence
            asset_summary[asset_type]["total_area"] += asset.estimated_area_sqm or 0
            
            if asset.is_verified:
                asset_summary[asset_type]["verified_count"] += 1
                verified_assets += 1
        
        # Calculate averages
        for asset_type in asset_summary:
            stats = asset_summary[asset_type]
            stats["avg_confidence"] = stats["avg_confidence"] / max(stats["count"], 1)
            stats["verification_rate"] = (stats["verified_count"] / max(stats["count"], 1)) * 100
        
        return {
            "total_assets_detected": total_assets,
            "total_verified": verified_assets,
            "verification_rate": (verified_assets / max(total_assets, 1)) * 100,
            "asset_type_distribution": asset_summary,
            "detection_methods": {
                "satellite_analysis": len([a for a in assets if a.detection_method == "satellite_analysis"]),
                "field_survey": len([a for a in assets if a.detection_method == "field_survey"]),
                "community_mapping": len([a for a in assets if a.detection_method == "community_mapping"])
            },
            "geographic_scope": {
                "state": state,
                "district": district
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve community assets summary: {str(e)}"
        )

@router.post("/reports/generate", response_model=ReportResponse)
async def generate_report(
    report_request: ReportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Generate analytics report"""
    try:
        # Check permissions
        if current_user.role.value not in ["admin", "government_official"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to generate reports"
            )
        
        # Generate report data based on type
        report_data = {}
        
        if report_request.report_type == "claims_summary":
            state = report_request.parameters.get("state")
            district = report_request.parameters.get("district")
            claims_summary = await calculate_claims_summary(db, state, district)
            report_data = claims_summary.dict()
            
        elif report_request.report_type == "performance_metrics":
            performance_metrics = await calculate_performance_metrics(db)
            report_data = performance_metrics.dict()
            
        elif report_request.report_type == "state_wise_analysis":
            summaries = []
            for state_name in settings.SUPPORTED_STATES:
                claims_summary = await calculate_claims_summary(db, state_name)
                state_config = STATE_CONFIG.get(state_name, {})
                summaries.append({
                    "state": state_name,
                    "claims": claims_summary.dict(),
                    "config": state_config
                })
            report_data = {"states": summaries}
        
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported report type: {report_request.report_type}"
            )
        
        # Create report record
        analytics_report = AnalyticsReport(
            report_name=f"{report_request.report_type.replace('_', ' ').title()} Report",
            report_type=report_request.report_type,
            parameters=report_request.parameters,
            filters=report_request.filters,
            data=report_data,
            generated_by=current_user.id,
            scope_level="national",
            scope_values=settings.SUPPORTED_STATES
        )
        
        db.add(analytics_report)
        await db.commit()
        await db.refresh(analytics_report)
        
        return ReportResponse(
            report_id=str(analytics_report.id),
            status="completed",
            report_type=report_request.report_type,
            generated_at=analytics_report.created_at,
            data=report_data if report_request.format == "json" else None,
            download_url=f"/api/v1/analytics/reports/{analytics_report.id}/download" if report_request.format != "json" else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Report generation failed: {str(e)}"
        )

@router.get("/reports/{report_id}")
async def get_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get analytics report by ID"""
    try:
        result = await db.execute(select(AnalyticsReport).where(AnalyticsReport.id == report_id))
        report = result.scalar_one_or_none()
        
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report not found"
            )
        
        # Check permissions
        if (current_user.role.value not in ["admin", "government_official"] and 
            report.generated_by != current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        return {
            "id": str(report.id),
            "report_name": report.report_name,
            "report_type": report.report_type,
            "description": report.description,
            "parameters": report.parameters,
            "filters": report.filters,
            "data": report.data,
            "summary_statistics": report.summary_statistics,
            "generated_at": report.created_at,
            "scope_level": report.scope_level,
            "scope_values": report.scope_values
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve report: {str(e)}"
        )

@router.get("/change-detection-summary")
async def get_change_detection_summary(
    state: Optional[str] = None,
    district: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get land use change detection summary"""
    try:
        query = select(ChangeDetection)
        
        # Apply role-based filtering
        if current_user.role.value == "government_official" and current_user.state:
            state = current_user.state
        elif current_user.role.value in ["field_worker", "tribal_community"]:
            state = current_user.state
            district = current_user.district
        
        if state:
            query = query.where(ChangeDetection.state == state)
        if district:
            query = query.where(ChangeDetection.district == district)
        if start_date:
            query = query.where(ChangeDetection.start_date >= start_date)
        if end_date:
            query = query.where(ChangeDetection.end_date <= end_date)
        
        result = await db.execute(query)
        changes = result.scalars().all()
        
        # Aggregate statistics
        change_summary = {}
        total_area_changed = 0
        
        for change in changes:
            change_type = change.change_type
            area = change.area_changed_hectares
            
            if change_type not in change_summary:
                change_summary[change_type] = {
                    "count": 0,
                    "total_area_hectares": 0,
                    "avg_confidence": 0,
                    "from_land_uses": {},
                    "to_land_uses": {}
                }
            
            change_summary[change_type]["count"] += 1
            change_summary[change_type]["total_area_hectares"] += area
            change_summary[change_type]["avg_confidence"] += change.confidence_score
            
            # Track land use transitions
            from_use = change.from_land_use
            to_use = change.to_land_use
            
            change_summary[change_type]["from_land_uses"][from_use] = change_summary[change_type]["from_land_uses"].get(from_use, 0) + 1
            change_summary[change_type]["to_land_uses"][to_use] = change_summary[change_type]["to_land_uses"].get(to_use, 0) + 1
            
            total_area_changed += area
        
        # Calculate averages
        for change_type in change_summary:
            stats = change_summary[change_type]
            stats["avg_confidence"] = stats["avg_confidence"] / max(stats["count"], 1)
            stats["area_percentage"] = (stats["total_area_hectares"] / max(total_area_changed, 1)) * 100
        
        return {
            "total_changes_detected": len(changes),
            "total_area_changed_hectares": total_area_changed,
            "change_type_distribution": change_summary,
            "time_period": {
                "start_date": start_date,
                "end_date": end_date
            },
            "geographic_scope": {
                "state": state,
                "district": district
            },
            "analysis_date": datetime.utcnow()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve change detection summary: {str(e)}"
        )