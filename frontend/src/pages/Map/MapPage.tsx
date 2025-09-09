import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Paper,
  Typography,
  Grid,
  Card,
  CardContent,
  Button,
  IconButton,
  Drawer,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Switch,
  FormControlLabel,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  MenuItem,
  Fab,
  Tooltip,
  Alert,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from '@mui/material';
import {
  Layers as LayersIcon,
  Satellite as SatelliteIcon,
  Forest as ForestIcon,
  Home as HomeIcon,
  Water as WaterIcon,
  Agriculture as AgricultureIcon,
  Close as CloseIcon,
  Info as InfoIcon,
  Settings as SettingsIcon,
  Fullscreen as FullscreenIcon,
  MyLocation as MyLocationIcon,
  Search as SearchIcon,
  FilterList as FilterIcon,
  ExpandMore as ExpandMoreIcon,
  Visibility as VisibilityIcon,
  VisibilityOff as VisibilityOffIcon,
} from '@mui/icons-material';
import { MapContainer, TileLayer, Marker, Popup, GeoJSON, useMap } from 'react-leaflet';
import L from 'leaflet';
import { Helmet } from 'react-helmet-async';
import { useQuery } from 'react-query';
import toast from 'react-hot-toast';

// Services
import { gisService, LayerInfo, FeatureCollection, CommunityAsset } from '../../services/gisService';
import { useAuth } from '../../contexts/AuthContext';

// Fix for default markers
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: require('leaflet/dist/images/marker-icon-2x.png'),
  iconUrl: require('leaflet/dist/images/marker-icon.png'),
  shadowUrl: require('leaflet/dist/images/marker-shadow.png'),
});

// Custom icons for different asset types
const createCustomIcon = (color: string, icon: string) => {
  return L.divIcon({
    html: `<div style="background-color: ${color}; width: 20px; height: 20px; border-radius: 50%; display: flex; align-items: center; justify-content: center; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);"><span style="color: white; font-size: 10px;">${icon}</span></div>`,
    className: 'custom-div-icon',
    iconSize: [20, 20],
    iconAnchor: [10, 10],
  });
};

const assetIcons = {
  house: createCustomIcon('#2E7D32', '🏠'),
  water_body: createCustomIcon('#1976D2', '💧'),
  agricultural_field: createCustomIcon('#FF8F00', '🌾'),
  temple: createCustomIcon('#9C27B0', '🛕'),
  school: createCustomIcon('#F44336', '🏫'),
  default: createCustomIcon('#757575', '📍'),
};

// Map Controls Component
const MapControls: React.FC<{
  onFullscreen: () => void;
  onMyLocation: () => void;
  onSearch: () => void;
}> = ({ onFullscreen, onMyLocation, onSearch }) => {
  return (
    <Box
      sx={{
        position: 'absolute',
        top: 10,
        right: 10,
        zIndex: 1000,
        display: 'flex',
        flexDirection: 'column',
        gap: 1,
      }}
    >
      <Tooltip title="Search Location">
        <Fab size="small" color="primary" onClick={onSearch}>
          <SearchIcon />
        </Fab>
      </Tooltip>
      <Tooltip title="My Location">
        <Fab size="small" color="primary" onClick={onMyLocation}>
          <MyLocationIcon />
        </Fab>
      </Tooltip>
      <Tooltip title="Fullscreen">
        <Fab size="small" color="primary" onClick={onFullscreen}>
          <FullscreenIcon />
        </Fab>
      </Tooltip>
    </Box>
  );
};

// Layer Control Component
const LayerControl: React.FC<{
  layers: LayerInfo[];
  visibleLayers: Set<string>;
  onLayerToggle: (layerId: string) => void;
  onLayerInfo: (layer: LayerInfo) => void;
}> = ({ layers, visibleLayers, onLayerToggle, onLayerInfo }) => {
  return (
    <List dense>
      {layers.map((layer) => (
        <ListItem key={layer.id} divider>
          <ListItemIcon>
            {layer.layer_type === 'vector' ? <LayersIcon /> : <SatelliteIcon />}
          </ListItemIcon>
          <ListItemText
            primary={layer.display_name}
            secondary={`${layer.layer_type} • ${layer.data_date ? new Date(layer.data_date).toLocaleDateString() : 'No date'}`}
          />
          <IconButton
            size="small"
            onClick={() => onLayerInfo(layer)}
            sx={{ mr: 1 }}
          >
            <InfoIcon fontSize="small" />
          </IconButton>
          <Switch
            checked={visibleLayers.has(layer.id)}
            onChange={() => onLayerToggle(layer.id)}
            size="small"
          />
        </ListItem>
      ))}
    </List>
  );
};

// Asset Filter Component
const AssetFilter: React.FC<{
  assetTypes: string[];
  selectedTypes: Set<string>;
  onTypeToggle: (type: string) => void;
  verifiedOnly: boolean;
  onVerifiedToggle: (checked: boolean) => void;
}> = ({ assetTypes, selectedTypes, onTypeToggle, verifiedOnly, onVerifiedToggle }) => {
  return (
    <Box sx={{ p: 2 }}>
      <Typography variant="subtitle2" gutterBottom>
        Asset Types
      </Typography>
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2 }}>
        {assetTypes.map((type) => (
          <Chip
            key={type}
            label={type.replace('_', ' ')}
            variant={selectedTypes.has(type) ? 'filled' : 'outlined'}
            onClick={() => onTypeToggle(type)}
            size="small"
            sx={{ textTransform: 'capitalize' }}
          />
        ))}
      </Box>
      <FormControlLabel
        control={
          <Switch
            checked={verifiedOnly}
            onChange={(e) => onVerifiedToggle(e.target.checked)}
            size="small"
          />
        }
        label="Verified Only"
      />
    </Box>
  );
};

// Main Map Page Component
const MapPage: React.FC = () => {
  const { user } = useAuth();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [visibleLayers, setVisibleLayers] = useState<Set<string>>(new Set());
  const [selectedAssetTypes, setSelectedAssetTypes] = useState<Set<string>>(new Set(['house', 'water_body', 'agricultural_field']));
  const [verifiedOnly, setVerifiedOnly] = useState(false);
  const [layerInfoDialog, setLayerInfoDialog] = useState<LayerInfo | null>(null);
  const [searchDialog, setSearchDialog] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [mapCenter, setMapCenter] = useState<[number, number]>([20.5937, 78.9629]); // India center
  const [mapZoom, setMapZoom] = useState(5);

  // Fetch GIS layers
  const { data: layers = [], isLoading: layersLoading } = useQuery(
    'gis-layers',
    () => gisService.getLayers(),
    {
      onError: (error: any) => {
        toast.error('Failed to load GIS layers');
        console.error('Layers error:', error);
      },
    }
  );

  // Fetch community assets
  const { data: assets = [], isLoading: assetsLoading } = useQuery(
    ['community-assets', user?.state, user?.district, Array.from(selectedAssetTypes), verifiedOnly],
    () => gisService.getCommunityAssets({
      state: user?.state,
      district: user?.district,
      asset_types: Array.from(selectedAssetTypes),
      verified_only: verifiedOnly,
    }),
    {
      enabled: selectedAssetTypes.size > 0,
      onError: (error: any) => {
        toast.error('Failed to load community assets');
        console.error('Assets error:', error);
      },
    }
  );

  // Get unique asset types from data
  const availableAssetTypes = React.useMemo(() => {
    const types = new Set<string>();
    assets.forEach(asset => types.add(asset.asset_type));
    return Array.from(types);
  }, [assets]);

  // Handle layer toggle
  const handleLayerToggle = useCallback((layerId: string) => {
    setVisibleLayers(prev => {
      const newSet = new Set(prev);
      if (newSet.has(layerId)) {
        newSet.delete(layerId);
      } else {
        newSet.add(layerId);
      }
      return newSet;
    });
  }, []);

  // Handle asset type toggle
  const handleAssetTypeToggle = useCallback((type: string) => {
    setSelectedAssetTypes(prev => {
      const newSet = new Set(prev);
      if (newSet.has(type)) {
        newSet.delete(type);
      } else {
        newSet.add(type);
      }
      return newSet;
    });
  }, []);

  // Handle my location
  const handleMyLocation = useCallback(() => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          const { latitude, longitude } = position.coords;
          setMapCenter([latitude, longitude]);
          setMapZoom(15);
          toast.success('Location found!');
        },
        (error) => {
          toast.error('Unable to get your location');
          console.error('Geolocation error:', error);
        }
      );
    } else {
      toast.error('Geolocation is not supported by this browser');
    }
  }, []);

  // Handle search
  const handleSearch = useCallback(() => {
    // In a real implementation, this would use a geocoding service
    toast.info('Search functionality would integrate with geocoding service');
    setSearchDialog(true);
  }, []);

  // Handle fullscreen
  const handleFullscreen = useCallback(() => {
    if (document.fullscreenElement) {
      document.exitFullscreen();
    } else {
      document.documentElement.requestFullscreen();
    }
  }, []);

  return (
    <>
      <Helmet>
        <title>Interactive Map - FRA WebGIS Platform</title>
        <meta name="description" content="Interactive WebGIS platform for Forest Rights Act implementation with satellite imagery analysis and community asset mapping" />
      </Helmet>

      <Box sx={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
        {/* Header */}
        <Paper elevation={2} sx={{ p: 2, borderRadius: 0 }}>
          <Box display="flex" justifyContent="space-between" alignItems="center">
            <Box>
              <Typography variant="h5" component="h1" gutterBottom>
                Interactive WebGIS Map
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Forest Rights Act implementation mapping and analysis
              </Typography>
            </Box>
            <Box display="flex" gap={1}>
              <Button
                startIcon={<LayersIcon />}
                onClick={() => setDrawerOpen(true)}
                variant="outlined"
              >
                Layers ({visibleLayers.size})
              </Button>
              <Button
                startIcon={<FilterIcon />}
                variant="outlined"
                onClick={() => setDrawerOpen(true)}
              >
                Filters
              </Button>
            </Box>
          </Box>
        </Paper>

        {/* Map Container */}
        <Box sx={{ flex: 1, position: 'relative' }}>
          <MapContainer
            center={mapCenter}
            zoom={mapZoom}
            style={{ height: '100%', width: '100%' }}
            zoomControl={false}
          >
            {/* Base Tile Layer */}
            <TileLayer
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            />

            {/* Satellite Tile Layer (optional) */}
            <TileLayer
              url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
              attribution='Tiles &copy; Esri'
              opacity={0.7}
            />

            {/* Community Assets Markers */}
            {assets.map((asset) => {
              const icon = assetIcons[asset.asset_type as keyof typeof assetIcons] || assetIcons.default;
              
              return (
                <Marker
                  key={asset.id}
                  position={[asset.location.lat, asset.location.lng]}
                  icon={icon}
                >
                  <Popup>
                    <Box sx={{ minWidth: 200 }}>
                      <Typography variant="subtitle2" gutterBottom>
                        {asset.asset_name}
                      </Typography>
                      <Typography variant="body2" color="text.secondary" gutterBottom>
                        Type: {asset.asset_type.replace('_', ' ')}
                      </Typography>
                      <Typography variant="body2" color="text.secondary" gutterBottom>
                        Confidence: {(asset.confidence * 100).toFixed(1)}%
                      </Typography>
                      <Typography variant="body2" color="text.secondary" gutterBottom>
                        Detection: {asset.detection_method.replace('_', ' ')}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Detected: {new Date(asset.detected_at).toLocaleDateString()}
                      </Typography>
                      {asset.is_verified && (
                        <Chip
                          label="Verified"
                          size="small"
                          color="success"
                          sx={{ mt: 1 }}
                        />
                      )}
                    </Box>
                  </Popup>
                </Marker>
              );
            })}
          </MapContainer>

          {/* Map Controls */}
          <MapControls
            onFullscreen={handleFullscreen}
            onMyLocation={handleMyLocation}
            onSearch={handleSearch}
          />
        </Box>

        {/* Side Drawer */}
        <Drawer
          anchor="left"
          open={drawerOpen}
          onClose={() => setDrawerOpen(false)}
          PaperProps={{ sx: { width: 350 } }}
        >
          <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
            <Box display="flex" justifyContent="space-between" alignItems="center">
              <Typography variant="h6">Map Controls</Typography>
              <IconButton onClick={() => setDrawerOpen(false)}>
                <CloseIcon />
              </IconButton>
            </Box>
          </Box>

          {/* Layers Section */}
          <Accordion defaultExpanded>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography variant="subtitle1">
                <LayersIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
                GIS Layers
              </Typography>
            </AccordionSummary>
            <AccordionDetails sx={{ p: 0 }}>
              {layersLoading ? (
                <Box sx={{ p: 2 }}>
                  <Typography>Loading layers...</Typography>
                </Box>
              ) : (
                <LayerControl
                  layers={layers}
                  visibleLayers={visibleLayers}
                  onLayerToggle={handleLayerToggle}
                  onLayerInfo={setLayerInfoDialog}
                />
              )}
            </AccordionDetails>
          </Accordion>

          {/* Asset Filters Section */}
          <Accordion defaultExpanded>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography variant="subtitle1">
                <FilterIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
                Asset Filters
              </Typography>
            </AccordionSummary>
            <AccordionDetails sx={{ p: 0 }}>
              <AssetFilter
                assetTypes={availableAssetTypes}
                selectedTypes={selectedAssetTypes}
                onTypeToggle={handleAssetTypeToggle}
                verifiedOnly={verifiedOnly}
                onVerifiedToggle={setVerifiedOnly}
              />
            </AccordionDetails>
          </Accordion>

          {/* Statistics */}
          <Box sx={{ p: 2, borderTop: 1, borderColor: 'divider' }}>
            <Typography variant="subtitle2" gutterBottom>
              Map Statistics
            </Typography>
            <Grid container spacing={1}>
              <Grid item xs={6}>
                <Card variant="outlined">
                  <CardContent sx={{ p: 1, '&:last-child': { pb: 1 } }}>
                    <Typography variant="h6" color="primary">
                      {assets.length}
                    </Typography>
                    <Typography variant="caption">
                      Assets
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
              <Grid item xs={6}>
                <Card variant="outlined">
                  <CardContent sx={{ p: 1, '&:last-child': { pb: 1 } }}>
                    <Typography variant="h6" color="secondary">
                      {layers.length}
                    </Typography>
                    <Typography variant="caption">
                      Layers
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
          </Box>
        </Drawer>

        {/* Layer Info Dialog */}
        <Dialog
          open={!!layerInfoDialog}
          onClose={() => setLayerInfoDialog(null)}
          maxWidth="md"
          fullWidth
        >
          {layerInfoDialog && (
            <>
              <DialogTitle>
                {layerInfoDialog.display_name}
              </DialogTitle>
              <DialogContent>
                <Typography variant="body2" paragraph>
                  {layerInfoDialog.description || 'No description available.'}
                </Typography>
                <Grid container spacing={2}>
                  <Grid item xs={6}>
                    <Typography variant="subtitle2">Type:</Typography>
                    <Typography variant="body2">{layerInfoDialog.layer_type}</Typography>
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="subtitle2">Status:</Typography>
                    <Chip
                      label={layerInfoDialog.is_published ? 'Published' : 'Draft'}
                      color={layerInfoDialog.is_published ? 'success' : 'default'}
                      size="small"
                    />
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="subtitle2">Access:</Typography>
                    <Chip
                      label={layerInfoDialog.is_public ? 'Public' : 'Restricted'}
                      color={layerInfoDialog.is_public ? 'info' : 'warning'}
                      size="small"
                    />
                  </Grid>
                  {layerInfoDialog.data_date && (
                    <Grid item xs={6}>
                      <Typography variant="subtitle2">Data Date:</Typography>
                      <Typography variant="body2">
                        {new Date(layerInfoDialog.data_date).toLocaleDateString()}
                      </Typography>
                    </Grid>
                  )}
                </Grid>
              </DialogContent>
              <DialogActions>
                <Button onClick={() => setLayerInfoDialog(null)}>Close</Button>
              </DialogActions>
            </>
          )}
        </Dialog>

        {/* Search Dialog */}
        <Dialog
          open={searchDialog}
          onClose={() => setSearchDialog(false)}
          maxWidth="sm"
          fullWidth
        >
          <DialogTitle>Search Location</DialogTitle>
          <DialogContent>
            <TextField
              fullWidth
              label="Search for a place"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Enter village, district, or coordinates"
              sx={{ mt: 1 }}
            />
            <Alert severity="info" sx={{ mt: 2 }}>
              Search functionality would integrate with geocoding services like Nominatim or Google Places API.
            </Alert>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setSearchDialog(false)}>Cancel</Button>
            <Button variant="contained" disabled>Search</Button>
          </DialogActions>
        </Dialog>
      </Box>
    </>
  );
};

export default MapPage;