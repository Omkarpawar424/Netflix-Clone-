import { api } from './authService';

// Types
export interface LayerInfo {
  id: string;
  name: string;
  display_name: string;
  layer_type: string;
  is_published: boolean;
  is_public: boolean;
  data_date?: string;
  description?: string;
}

export interface LayerDetails extends LayerInfo {
  geometry_type?: string;
  default_style?: any;
  bounding_box?: any;
  feature_count?: number;
}

export interface Feature {
  type: 'Feature';
  id: string;
  geometry: any;
  properties: any;
}

export interface FeatureCollection {
  type: 'FeatureCollection';
  features: Feature[];
  total_count?: number;
}

export interface SatelliteImageInfo {
  id: string;
  image_id: string;
  satellite_name: string;
  sensor: string;
  acquisition_date: string;
  cloud_cover_percentage?: number;
  resolution_meters: number;
  processing_level: string;
  states_covered: string[];
}

export interface CommunityAsset {
  id: string;
  asset_name: string;
  asset_type: string;
  location: {
    lat: number;
    lng: number;
  };
  confidence: number;
  detection_method: string;
  detected_at: string;
  is_verified: boolean;
}

export interface AnalysisRequest {
  image_path: string;
  analysis_type: string;
  parameters?: any;
}

export interface AnalysisResult {
  analysis_id: string;
  status: string;
  image_path: string;
  analysis_type: string;
  results?: any;
  processing_time?: string;
}

export interface VillageBoundary {
  type: 'Feature';
  id: string;
  geometry: any;
  properties: {
    village_name: string;
    village_code?: string;
    block_name: string;
    district_name: string;
    state_name: string;
    area_hectares: number;
    population?: number;
    tribal_population?: number;
    total_fra_claims?: number;
    approved_fra_claims?: number;
    centroid?: any;
  };
}

export interface ChangeDetectionResult {
  id: string;
  change_type: string;
  from_land_use: string;
  to_land_use: string;
  area_changed_hectares: number;
  change_percentage: number;
  confidence_score: number;
  start_date: string;
  end_date: string;
  state: string;
  district: string;
  geometry: any;
  change_drivers?: string[];
  impact_assessment?: any;
  recommendations?: string;
  processed_at: string;
  is_verified: boolean;
}

export const gisService = {
  // Layers
  async getLayers(layerType?: string, isPublic?: boolean): Promise<LayerInfo[]> {
    const params = new URLSearchParams();
    if (layerType) params.append('layer_type', layerType);
    if (isPublic !== undefined) params.append('is_public', isPublic.toString());
    
    const response = await api.get(`/gis/layers?${params.toString()}`);
    return response.data;
  },

  async getLayerDetails(layerId: string): Promise<LayerDetails> {
    const response = await api.get(`/gis/layers/${layerId}`);
    return response.data;
  },

  async getLayerFeatures(
    layerId: string,
    bbox?: string,
    limit?: number,
    offset?: number
  ): Promise<FeatureCollection> {
    const params = new URLSearchParams();
    if (bbox) params.append('bbox', bbox);
    if (limit) params.append('limit', limit.toString());
    if (offset) params.append('offset', offset.toString());
    
    const response = await api.get(`/gis/layers/${layerId}/features?${params.toString()}`);
    return response.data;
  },

  // Satellite Images
  async getSatelliteImages(filters?: {
    state?: string;
    start_date?: string;
    end_date?: string;
    max_cloud_cover?: number;
    limit?: number;
  }): Promise<SatelliteImageInfo[]> {
    const params = new URLSearchParams();
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined) {
          params.append(key, value.toString());
        }
      });
    }
    
    const response = await api.get(`/gis/satellite-images?${params.toString()}`);
    return response.data;
  },

  async analyzeSatelliteImage(
    imageId: string,
    analysisRequest: AnalysisRequest
  ): Promise<AnalysisResult> {
    const response = await api.post(`/gis/satellite-images/${imageId}/analyze`, analysisRequest);
    return response.data;
  },

  // Community Assets
  async getCommunityAssets(filters?: {
    state?: string;
    district?: string;
    asset_types?: string[];
    verified_only?: boolean;
    limit?: number;
  }): Promise<CommunityAsset[]> {
    const params = new URLSearchParams();
    if (filters) {
      if (filters.state) params.append('state', filters.state);
      if (filters.district) params.append('district', filters.district);
      if (filters.asset_types) {
        filters.asset_types.forEach(type => params.append('asset_type', type));
      }
      if (filters.verified_only !== undefined) {
        params.append('verified_only', filters.verified_only.toString());
      }
      if (filters.limit) params.append('limit', filters.limit.toString());
    }
    
    const response = await api.get(`/gis/community-assets?${params.toString()}`);
    return response.data;
  },

  async verifyAsset(assetId: string, verificationData: {
    is_verified: boolean;
    notes?: string;
    asset_name?: string;
    condition_assessment?: string;
    ownership_type?: string;
  }): Promise<{ message: string }> {
    const response = await api.put(`/gis/community-assets/${assetId}/verify`, verificationData);
    return response.data;
  },

  // Village Boundaries
  async getVillageBoundary(
    villageName: string,
    state: string,
    district: string
  ): Promise<VillageBoundary> {
    const params = new URLSearchParams({
      state,
      district,
    });
    
    const response = await api.get(`/gis/villages/${encodeURIComponent(villageName)}/boundary?${params.toString()}`);
    return response.data;
  },

  // Change Detection
  async getChangeDetection(filters?: {
    state?: string;
    district?: string;
    change_type?: string;
    start_date?: string;
    end_date?: string;
    min_area?: number;
    limit?: number;
  }): Promise<ChangeDetectionResult[]> {
    const params = new URLSearchParams();
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined) {
          params.append(key, value.toString());
        }
      });
    }
    
    const response = await api.get(`/gis/change-detection?${params.toString()}`);
    return response.data;
  },

  // Utility functions
  async uploadShapefile(file: File): Promise<{ layer_id: string; message: string }> {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await api.post('/gis/upload/shapefile', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  async exportLayer(layerId: string, format: string = 'geojson'): Promise<Blob> {
    const response = await api.get(`/gis/layers/${layerId}/export`, {
      params: { format },
      responseType: 'blob',
    });
    return response.data;
  },

  // Spatial Analysis
  async performSpatialAnalysis(analysisType: string, parameters: any): Promise<any> {
    const response = await api.post('/gis/analysis/spatial', {
      analysis_type: analysisType,
      parameters,
    });
    return response.data;
  },

  async getBufferAnalysis(
    geometry: any,
    distance: number,
    units: string = 'meters'
  ): Promise<any> {
    const response = await api.post('/gis/analysis/buffer', {
      geometry,
      distance,
      units,
    });
    return response.data;
  },

  async getIntersectionAnalysis(
    layer1Id: string,
    layer2Id: string
  ): Promise<any> {
    const response = await api.post('/gis/analysis/intersection', {
      layer1_id: layer1Id,
      layer2_id: layer2Id,
    });
    return response.data;
  },

  // Statistics
  async getLayerStatistics(layerId: string): Promise<{
    feature_count: number;
    area_statistics?: any;
    attribute_statistics?: any;
    spatial_extent?: any;
  }> {
    const response = await api.get(`/gis/layers/${layerId}/statistics`);
    return response.data;
  },

  async getLandUseStatistics(filters?: {
    state?: string;
    district?: string;
  }): Promise<{
    total_area_analyzed: number;
    land_use_distribution: Record<string, {
      area_hectares: number;
      percentage: number;
      count: number;
      avg_confidence: number;
    }>;
    analysis_date: string;
    geographic_scope: {
      state?: string;
      district?: string;
    };
  }> {
    const params = new URLSearchParams();
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value) params.append(key, value);
      });
    }
    
    const response = await api.get(`/gis/land-use-statistics?${params.toString()}`);
    return response.data;
  },
};