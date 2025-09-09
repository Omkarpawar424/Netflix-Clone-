"""
GIS and mapping API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
import json
import asyncio

from app.core.config import settings
from app.core.database import get_db
from app.database.models.user_models import User
from app.database.models.gis_models import (
    GISLayer, GISFeature, SatelliteImage, LandUseClassification,
    CommunityAsset, VillageBoundary, ChangeDetection
)
from app.api.auth import get_current_user
from app.ai_models.model_manager import ModelManager

router = APIRouter()

# Pydantic models for request/response
class LayerInfo(BaseModel):
    id: str
    name: str
    display_name: str
    layer_type: str
    is_published: bool
    is_public: bool
    data_date: Optional[datetime] = None

class LayerDetails(BaseModel):
    id: str
    name: str
    display_name: str
    description: Optional[str] = None
    layer_type: str
    geometry_type: Optional[str] = None
    default_style: Optional[Dict[str, Any]] = None
    bounding_box: Optional[Dict[str, Any]] = None
    feature_count: Optional[int] = None

class FeatureCollection(BaseModel):
    type: str = "FeatureCollection"
    features: List[Dict[str, Any]]
    total_count: Optional[int] = None

class SatelliteImageInfo(BaseModel):
    id: str
    image_id: str
    satellite_name: str
    sensor: str
    acquisition_date: datetime
    cloud_cover_percentage: Optional[float] = None
    resolution_meters: float
    processing_level: str
    states_covered: List[str]

class AnalysisRequest(BaseModel):
    image_path: str
    analysis_type: str = Field(..., description="Type of analysis: classification, assets, full")
    parameters: Optional[Dict[str, Any]] = None

class AnalysisResult(BaseModel):
    analysis_id: str
    status: str
    image_path: str
    analysis_type: str
    results: Optional[Dict[str, Any]] = None
    processing_time: Optional[str] = None

class AssetDetection(BaseModel):
    id: str
    asset_name: str
    asset_type: str
    location: Dict[str, float]  # lat, lng
    confidence: float
    detection_method: str
    detected_at: datetime
    is_verified: bool

# Utility functions
def geojson_to_dict(geom) -> Optional[Dict[str, Any]]:
    """Convert PostGIS geometry to GeoJSON dict"""
    if geom is None:
        return None
    try:
        # In a real implementation, this would use proper PostGIS functions
        # For now, return a placeholder
        return {
            "type": "Point",
            "coordinates": [0.0, 0.0]
        }
    except Exception:
        return None

async def get_model_manager() -> ModelManager:
    """Get model manager instance"""
    return ModelManager()

# API Endpoints
@router.get("/layers", response_model=List[LayerInfo])
async def list_gis_layers(
    layer_type: Optional[str] = None,
    is_public: Optional[bool] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List available GIS layers"""
    try:
        query = select(GISLayer)
        
        # Apply role-based filtering
        if current_user.role.value not in ["admin", "government_official"]:
            query = query.where(GISLayer.is_public == True)
        
        # Apply filters
        if layer_type:
            query = query.where(GISLayer.layer_type == layer_type)
        if is_public is not None:
            query = query.where(GISLayer.is_public == is_public)
        
        result = await db.execute(query)
        layers = result.scalars().all()
        
        return [
            LayerInfo(
                id=str(layer.id),
                name=layer.name,
                display_name=layer.display_name,
                layer_type=layer.layer_type.value,
                is_published=layer.is_published,
                is_public=layer.is_public,
                data_date=layer.data_date
            )
            for layer in layers
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve layers: {str(e)}"
        )

@router.get("/layers/{layer_id}", response_model=LayerDetails)
async def get_layer_details(
    layer_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed information about a GIS layer"""
    try:
        result = await db.execute(select(GISLayer).where(GISLayer.id == layer_id))
        layer = result.scalar_one_or_none()
        
        if not layer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Layer not found"
            )
        
        # Check permissions
        if not layer.is_public and current_user.role.value not in ["admin", "government_official"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Get feature count
        feature_count_result = await db.execute(
            select(func.count(GISFeature.id)).where(GISFeature.layer_id == layer_id)
        )
        feature_count = feature_count_result.scalar()
        
        return LayerDetails(
            id=str(layer.id),
            name=layer.name,
            display_name=layer.display_name,
            description=layer.description,
            layer_type=layer.layer_type.value,
            geometry_type=layer.geometry_type,
            default_style=layer.default_style,
            bounding_box=geojson_to_dict(layer.bounding_box),
            feature_count=feature_count
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve layer details: {str(e)}"
        )

@router.get("/layers/{layer_id}/features", response_model=FeatureCollection)
async def get_layer_features(
    layer_id: str,
    bbox: Optional[str] = Query(None, description="Bounding box: minx,miny,maxx,maxy"),
    limit: int = Query(1000, le=5000),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get features from a GIS layer"""
    try:
        # Check layer exists and permissions
        layer_result = await db.execute(select(GISLayer).where(GISLayer.id == layer_id))
        layer = layer_result.scalar_one_or_none()
        
        if not layer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Layer not found"
            )
        
        if not layer.is_public and current_user.role.value not in ["admin", "government_official"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Build query
        query = select(GISFeature).where(GISFeature.layer_id == layer_id)
        
        # Apply bounding box filter if provided
        if bbox:
            try:
                minx, miny, maxx, maxy = map(float, bbox.split(','))
                # In a real implementation, this would use PostGIS spatial functions
                # query = query.where(func.ST_Intersects(GISFeature.geometry, func.ST_MakeEnvelope(minx, miny, maxx, maxy, 4326)))
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid bounding box format"
                )
        
        # Apply pagination
        query = query.offset(offset).limit(limit)
        
        # Get total count
        count_query = select(func.count(GISFeature.id)).where(GISFeature.layer_id == layer_id)
        total_count_result = await db.execute(count_query)
        total_count = total_count_result.scalar()
        
        # Execute query
        result = await db.execute(query)
        features = result.scalars().all()
        
        # Convert to GeoJSON features
        geojson_features = []
        for feature in features:
            geojson_features.append({
                "type": "Feature",
                "id": str(feature.id),
                "geometry": geojson_to_dict(feature.geometry),
                "properties": {
                    **feature.properties,
                    "feature_id": feature.feature_id,
                    "name": feature.name,
                    "state": feature.state,
                    "district": feature.district,
                    "collection_date": feature.collection_date.isoformat() if feature.collection_date else None
                }
            })
        
        return FeatureCollection(
            features=geojson_features,
            total_count=total_count
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve features: {str(e)}"
        )

@router.get("/satellite-images", response_model=List[SatelliteImageInfo])
async def list_satellite_images(
    state: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    max_cloud_cover: Optional[float] = Query(None, le=100),
    limit: int = Query(100, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List available satellite images"""
    try:
        query = select(SatelliteImage)
        
        # Apply filters
        if state:
            query = query.where(SatelliteImage.states_covered.contains([state]))
        
        if start_date:
            query = query.where(SatelliteImage.acquisition_date >= start_date)
        
        if end_date:
            query = query.where(SatelliteImage.acquisition_date <= end_date)
        
        if max_cloud_cover is not None:
            query = query.where(
                or_(
                    SatelliteImage.cloud_cover_percentage.is_(None),
                    SatelliteImage.cloud_cover_percentage <= max_cloud_cover
                )
            )
        
        # Order by acquisition date (newest first)
        query = query.order_by(SatelliteImage.acquisition_date.desc()).limit(limit)
        
        result = await db.execute(query)
        images = result.scalars().all()
        
        return [
            SatelliteImageInfo(
                id=str(image.id),
                image_id=image.image_id,
                satellite_name=image.satellite_name,
                sensor=image.sensor,
                acquisition_date=image.acquisition_date,
                cloud_cover_percentage=image.cloud_cover_percentage,
                resolution_meters=image.resolution_meters,
                processing_level=image.processing_level,
                states_covered=image.states_covered
            )
            for image in images
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve satellite images: {str(e)}"
        )

@router.post("/satellite-images/{image_id}/analyze", response_model=AnalysisResult)
async def analyze_satellite_image(
    image_id: str,
    analysis_request: AnalysisRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Analyze satellite image using AI models"""
    try:
        # Check if user has permission to run analysis
        if current_user.role.value not in ["admin", "government_official", "field_worker"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions for satellite analysis"
            )
        
        # Get satellite image
        result = await db.execute(select(SatelliteImage).where(SatelliteImage.id == image_id))
        image = result.scalar_one_or_none()
        
        if not image:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Satellite image not found"
            )
        
        # Get model manager and run analysis
        model_manager = await get_model_manager()
        
        start_time = datetime.utcnow()
        analysis_result = await model_manager.analyze_satellite_image(
            image.file_path, 
            analysis_request.analysis_type
        )
        end_time = datetime.utcnow()
        
        # Store analysis results in database if successful
        if analysis_result.get('status') != 'failed':
            # Store land use classifications
            if 'land_use_classification' in analysis_result:
                for classification in analysis_result['land_use_classification']:
                    land_use_record = LandUseClassification(
                        satellite_image_id=image.id,
                        classification_method="ensemble",
                        model_name="cnn_rf_ensemble",
                        model_version="1.0",
                        geometry=None,  # Would need proper geometry
                        land_use_class=classification.get('predicted_class', 'unknown'),
                        confidence_score=classification.get('confidence', 0.0),
                        area_hectares=100.0,  # Placeholder
                        processed_at=end_time
                    )
                    db.add(land_use_record)
            
            # Store community assets
            if 'community_assets' in analysis_result:
                for asset in analysis_result['community_assets']:
                    asset_record = CommunityAsset(
                        asset_name=f"{asset.get('asset_type', 'Unknown')} Asset",
                        asset_type=asset.get('asset_type', 'unknown'),
                        geometry=None,  # Would need proper geometry
                        state=image.states_covered[0] if image.states_covered else "Unknown",
                        district="Unknown",
                        block="Unknown", 
                        village="Unknown",
                        detection_method="satellite_analysis",
                        detection_confidence=asset.get('confidence', 0.0),
                        estimated_area_sqm=asset.get('area', 0.0),
                        detected_at=end_time
                    )
                    db.add(asset_record)
            
            await db.commit()
        
        return AnalysisResult(
            analysis_id=str(image.id),
            status=analysis_result.get('status', 'failed'),
            image_path=image.file_path,
            analysis_type=analysis_request.analysis_type,
            results=analysis_result,
            processing_time=str(end_time - start_time)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Satellite image analysis failed: {str(e)}"
        )

@router.get("/community-assets", response_model=List[AssetDetection])
async def list_community_assets(
    state: Optional[str] = None,
    district: Optional[str] = None,
    asset_type: Optional[str] = None,
    verified_only: bool = False,
    limit: int = Query(100, le=1000),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List detected community assets"""
    try:
        query = select(CommunityAsset)
        
        # Apply role-based filtering
        if current_user.role.value == "tribal_community":
            query = query.where(
                and_(
                    CommunityAsset.state == current_user.state,
                    CommunityAsset.district == current_user.district
                )
            )
        elif current_user.role.value == "field_worker":
            query = query.where(
                and_(
                    CommunityAsset.state == current_user.state,
                    CommunityAsset.district == current_user.district
                )
            )
        elif current_user.role.value == "government_official":
            if current_user.state:
                query = query.where(CommunityAsset.state == current_user.state)
        
        # Apply filters
        if state:
            query = query.where(CommunityAsset.state == state)
        if district:
            query = query.where(CommunityAsset.district == district)
        if asset_type:
            query = query.where(CommunityAsset.asset_type == asset_type)
        if verified_only:
            query = query.where(CommunityAsset.is_verified == True)
        
        query = query.order_by(CommunityAsset.detected_at.desc()).limit(limit)
        
        result = await db.execute(query)
        assets = result.scalars().all()
        
        return [
            AssetDetection(
                id=str(asset.id),
                asset_name=asset.asset_name,
                asset_type=asset.asset_type,
                location={"lat": 0.0, "lng": 0.0},  # Would extract from geometry
                confidence=asset.detection_confidence,
                detection_method=asset.detection_method,
                detected_at=asset.detected_at,
                is_verified=asset.is_verified
            )
            for asset in assets
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve community assets: {str(e)}"
        )

@router.put("/community-assets/{asset_id}/verify")
async def verify_community_asset(
    asset_id: str,
    verification_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Verify a community asset detection"""
    try:
        # Check permissions
        if current_user.role.value not in ["admin", "government_official", "field_worker"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to verify assets"
            )
        
        # Get asset
        result = await db.execute(select(CommunityAsset).where(CommunityAsset.id == asset_id))
        asset = result.scalar_one_or_none()
        
        if not asset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Community asset not found"
            )
        
        # Update verification status
        asset.is_verified = verification_data.get('is_verified', True)
        asset.verified_by = current_user.id
        asset.verification_date = datetime.utcnow()
        asset.verification_notes = verification_data.get('notes')
        
        # Update asset properties if provided
        if 'asset_name' in verification_data:
            asset.asset_name = verification_data['asset_name']
        if 'condition_assessment' in verification_data:
            asset.condition_assessment = verification_data['condition_assessment']
        if 'ownership_type' in verification_data:
            asset.ownership_type = verification_data['ownership_type']
        
        await db.commit()
        
        return {"message": "Asset verification updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Asset verification failed: {str(e)}"
        )

@router.get("/villages/{village_name}/boundary")
async def get_village_boundary(
    village_name: str,
    state: str,
    district: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get village boundary geometry"""
    try:
        result = await db.execute(
            select(VillageBoundary).where(
                and_(
                    VillageBoundary.village_name == village_name,
                    VillageBoundary.state_name == state,
                    VillageBoundary.district_name == district
                )
            )
        )
        village = result.scalar_one_or_none()
        
        if not village:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Village boundary not found"
            )
        
        return {
            "type": "Feature",
            "id": str(village.id),
            "geometry": geojson_to_dict(village.boundary),
            "properties": {
                "village_name": village.village_name,
                "village_code": village.village_code,
                "block_name": village.block_name,
                "district_name": village.district_name,
                "state_name": village.state_name,
                "area_hectares": village.area_hectares,
                "population": village.population,
                "tribal_population": village.tribal_population,
                "total_fra_claims": village.total_fra_claims,
                "approved_fra_claims": village.approved_fra_claims,
                "centroid": geojson_to_dict(village.centroid)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve village boundary: {str(e)}"
        )

@router.get("/change-detection")
async def get_change_detection_results(
    state: Optional[str] = None,
    district: Optional[str] = None,
    change_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    min_area: Optional[float] = None,
    limit: int = Query(100, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get land use change detection results"""
    try:
        query = select(ChangeDetection)
        
        # Apply role-based filtering
        if current_user.role.value == "government_official" and current_user.state:
            query = query.where(ChangeDetection.state == current_user.state)
        
        # Apply filters
        if state:
            query = query.where(ChangeDetection.state == state)
        if district:
            query = query.where(ChangeDetection.district == district)
        if change_type:
            query = query.where(ChangeDetection.change_type == change_type)
        if start_date:
            query = query.where(ChangeDetection.start_date >= start_date)
        if end_date:
            query = query.where(ChangeDetection.end_date <= end_date)
        if min_area:
            query = query.where(ChangeDetection.area_changed_hectares >= min_area)
        
        query = query.order_by(ChangeDetection.processed_at.desc()).limit(limit)
        
        result = await db.execute(query)
        changes = result.scalars().all()
        
        change_results = []
        for change in changes:
            change_results.append({
                "id": str(change.id),
                "change_type": change.change_type,
                "from_land_use": change.from_land_use,
                "to_land_use": change.to_land_use,
                "area_changed_hectares": change.area_changed_hectares,
                "change_percentage": change.change_percentage,
                "confidence_score": change.confidence_score,
                "start_date": change.start_date,
                "end_date": change.end_date,
                "state": change.state,
                "district": change.district,
                "geometry": geojson_to_dict(change.geometry),
                "change_drivers": change.change_drivers,
                "impact_assessment": change.impact_assessment,
                "recommendations": change.recommendations,
                "processed_at": change.processed_at,
                "is_verified": change.is_verified
            })
        
        return change_results
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve change detection results: {str(e)}"
        )