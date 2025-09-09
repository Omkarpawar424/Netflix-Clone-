"""
Government schemes integration and recommendation API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, func
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
import asyncio

from app.core.config import settings, CENTRAL_SCHEMES
from app.core.database import get_db
from app.database.models.user_models import User
from app.database.models.document_models import FRAClaim
from app.database.models.scheme_models import (
    GovernmentScheme, FRAHolderProfile, SchemeEligibilityAssessment,
    SchemeApplication, SchemeRecommendation, SchemePerformanceMetric,
    SchemeType, EligibilityStatus, ApplicationStatus
)
from app.api.auth import get_current_user
from app.ai_models.model_manager import ModelManager

router = APIRouter()

# Pydantic models for request/response
class SchemeInfo(BaseModel):
    id: str
    scheme_name: str
    scheme_code: str
    scheme_type: str
    implementing_ministry: str
    description: str
    is_active: bool
    coverage_type: str
    launch_date: Optional[datetime] = None

class SchemeDetails(BaseModel):
    id: str
    scheme_name: str
    scheme_code: str
    scheme_type: str
    description: str
    objectives: List[str]
    key_features: List[str]
    implementing_ministry: str
    implementing_agency: Optional[str] = None
    eligibility_criteria: Dict[str, Any]
    target_beneficiaries: List[str]
    benefit_amount: Optional[Dict[str, Any]] = None
    application_process: List[str]
    required_documents: List[str]
    application_channels: List[str]
    helpline_number: Optional[str] = None
    website_url: Optional[str] = None
    coverage_type: str
    covered_states: Optional[List[str]] = None

class FRAHolderCreate(BaseModel):
    holder_name: str
    father_husband_name: Optional[str] = None
    date_of_birth: Optional[datetime] = None
    gender: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    state: str
    district: str
    block: str
    village: str
    caste_category: Optional[str] = None
    tribe_name: Optional[str] = None
    is_tribal: bool = False
    family_size: Optional[int] = None
    annual_income: Optional[float] = None
    landholding_hectares: Optional[float] = None
    housing_type: Optional[str] = None
    bank_account: Optional[bool] = None
    fra_claim_id: Optional[str] = None

class FRAHolderResponse(BaseModel):
    id: str
    holder_name: str
    state: str
    district: str
    village: str
    is_tribal: bool
    annual_income: Optional[float] = None
    landholding_hectares: Optional[float] = None
    bank_account: Optional[bool] = None
    created_at: datetime

class EligibilityAssessmentResponse(BaseModel):
    id: str
    scheme_name: str
    eligibility_status: str
    eligibility_score: float
    confidence_score: float
    recommendation_priority: str
    recommendation_reason: str
    next_steps: List[str]
    estimated_benefit: Optional[str] = None
    assessment_date: datetime

class SchemeRecommendationResponse(BaseModel):
    id: str
    recommended_schemes: List[Dict[str, Any]]
    priority_ranking: List[str]
    overall_confidence: float
    recommendation_date: datetime
    expires_at: datetime

class ApplicationRequest(BaseModel):
    scheme_id: str
    application_data: Dict[str, Any]
    submitted_documents: List[str]
    application_channel: str = "online"
    communication_preferences: Optional[Dict[str, str]] = None

class ApplicationResponse(BaseModel):
    id: str
    application_number: str
    scheme_name: str
    status: str
    application_date: datetime
    expected_processing_time: Optional[int] = None
    assigned_officer: Optional[str] = None

# Utility functions
async def get_model_manager() -> ModelManager:
    """Get model manager instance"""
    return ModelManager()

def create_fra_holder_profile_from_claim(claim: FRAClaim) -> Dict[str, Any]:
    """Create FRA holder profile data from FRA claim"""
    return {
        "holder_name": claim.claimant_name,
        "father_husband_name": claim.father_husband_name,
        "phone_number": claim.phone_number,
        "address": claim.address,
        "state": claim.state,
        "district": claim.district,
        "block": claim.block,
        "village": claim.village,
        "caste_category": claim.caste_tribe,
        "is_tribal": True,  # FRA claimants are typically tribal
        "family_size": claim.family_members,
        "landholding_hectares": claim.area_claimed_hectares,
        "fra_claim_id": str(claim.id),
        "title_holder": claim.status == "title_distributed",
        "title_area_hectares": claim.area_approved_hectares
    }

# API Endpoints
@router.get("/schemes", response_model=List[SchemeInfo])
async def list_government_schemes(
    scheme_type: Optional[str] = None,
    state: Optional[str] = None,
    is_active: bool = True,
    limit: int = Query(100, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List available government schemes"""
    try:
        query = select(GovernmentScheme)
        
        # Apply filters
        if scheme_type:
            query = query.where(GovernmentScheme.scheme_type == scheme_type)
        if is_active:
            query = query.where(GovernmentScheme.is_active == True)
        if state:
            query = query.where(
                or_(
                    GovernmentScheme.coverage_type == "national",
                    GovernmentScheme.covered_states.contains([state])
                )
            )
        
        query = query.limit(limit)
        result = await db.execute(query)
        schemes = result.scalars().all()
        
        return [
            SchemeInfo(
                id=str(scheme.id),
                scheme_name=scheme.scheme_name,
                scheme_code=scheme.scheme_code,
                scheme_type=scheme.scheme_type.value,
                implementing_ministry=scheme.implementing_ministry,
                description=scheme.description[:200] + "..." if len(scheme.description) > 200 else scheme.description,
                is_active=scheme.is_active,
                coverage_type=scheme.coverage_type,
                launch_date=scheme.launch_date
            )
            for scheme in schemes
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve schemes: {str(e)}"
        )

@router.get("/schemes/{scheme_id}", response_model=SchemeDetails)
async def get_scheme_details(
    scheme_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed information about a government scheme"""
    try:
        result = await db.execute(select(GovernmentScheme).where(GovernmentScheme.id == scheme_id))
        scheme = result.scalar_one_or_none()
        
        if not scheme:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scheme not found"
            )
        
        return SchemeDetails(
            id=str(scheme.id),
            scheme_name=scheme.scheme_name,
            scheme_code=scheme.scheme_code,
            scheme_type=scheme.scheme_type.value,
            description=scheme.description,
            objectives=scheme.objectives,
            key_features=scheme.key_features,
            implementing_ministry=scheme.implementing_ministry,
            implementing_agency=scheme.implementing_agency,
            eligibility_criteria=scheme.eligibility_criteria,
            target_beneficiaries=scheme.target_beneficiaries,
            benefit_amount=scheme.benefit_amount,
            application_process=scheme.application_process,
            required_documents=scheme.required_documents,
            application_channels=scheme.application_channels,
            helpline_number=scheme.helpline_number,
            website_url=scheme.website_url,
            coverage_type=scheme.coverage_type,
            covered_states=scheme.covered_states
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve scheme details: {str(e)}"
        )

@router.post("/fra-holders", response_model=FRAHolderResponse)
async def create_fra_holder_profile(
    holder_data: FRAHolderCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create FRA holder profile for scheme eligibility assessment"""
    try:
        # Create profile
        fra_holder = FRAHolderProfile(
            holder_name=holder_data.holder_name,
            father_husband_name=holder_data.father_husband_name,
            date_of_birth=holder_data.date_of_birth,
            gender=holder_data.gender,
            phone_number=holder_data.phone_number,
            email=holder_data.email,
            address=holder_data.address,
            state=holder_data.state,
            district=holder_data.district,
            block=holder_data.block,
            village=holder_data.village,
            caste_category=holder_data.caste_category,
            tribe_name=holder_data.tribe_name,
            is_tribal=holder_data.is_tribal,
            family_size=holder_data.family_size,
            annual_income=holder_data.annual_income,
            landholding_hectares=holder_data.landholding_hectares,
            housing_type=holder_data.housing_type,
            bank_account=holder_data.bank_account,
            fra_claim_id=holder_data.fra_claim_id,
            data_source="manual_entry",
            last_verified=datetime.utcnow(),
            verified_by=current_user.id
        )
        
        db.add(fra_holder)
        await db.commit()
        await db.refresh(fra_holder)
        
        return FRAHolderResponse(
            id=str(fra_holder.id),
            holder_name=fra_holder.holder_name,
            state=fra_holder.state,
            district=fra_holder.district,
            village=fra_holder.village,
            is_tribal=fra_holder.is_tribal,
            annual_income=fra_holder.annual_income,
            landholding_hectares=fra_holder.landholding_hectares,
            bank_account=fra_holder.bank_account,
            created_at=fra_holder.created_at
        )
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create FRA holder profile: {str(e)}"
        )

@router.get("/fra-holders", response_model=List[FRAHolderResponse])
async def list_fra_holders(
    state: Optional[str] = None,
    district: Optional[str] = None,
    is_tribal: Optional[bool] = None,
    limit: int = Query(100, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List FRA holder profiles"""
    try:
        query = select(FRAHolderProfile)
        
        # Apply role-based filtering
        if current_user.role.value == "government_official" and current_user.state:
            query = query.where(FRAHolderProfile.state == current_user.state)
        elif current_user.role.value in ["field_worker", "tribal_community"]:
            query = query.where(
                and_(
                    FRAHolderProfile.state == current_user.state,
                    FRAHolderProfile.district == current_user.district
                )
            )
        
        # Apply additional filters
        if state:
            query = query.where(FRAHolderProfile.state == state)
        if district:
            query = query.where(FRAHolderProfile.district == district)
        if is_tribal is not None:
            query = query.where(FRAHolderProfile.is_tribal == is_tribal)
        
        query = query.order_by(desc(FRAHolderProfile.created_at)).limit(limit)
        
        result = await db.execute(query)
        holders = result.scalars().all()
        
        return [
            FRAHolderResponse(
                id=str(holder.id),
                holder_name=holder.holder_name,
                state=holder.state,
                district=holder.district,
                village=holder.village,
                is_tribal=holder.is_tribal,
                annual_income=holder.annual_income,
                landholding_hectares=holder.landholding_hectares,
                bank_account=holder.bank_account,
                created_at=holder.created_at
            )
            for holder in holders
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve FRA holders: {str(e)}"
        )

@router.post("/fra-holders/{holder_id}/assess-eligibility")
async def assess_scheme_eligibility(
    holder_id: str,
    scheme_ids: Optional[List[str]] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Assess FRA holder eligibility for government schemes"""
    try:
        # Get FRA holder profile
        holder_result = await db.execute(
            select(FRAHolderProfile).where(FRAHolderProfile.id == holder_id)
        )
        holder = holder_result.scalar_one_or_none()
        
        if not holder:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="FRA holder profile not found"
            )
        
        # Get schemes to assess
        schemes_query = select(GovernmentScheme).where(GovernmentScheme.is_active == True)
        if scheme_ids:
            schemes_query = schemes_query.where(GovernmentScheme.id.in_(scheme_ids))
        
        schemes_result = await db.execute(schemes_query)
        schemes = schemes_result.scalars().all()
        
        # Get model manager for AI-assisted assessment
        model_manager = await get_model_manager()
        
        # Prepare holder data for assessment
        holder_data = {
            "holder_name": holder.holder_name,
            "state": holder.state,
            "district": holder.district,
            "is_tribal": holder.is_tribal,
            "family_size": holder.family_size or 1,
            "annual_income": holder.annual_income or 0,
            "landholding_hectares": holder.landholding_hectares or 0,
            "bank_account": holder.bank_account or False,
            "housing_type": holder.housing_type or "kutcha",
            "rural_household": True,  # FRA holders are typically rural
            "adult_member": True,
            "farmer": holder.landholding_hectares and holder.landholding_hectares > 0,
            "landholding_upto_2ha": holder.landholding_hectares and holder.landholding_hectares <= 2,
            "below_poverty_line": holder.annual_income and holder.annual_income < 50000,
            "no_pucca_house": holder.housing_type != "pucca",
            "no_bank_account": not holder.bank_account,
            "indian_citizen": True
        }
        
        # Get AI recommendations
        recommendations = await model_manager.recommend_schemes(holder_data)
        
        assessments = []
        for scheme in schemes:
            # Find corresponding AI recommendation
            ai_recommendation = next(
                (rec for rec in recommendations if rec.get('scheme_name') == scheme.scheme_code),
                None
            )
            
            if ai_recommendation:
                # Create assessment record
                assessment = SchemeEligibilityAssessment(
                    fra_holder_id=holder.id,
                    scheme_id=scheme.id,
                    eligibility_status=EligibilityStatus.ELIGIBLE if ai_recommendation['eligible'] else EligibilityStatus.NOT_ELIGIBLE,
                    eligibility_score=ai_recommendation['priority_score'] * 100,
                    confidence_score=ai_recommendation['priority_score'],
                    criteria_evaluation={},
                    met_criteria=[],
                    unmet_criteria=[],
                    recommendation_priority="high" if ai_recommendation['priority_score'] > 0.7 else "medium" if ai_recommendation['priority_score'] > 0.4 else "low",
                    recommendation_reason=ai_recommendation['recommendation_reason'],
                    next_steps=ai_recommendation['next_steps'],
                    estimated_benefit=ai_recommendation['estimated_benefit'],
                    assessment_method="ai_assisted",
                    assessed_by=current_user.id
                )
                
                db.add(assessment)
                assessments.append(assessment)
        
        await db.commit()
        
        # Refresh assessments to get IDs
        for assessment in assessments:
            await db.refresh(assessment)
        
        return {
            "holder_id": str(holder.id),
            "total_schemes_assessed": len(assessments),
            "eligible_schemes": len([a for a in assessments if a.eligibility_status == EligibilityStatus.ELIGIBLE]),
            "high_priority_recommendations": len([a for a in assessments if a.recommendation_priority == "high"]),
            "assessment_date": datetime.utcnow(),
            "assessments": [
                {
                    "id": str(assessment.id),
                    "scheme_name": next(s.scheme_name for s in schemes if str(s.id) == str(assessment.scheme_id)),
                    "eligibility_status": assessment.eligibility_status.value,
                    "eligibility_score": assessment.eligibility_score,
                    "recommendation_priority": assessment.recommendation_priority
                }
                for assessment in assessments
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Eligibility assessment failed: {str(e)}"
        )

@router.get("/fra-holders/{holder_id}/eligibility", response_model=List[EligibilityAssessmentResponse])
async def get_eligibility_assessments(
    holder_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get eligibility assessments for an FRA holder"""
    try:
        # Check if holder exists
        holder_result = await db.execute(
            select(FRAHolderProfile).where(FRAHolderProfile.id == holder_id)
        )
        holder = holder_result.scalar_one_or_none()
        
        if not holder:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="FRA holder profile not found"
            )
        
        # Get assessments with scheme details
        assessments_result = await db.execute(
            select(SchemeEligibilityAssessment, GovernmentScheme)
            .join(GovernmentScheme, SchemeEligibilityAssessment.scheme_id == GovernmentScheme.id)
            .where(
                and_(
                    SchemeEligibilityAssessment.fra_holder_id == holder_id,
                    SchemeEligibilityAssessment.is_current == True
                )
            )
            .order_by(desc(SchemeEligibilityAssessment.eligibility_score))
        )
        
        assessment_pairs = assessments_result.all()
        
        return [
            EligibilityAssessmentResponse(
                id=str(assessment.id),
                scheme_name=scheme.scheme_name,
                eligibility_status=assessment.eligibility_status.value,
                eligibility_score=assessment.eligibility_score,
                confidence_score=assessment.confidence_score,
                recommendation_priority=assessment.recommendation_priority,
                recommendation_reason=assessment.recommendation_reason,
                next_steps=assessment.next_steps,
                estimated_benefit=assessment.estimated_benefit,
                assessment_date=assessment.assessment_date
            )
            for assessment, scheme in assessment_pairs
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve eligibility assessments: {str(e)}"
        )

@router.post("/fra-holders/{holder_id}/apply", response_model=ApplicationResponse)
async def submit_scheme_application(
    holder_id: str,
    application_request: ApplicationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Submit scheme application for FRA holder"""
    try:
        # Verify holder and scheme exist
        holder_result = await db.execute(
            select(FRAHolderProfile).where(FRAHolderProfile.id == holder_id)
        )
        holder = holder_result.scalar_one_or_none()
        
        if not holder:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="FRA holder profile not found"
            )
        
        scheme_result = await db.execute(
            select(GovernmentScheme).where(GovernmentScheme.id == application_request.scheme_id)
        )
        scheme = scheme_result.scalar_one_or_none()
        
        if not scheme:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Government scheme not found"
            )
        
        # Check if already applied
        existing_result = await db.execute(
            select(SchemeApplication).where(
                and_(
                    SchemeApplication.fra_holder_id == holder_id,
                    SchemeApplication.scheme_id == application_request.scheme_id,
                    SchemeApplication.status.in_([
                        ApplicationStatus.APPLIED,
                        ApplicationStatus.UNDER_REVIEW,
                        ApplicationStatus.APPROVED
                    ])
                )
            )
        )
        
        if existing_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Application already exists for this scheme"
            )
        
        # Generate application number
        app_number = f"{scheme.scheme_code}/{datetime.now().year}/{holder.state[:2]}/{datetime.now().strftime('%m%d')}/{holder_id[-6:]}"
        
        # Create application
        application = SchemeApplication(
            fra_holder_id=holder.id,
            scheme_id=scheme.id,
            application_number=app_number,
            application_channel=application_request.application_channel,
            status=ApplicationStatus.APPLIED,
            application_data=application_request.application_data,
            submitted_documents=application_request.submitted_documents,
            communication_preferences=application_request.communication_preferences,
            expected_processing_time=30,  # Default 30 days
            audit_trail=[
                {
                    "action": "application_submitted",
                    "timestamp": datetime.utcnow().isoformat(),
                    "user_id": str(current_user.id),
                    "details": "Application submitted successfully"
                }
            ]
        )
        
        db.add(application)
        await db.commit()
        await db.refresh(application)
        
        return ApplicationResponse(
            id=str(application.id),
            application_number=application.application_number,
            scheme_name=scheme.scheme_name,
            status=application.status.value,
            application_date=application.application_date,
            expected_processing_time=application.expected_processing_time,
            assigned_officer=None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Application submission failed: {str(e)}"
        )

@router.get("/applications", response_model=List[ApplicationResponse])
async def list_scheme_applications(
    holder_id: Optional[str] = None,
    scheme_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(100, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List scheme applications"""
    try:
        query = select(SchemeApplication, GovernmentScheme).join(
            GovernmentScheme, SchemeApplication.scheme_id == GovernmentScheme.id
        )
        
        # Apply filters
        if holder_id:
            query = query.where(SchemeApplication.fra_holder_id == holder_id)
        if scheme_id:
            query = query.where(SchemeApplication.scheme_id == scheme_id)
        if status:
            query = query.where(SchemeApplication.status == status)
        
        # Apply role-based filtering for government officials
        if current_user.role.value == "government_official" and current_user.state:
            query = query.join(FRAHolderProfile, SchemeApplication.fra_holder_id == FRAHolderProfile.id)
            query = query.where(FRAHolderProfile.state == current_user.state)
        
        query = query.order_by(desc(SchemeApplication.application_date)).limit(limit)
        
        result = await db.execute(query)
        application_pairs = result.all()
        
        return [
            ApplicationResponse(
                id=str(application.id),
                application_number=application.application_number,
                scheme_name=scheme.scheme_name,
                status=application.status.value,
                application_date=application.application_date,
                expected_processing_time=application.expected_processing_time,
                assigned_officer=str(application.assigned_officer) if application.assigned_officer else None
            )
            for application, scheme in application_pairs
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve applications: {str(e)}"
        )

@router.get("/applications/{application_id}")
async def get_application_details(
    application_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed information about a scheme application"""
    try:
        result = await db.execute(
            select(SchemeApplication, GovernmentScheme, FRAHolderProfile)
            .join(GovernmentScheme, SchemeApplication.scheme_id == GovernmentScheme.id)
            .join(FRAHolderProfile, SchemeApplication.fra_holder_id == FRAHolderProfile.id)
            .where(SchemeApplication.id == application_id)
        )
        
        application_data = result.first()
        if not application_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found"
            )
        
        application, scheme, holder = application_data
        
        return {
            "id": str(application.id),
            "application_number": application.application_number,
            "scheme": {
                "id": str(scheme.id),
                "name": scheme.scheme_name,
                "code": scheme.scheme_code,
                "ministry": scheme.implementing_ministry
            },
            "fra_holder": {
                "id": str(holder.id),
                "name": holder.holder_name,
                "state": holder.state,
                "district": holder.district,
                "village": holder.village
            },
            "status": application.status.value,
            "application_date": application.application_date,
            "application_channel": application.application_channel,
            "application_data": application.application_data,
            "submitted_documents": application.submitted_documents,
            "document_verification_status": application.document_verification_status,
            "assigned_officer": str(application.assigned_officer) if application.assigned_officer else None,
            "processing_office": application.processing_office,
            "expected_processing_time": application.expected_processing_time,
            "decision_date": application.decision_date,
            "decision_remarks": application.decision_remarks,
            "approved_amount": application.approved_amount,
            "disbursement_date": application.disbursement_date,
            "audit_trail": application.audit_trail
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve application details: {str(e)}"
        )

@router.post("/sync-fra-claims")
async def sync_fra_claims_to_profiles(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Sync FRA claims to create holder profiles for scheme assessment"""
    try:
        # Check permissions
        if current_user.role.value not in ["admin", "government_official"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        # Get FRA claims that don't have corresponding holder profiles
        claims_result = await db.execute(
            select(FRAClaim)
            .where(
                ~FRAClaim.id.in_(
                    select(FRAHolderProfile.fra_claim_id)
                    .where(FRAHolderProfile.fra_claim_id.is_not(None))
                )
            )
            .limit(100)  # Process in batches
        )
        
        claims = claims_result.scalars().all()
        
        created_profiles = 0
        for claim in claims:
            # Create holder profile from claim data
            profile_data = create_fra_holder_profile_from_claim(claim)
            
            holder_profile = FRAHolderProfile(
                **profile_data,
                data_source="fra_claim_sync",
                last_verified=datetime.utcnow(),
                verified_by=current_user.id
            )
            
            db.add(holder_profile)
            created_profiles += 1
        
        await db.commit()
        
        return {
            "message": f"Successfully synced {created_profiles} FRA claims to holder profiles",
            "created_profiles": created_profiles,
            "sync_date": datetime.utcnow()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"FRA claims sync failed: {str(e)}"
        )