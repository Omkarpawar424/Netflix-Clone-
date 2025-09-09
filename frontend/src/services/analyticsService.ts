import { api } from './authService';

// Types
export interface ClaimsSummary {
  total_claims: number;
  submitted: number;
  under_review: number;
  approved: number;
  rejected: number;
  title_distributed: number;
  total_area_claimed: number;
  total_area_approved: number;
}

export interface StateSummary {
  state_name: string;
  total_claims: number;
  approval_rate: number;
  total_area_hectares: number;
  tribal_population: number;
  forest_cover_percent: number;
  priority_districts: string[];
}

export interface PerformanceMetrics {
  document_processing_accuracy: number;
  average_claim_processing_time: number;
  system_uptime_percentage: number;
  user_satisfaction_score: number;
  data_quality_score: number;
}

export interface DashboardData {
  summary_stats: {
    claims: ClaimsSummary;
    total_users: number;
    active_sessions: number;
    documents_processed: number;
  };
  recent_activities: Array<{
    type: string;
    description: string;
    timestamp: string;
    location: string;
    status: string;
  }>;
  performance_metrics: PerformanceMetrics;
  geographical_distribution: Array<{
    state: string;
    state_code: string;
    total_claims: number;
    approval_rate: number;
    forest_cover: number;
    tribal_population_percent: number;
  }>;
  trends: {
    claims_trend: {
      current_month: number;
      previous_month: number;
      growth_rate: number;
    };
    approval_trend: {
      current_rate: number;
      previous_rate: number;
      improvement: number;
    };
  };
}

export interface LandUseStatistics {
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
}

export interface CommunityAssetsSummary {
  total_assets_detected: number;
  total_verified: number;
  verification_rate: number;
  asset_type_distribution: Record<string, {
    count: number;
    verified_count: number;
    avg_confidence: number;
    total_area: number;
    verification_rate: number;
  }>;
  detection_methods: {
    satellite_analysis: number;
    field_survey: number;
    community_mapping: number;
  };
  geographic_scope: {
    state?: string;
    district?: string;
  };
}

export interface ChangeDetectionSummary {
  total_changes_detected: number;
  total_area_changed_hectares: number;
  change_type_distribution: Record<string, {
    count: number;
    total_area_hectares: number;
    avg_confidence: number;
    area_percentage: number;
    from_land_uses: Record<string, number>;
    to_land_uses: Record<string, number>;
  }>;
  time_period: {
    start_date?: string;
    end_date?: string;
  };
  geographic_scope: {
    state?: string;
    district?: string;
  };
  analysis_date: string;
}

export interface ReportRequest {
  report_type: string;
  parameters?: Record<string, any>;
  filters?: Record<string, any>;
  format?: string;
}

export interface ReportResponse {
  report_id: string;
  status: string;
  report_type: string;
  generated_at: string;
  data?: any;
  download_url?: string;
}

export interface Report {
  id: string;
  report_name: string;
  report_type: string;
  description?: string;
  parameters: Record<string, any>;
  filters?: Record<string, any>;
  data: any;
  summary_statistics?: Record<string, any>;
  generated_at: string;
  scope_level: string;
  scope_values: string[];
}

export const analyticsService = {
  // Dashboard
  async getDashboardData(filters?: {
    state?: string;
    district?: string;
  }): Promise<DashboardData> {
    const params = new URLSearchParams();
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value) params.append(key, value);
      });
    }
    
    const response = await api.get(`/analytics/dashboard?${params.toString()}`);
    return response.data;
  },

  // Claims Analytics
  async getClaimsSummary(filters?: {
    state?: string;
    district?: string;
    start_date?: string;
    end_date?: string;
  }): Promise<ClaimsSummary> {
    const params = new URLSearchParams();
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value) params.append(key, value);
      });
    }
    
    const response = await api.get(`/analytics/claims-summary?${params.toString()}`);
    return response.data;
  },

  async getStateWiseSummary(): Promise<StateSummary[]> {
    const response = await api.get('/analytics/state-wise-summary');
    return response.data;
  },

  // Performance Metrics
  async getPerformanceMetrics(): Promise<PerformanceMetrics> {
    const response = await api.get('/analytics/performance-metrics');
    return response.data;
  },

  // Land Use Analytics
  async getLandUseStatistics(filters?: {
    state?: string;
    district?: string;
  }): Promise<LandUseStatistics> {
    const params = new URLSearchParams();
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value) params.append(key, value);
      });
    }
    
    const response = await api.get(`/analytics/land-use-statistics?${params.toString()}`);
    return response.data;
  },

  // Community Assets Analytics
  async getCommunityAssetsSummary(filters?: {
    state?: string;
    district?: string;
  }): Promise<CommunityAssetsSummary> {
    const params = new URLSearchParams();
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value) params.append(key, value);
      });
    }
    
    const response = await api.get(`/analytics/community-assets-summary?${params.toString()}`);
    return response.data;
  },

  // Change Detection Analytics
  async getChangeDetectionSummary(filters?: {
    state?: string;
    district?: string;
    start_date?: string;
    end_date?: string;
  }): Promise<ChangeDetectionSummary> {
    const params = new URLSearchParams();
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value) params.append(key, value);
      });
    }
    
    const response = await api.get(`/analytics/change-detection-summary?${params.toString()}`);
    return response.data;
  },

  // Reports
  async generateReport(reportRequest: ReportRequest): Promise<ReportResponse> {
    const response = await api.post('/analytics/reports/generate', reportRequest);
    return response.data;
  },

  async getReport(reportId: string): Promise<Report> {
    const response = await api.get(`/analytics/reports/${reportId}`);
    return response.data;
  },

  async getReportsList(filters?: {
    report_type?: string;
    start_date?: string;
    end_date?: string;
    limit?: number;
  }): Promise<ReportResponse[]> {
    const params = new URLSearchParams();
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined) params.append(key, value.toString());
      });
    }
    
    const response = await api.get(`/analytics/reports?${params.toString()}`);
    return response.data;
  },

  async downloadReport(reportId: string): Promise<Blob> {
    const response = await api.get(`/analytics/reports/${reportId}/download`, {
      responseType: 'blob',
    });
    return response.data;
  },

  // Time Series Data
  async getClaimsTrend(filters?: {
    period?: 'monthly' | 'quarterly' | 'yearly';
    state?: string;
    district?: string;
    start_date?: string;
    end_date?: string;
  }): Promise<Array<{
    period: string;
    total_claims: number;
    approved_claims: number;
    rejected_claims: number;
    pending_claims: number;
  }>> {
    const params = new URLSearchParams();
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value) params.append(key, value);
      });
    }
    
    const response = await api.get(`/analytics/claims-trend?${params.toString()}`);
    return response.data;
  },

  async getProcessingTimeTrend(filters?: {
    period?: 'monthly' | 'quarterly' | 'yearly';
    state?: string;
  }): Promise<Array<{
    period: string;
    avg_processing_time: number;
    median_processing_time: number;
    total_processed: number;
  }>> {
    const params = new URLSearchParams();
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value) params.append(key, value);
      });
    }
    
    const response = await api.get(`/analytics/processing-time-trend?${params.toString()}`);
    return response.data;
  },

  // Comparative Analytics
  async getStateComparison(metrics: string[]): Promise<Array<{
    state: string;
    metrics: Record<string, number>;
  }>> {
    const params = new URLSearchParams();
    metrics.forEach(metric => params.append('metrics', metric));
    
    const response = await api.get(`/analytics/state-comparison?${params.toString()}`);
    return response.data;
  },

  async getDistrictComparison(
    state: string,
    metrics: string[]
  ): Promise<Array<{
    district: string;
    metrics: Record<string, number>;
  }>> {
    const params = new URLSearchParams();
    params.append('state', state);
    metrics.forEach(metric => params.append('metrics', metric));
    
    const response = await api.get(`/analytics/district-comparison?${params.toString()}`);
    return response.data;
  },

  // Custom Analytics
  async getCustomAnalytics(query: {
    dimensions: string[];
    measures: string[];
    filters?: Record<string, any>;
    group_by?: string[];
    order_by?: string;
    limit?: number;
  }): Promise<Array<Record<string, any>>> {
    const response = await api.post('/analytics/custom', query);
    return response.data;
  },

  // Export Functions
  async exportData(
    dataType: string,
    format: 'csv' | 'excel' | 'json',
    filters?: Record<string, any>
  ): Promise<Blob> {
    const response = await api.post('/analytics/export', {
      data_type: dataType,
      format,
      filters,
    }, {
      responseType: 'blob',
    });
    return response.data;
  },

  // Real-time Analytics
  async getRealTimeStats(): Promise<{
    active_users: number;
    processing_queue_size: number;
    recent_uploads: number;
    system_health: 'healthy' | 'warning' | 'critical';
    last_updated: string;
  }> {
    const response = await api.get('/analytics/realtime');
    return response.data;
  },

  // Predictive Analytics
  async getClaimsPrediction(
    horizon_months: number,
    filters?: {
      state?: string;
      district?: string;
    }
  ): Promise<{
    predictions: Array<{
      period: string;
      predicted_claims: number;
      confidence_interval: [number, number];
    }>;
    model_accuracy: number;
    factors: Array<{
      factor: string;
      importance: number;
    }>;
  }> {
    const params = new URLSearchParams();
    params.append('horizon_months', horizon_months.toString());
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value) params.append(key, value);
      });
    }
    
    const response = await api.get(`/analytics/predictions/claims?${params.toString()}`);
    return response.data;
  },
};