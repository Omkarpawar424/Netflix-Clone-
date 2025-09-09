"""
Document processing and FRA claims management API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
import os
from pathlib import Path
import shutil

from app.core.config import settings
from app.core.database import get_db
from app.database.models.user_models import User
from app.database.models.document_models import (
    Document, FRAClaim, FieldVerification, DocumentType, 
    DocumentStatus, ClaimStatus, ProcessingQueue
)
from app.api.auth import get_current_user
from app.ai_models.model_manager import ModelManager

router = APIRouter()

# Pydantic models for request/response
class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    status: str
    message: str

class DocumentInfo(BaseModel):
    id: str
    filename: str
    document_type: str
    status: str
    confidence_score: Optional[float] = None
    upload_date: datetime
    file_size: int

class FRAClaimCreate(BaseModel):
    claim_type: str = Field(..., description="Type of claim: individual, community, community_forest_resource")
    claimant_name: str
    father_husband_name: Optional[str] = None
    caste_tribe: Optional[str] = None
    family_members: Optional[int] = None
    address: Optional[str] = None
    phone_number: Optional[str] = None
    state: str
    district: str
    block: str
    village: str
    forest_division: Optional[str] = None
    forest_range: Optional[str] = None
    survey_number: Optional[str] = None
    area_claimed_hectares: Optional[float] = None
    livelihood_activities: Optional[List[str]] = None
    community_assets: Optional[List[str]] = None
    remarks: Optional[str] = None

class FRAClaimResponse(BaseModel):
    id: str
    claim_number: str
    claim_type: str
    claimant_name: str
    status: str
    state: str
    district: str
    village: str
    area_claimed_hectares: Optional[float] = None
    submission_date: Optional[datetime] = None
    created_at: datetime

class ProcessingResult(BaseModel):
    document_id: str
    status: str
    extracted_text: Optional[str] = None
    document_type: Optional[str] = None
    structured_data: Optional[Dict[str, Any]] = None
    confidence: Optional[float] = None
    processing_time: Optional[str] = None

# Utility functions
def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in settings.ALLOWED_EXTENSIONS

def generate_unique_filename(original_filename: str) -> str:
    """Generate unique filename to avoid conflicts"""
    file_ext = Path(original_filename).suffix
    unique_name = f"{uuid.uuid4()}{file_ext}"
    return unique_name

async def get_model_manager() -> ModelManager:
    """Get model manager instance"""
    # In a real application, this would be injected from the app state
    # For now, we'll create a placeholder
    return ModelManager()

# API Endpoints
@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    document_type: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Upload and process a document"""
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No file selected"
            )
        
        if not allowed_file(file.filename):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type not allowed. Supported types: {settings.ALLOWED_EXTENSIONS}"
            )
        
        # Check file size
        if file.size and file.size > settings.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum size: {settings.MAX_FILE_SIZE / (1024*1024):.1f}MB"
            )
        
        # Create upload directory if it doesn't exist
        upload_dir = Path(settings.UPLOAD_DIR)
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename and save file
        unique_filename = generate_unique_filename(file.filename)
        file_path = upload_dir / unique_filename
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Create document record
        document = Document(
            filename=unique_filename,
            original_filename=file.filename,
            file_path=str(file_path),
            file_size=file_path.stat().st_size,
            mime_type=file.content_type or "application/octet-stream",
            document_type=DocumentType(document_type) if document_type else DocumentType.OTHER,
            status=DocumentStatus.UPLOADED,
            state=current_user.state,
            district=current_user.district,
            uploaded_by=current_user.id
        )
        
        db.add(document)
        await db.commit()
        await db.refresh(document)
        
        # Add to processing queue
        queue_item = ProcessingQueue(
            document_id=document.id,
            job_type="full_processing",
            priority=3
        )
        db.add(queue_item)
        await db.commit()
        
        return DocumentUploadResponse(
            document_id=str(document.id),
            filename=file.filename,
            status="uploaded",
            message="Document uploaded successfully and queued for processing"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        # Clean up file if it was created
        if 'file_path' in locals() and file_path.exists():
            file_path.unlink()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}"
        )

@router.get("/documents", response_model=List[DocumentInfo])
async def list_documents(
    skip: int = 0,
    limit: int = 100,
    document_type: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List documents with filtering options"""
    try:
        query = select(Document)
        
        # Apply role-based filtering
        if current_user.role.value == "tribal_community":
            query = query.where(Document.uploaded_by == current_user.id)
        elif current_user.role.value == "field_worker":
            # Field workers can see documents from their assigned area
            query = query.where(
                and_(
                    Document.state == current_user.state,
                    Document.district == current_user.district
                )
            )
        elif current_user.role.value == "government_official":
            # Government officials can see documents from their state
            if current_user.state:
                query = query.where(Document.state == current_user.state)
        # Admins can see all documents
        
        # Apply filters
        if document_type:
            query = query.where(Document.document_type == document_type)
        
        if status:
            query = query.where(Document.status == status)
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        result = await db.execute(query)
        documents = result.scalars().all()
        
        return [
            DocumentInfo(
                id=str(doc.id),
                filename=doc.original_filename,
                document_type=doc.document_type.value,
                status=doc.status.value,
                confidence_score=doc.confidence_score,
                upload_date=doc.created_at,
                file_size=doc.file_size
            )
            for doc in documents
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve documents: {str(e)}"
        )

@router.get("/documents/{document_id}")
async def get_document_details(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed information about a document"""
    try:
        result = await db.execute(select(Document).where(Document.id == document_id))
        document = result.scalar_one_or_none()
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # Check permissions
        if (current_user.role.value == "tribal_community" and 
            document.uploaded_by != current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        return {
            "id": str(document.id),
            "filename": document.original_filename,
            "document_type": document.document_type.value,
            "status": document.status.value,
            "extracted_text": document.ocr_text,
            "structured_data": document.extracted_entities,
            "confidence_score": document.confidence_score,
            "processing_errors": document.processing_errors,
            "upload_date": document.created_at,
            "processed_date": document.processed_at,
            "file_size": document.file_size,
            "language": document.language,
            "page_count": document.page_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve document details: {str(e)}"
        )

@router.post("/documents/{document_id}/process", response_model=ProcessingResult)
async def process_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Manually trigger document processing"""
    try:
        # Get document
        result = await db.execute(select(Document).where(Document.id == document_id))
        document = result.scalar_one_or_none()
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # Check permissions (only admins and government officials can trigger processing)
        if current_user.role.value not in ["admin", "government_official"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        # Check if already processing
        if document.status == DocumentStatus.PROCESSING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Document is already being processed"
            )
        
        # Update status
        document.status = DocumentStatus.PROCESSING
        document.processed_by = current_user.id
        await db.commit()
        
        # Get model manager and process document
        model_manager = await get_model_manager()
        
        start_time = datetime.utcnow()
        processing_result = await model_manager.process_document(document.file_path)
        end_time = datetime.utcnow()
        
        # Update document with results
        if processing_result.get('status') == 'success':
            document.status = DocumentStatus.PROCESSED
            document.ocr_text = processing_result.get('extracted_text')
            document.extracted_entities = processing_result.get('structured_data')
            document.confidence_score = processing_result.get('overall_confidence')
            document.document_type = DocumentType(processing_result.get('document_type', 'other'))
        else:
            document.status = DocumentStatus.REJECTED
            document.processing_errors = [processing_result.get('error', 'Unknown error')]
        
        document.processed_at = end_time
        await db.commit()
        
        return ProcessingResult(
            document_id=str(document.id),
            status=processing_result.get('status', 'failed'),
            extracted_text=processing_result.get('extracted_text'),
            document_type=processing_result.get('document_type'),
            structured_data=processing_result.get('structured_data'),
            confidence=processing_result.get('overall_confidence'),
            processing_time=str(end_time - start_time)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document processing failed: {str(e)}"
        )

@router.get("/documents/{document_id}/download")
async def download_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Download document file"""
    try:
        result = await db.execute(select(Document).where(Document.id == document_id))
        document = result.scalar_one_or_none()
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # Check permissions
        if (current_user.role.value == "tribal_community" and 
            document.uploaded_by != current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        file_path = Path(document.file_path)
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found on disk"
            )
        
        return FileResponse(
            path=file_path,
            filename=document.original_filename,
            media_type=document.mime_type
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Download failed: {str(e)}"
        )

# FRA Claims endpoints
@router.post("/claims", response_model=FRAClaimResponse)
async def create_fra_claim(
    claim_data: FRAClaimCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new FRA claim"""
    try:
        # Generate claim number
        claim_number = f"{claim_data.state[:2].upper()}/{datetime.now().year}/{uuid.uuid4().hex[:8].upper()}"
        
        # Create claim
        fra_claim = FRAClaim(
            claim_number=claim_number,
            claim_type=claim_data.claim_type,
            claimant_name=claim_data.claimant_name,
            father_husband_name=claim_data.father_husband_name,
            caste_tribe=claim_data.caste_tribe,
            family_members=claim_data.family_members,
            address=claim_data.address,
            phone_number=claim_data.phone_number,
            state=claim_data.state,
            district=claim_data.district,
            block=claim_data.block,
            village=claim_data.village,
            forest_division=claim_data.forest_division,
            forest_range=claim_data.forest_range,
            survey_number=claim_data.survey_number,
            area_claimed_hectares=claim_data.area_claimed_hectares,
            submission_date=datetime.utcnow(),
            livelihood_activities=claim_data.livelihood_activities,
            community_assets=claim_data.community_assets,
            remarks=claim_data.remarks,
            status=ClaimStatus.SUBMITTED
        )
        
        db.add(fra_claim)
        await db.commit()
        await db.refresh(fra_claim)
        
        return FRAClaimResponse(
            id=str(fra_claim.id),
            claim_number=fra_claim.claim_number,
            claim_type=fra_claim.claim_type,
            claimant_name=fra_claim.claimant_name,
            status=fra_claim.status.value,
            state=fra_claim.state,
            district=fra_claim.district,
            village=fra_claim.village,
            area_claimed_hectares=fra_claim.area_claimed_hectares,
            submission_date=fra_claim.submission_date,
            created_at=fra_claim.created_at
        )
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create FRA claim: {str(e)}"
        )

@router.get("/claims", response_model=List[FRAClaimResponse])
async def list_fra_claims(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    state: Optional[str] = None,
    district: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List FRA claims with filtering"""
    try:
        query = select(FRAClaim)
        
        # Apply role-based filtering
        if current_user.role.value == "tribal_community":
            # Tribal community members can only see claims from their area
            query = query.where(
                and_(
                    FRAClaim.state == current_user.state,
                    FRAClaim.district == current_user.district,
                    FRAClaim.village == current_user.village
                )
            )
        elif current_user.role.value == "field_worker":
            query = query.where(
                and_(
                    FRAClaim.state == current_user.state,
                    FRAClaim.district == current_user.district
                )
            )
        elif current_user.role.value == "government_official":
            if current_user.state:
                query = query.where(FRAClaim.state == current_user.state)
        
        # Apply additional filters
        if status:
            query = query.where(FRAClaim.status == status)
        if state:
            query = query.where(FRAClaim.state == state)
        if district:
            query = query.where(FRAClaim.district == district)
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        result = await db.execute(query)
        claims = result.scalars().all()
        
        return [
            FRAClaimResponse(
                id=str(claim.id),
                claim_number=claim.claim_number,
                claim_type=claim.claim_type,
                claimant_name=claim.claimant_name,
                status=claim.status.value,
                state=claim.state,
                district=claim.district,
                village=claim.village,
                area_claimed_hectares=claim.area_claimed_hectares,
                submission_date=claim.submission_date,
                created_at=claim.created_at
            )
            for claim in claims
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve FRA claims: {str(e)}"
        )

@router.get("/claims/{claim_id}")
async def get_fra_claim_details(
    claim_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed information about an FRA claim"""
    try:
        result = await db.execute(select(FRAClaim).where(FRAClaim.id == claim_id))
        claim = result.scalar_one_or_none()
        
        if not claim:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="FRA claim not found"
            )
        
        # Check permissions
        if (current_user.role.value == "tribal_community" and 
            current_user.state != claim.state):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Get associated documents and verifications
        doc_result = await db.execute(
            select(Document).where(Document.fra_claims.any(FRAClaim.id == claim_id))
        )
        documents = doc_result.scalars().all()
        
        verification_result = await db.execute(
            select(FieldVerification).where(FieldVerification.fra_claim_id == claim_id)
        )
        verifications = verification_result.scalars().all()
        
        return {
            "id": str(claim.id),
            "claim_number": claim.claim_number,
            "claim_type": claim.claim_type,
            "status": claim.status.value,
            "claimant_name": claim.claimant_name,
            "father_husband_name": claim.father_husband_name,
            "caste_tribe": claim.caste_tribe,
            "family_members": claim.family_members,
            "address": claim.address,
            "phone_number": claim.phone_number,
            "state": claim.state,
            "district": claim.district,
            "block": claim.block,
            "village": claim.village,
            "forest_division": claim.forest_division,
            "forest_range": claim.forest_range,
            "survey_number": claim.survey_number,
            "area_claimed_hectares": claim.area_claimed_hectares,
            "area_verified_hectares": claim.area_verified_hectares,
            "area_approved_hectares": claim.area_approved_hectares,
            "submission_date": claim.submission_date,
            "verification_date": claim.verification_date,
            "approval_date": claim.approval_date,
            "title_distribution_date": claim.title_distribution_date,
            "livelihood_activities": claim.livelihood_activities,
            "community_assets": claim.community_assets,
            "remarks": claim.remarks,
            "title_number": claim.title_number,
            "documents": [
                {
                    "id": str(doc.id),
                    "filename": doc.original_filename,
                    "type": doc.document_type.value,
                    "status": doc.status.value
                }
                for doc in documents
            ],
            "field_verifications": [
                {
                    "id": str(ver.id),
                    "verification_date": ver.verification_date,
                    "result": ver.verification_result,
                    "measured_area": ver.measured_area_hectares
                }
                for ver in verifications
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve FRA claim details: {str(e)}"
        )