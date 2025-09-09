import React, { useState } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Paper,
  IconButton,
  Button,
  Chip,
  Avatar,
  List,
  ListItem,
  ListItemAvatar,
  ListItemText,
  ListItemSecondaryAction,
  LinearProgress,
  Divider,
  Alert,
  Tab,
  Tabs,
  useTheme,
} from '@mui/material';
import {
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  Description as DocumentIcon,
  Gavel as ClaimIcon,
  Map as MapIcon,
  People as PeopleIcon,
  CheckCircle as CheckCircleIcon,
  Schedule as ScheduleIcon,
  Warning as WarningIcon,
  Refresh as RefreshIcon,
  ArrowForward as ArrowForwardIcon,
  Forest as ForestIcon,
  Home as HomeIcon,
  Water as WaterIcon,
  Agriculture as AgricultureIcon,
} from '@mui/icons-material';
import { Helmet } from 'react-helmet-async';
import { useQuery } from 'react-query';
import { Line, Doughnut, Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
  BarElement,
} from 'chart.js';

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
  BarElement
);

import { useAuth } from '../../contexts/AuthContext';
import { analyticsService } from '../../services/analyticsService';

// Types
interface DashboardStats {
  totalClaims: number;
  approvedClaims: number;
  pendingClaims: number;
  documentsProcessed: number;
  activeUsers: number;
  landAreaMapped: number;
}

interface RecentActivity {
  id: string;
  type: 'claim_submitted' | 'document_processed' | 'verification_completed';
  title: string;
  description: string;
  timestamp: string;
  user?: string;
  status?: string;
}

// Mock data (replace with actual API calls)
const mockStats: DashboardStats = {
  totalClaims: 1247,
  approvedClaims: 892,
  pendingClaims: 355,
  documentsProcessed: 2156,
  activeUsers: 89,
  landAreaMapped: 15420.5,
};

const mockActivities: RecentActivity[] = [
  {
    id: '1',
    type: 'claim_submitted',
    title: 'New FRA Claim Submitted',
    description: 'MP/2024/001234 by Ramesh Kumar',
    timestamp: '2 hours ago',
    user: 'Ramesh Kumar',
    status: 'submitted',
  },
  {
    id: '2',
    type: 'document_processed',
    title: 'Document Processing Completed',
    description: 'Title deed processed with 95% accuracy',
    timestamp: '4 hours ago',
    status: 'completed',
  },
  {
    id: '3',
    type: 'verification_completed',
    title: 'Field Verification Completed',
    description: 'Verification for claim OR/2024/005678',
    timestamp: '1 day ago',
    user: 'Field Officer',
    status: 'verified',
  },
];

// Stat Card Component
const StatCard: React.FC<{
  title: string;
  value: string | number;
  icon: React.ReactElement;
  trend?: number;
  color?: string;
  subtitle?: string;
}> = ({ title, value, icon, trend, color = 'primary', subtitle }) => {
  const theme = useTheme();
  
  return (
    <Card sx={{ height: '100%' }}>
      <CardContent>
        <Box display="flex" justifyContent="space-between" alignItems="flex-start">
          <Box>
            <Typography color="textSecondary" gutterBottom variant="overline">
              {title}
            </Typography>
            <Typography variant="h4" component="div" sx={{ fontWeight: 600, mb: 1 }}>
              {typeof value === 'number' ? value.toLocaleString() : value}
            </Typography>
            {subtitle && (
              <Typography variant="body2" color="textSecondary">
                {subtitle}
              </Typography>
            )}
            {trend !== undefined && (
              <Box display="flex" alignItems="center" mt={1}>
                {trend > 0 ? (
                  <TrendingUpIcon color="success" fontSize="small" />
                ) : (
                  <TrendingDownIcon color="error" fontSize="small" />
                )}
                <Typography
                  variant="body2"
                  color={trend > 0 ? 'success.main' : 'error.main'}
                  sx={{ ml: 0.5 }}
                >
                  {Math.abs(trend)}%
                </Typography>
              </Box>
            )}
          </Box>
          <Avatar
            sx={{
              bgcolor: `${color}.main`,
              width: 56,
              height: 56,
            }}
          >
            {icon}
          </Avatar>
        </Box>
      </CardContent>
    </Card>
  );
};

// Activity Item Component
const ActivityItem: React.FC<{ activity: RecentActivity }> = ({ activity }) => {
  const getActivityIcon = (type: string) => {
    switch (type) {
      case 'claim_submitted':
        return <ClaimIcon />;
      case 'document_processed':
        return <DocumentIcon />;
      case 'verification_completed':
        return <CheckCircleIcon />;
      default:
        return <ScheduleIcon />;
    }
  };

  const getStatusColor = (status?: string) => {
    switch (status) {
      case 'completed':
      case 'verified':
        return 'success';
      case 'submitted':
      case 'pending':
        return 'warning';
      case 'rejected':
        return 'error';
      default:
        return 'default';
    }
  };

  return (
    <ListItem>
      <ListItemAvatar>
        <Avatar sx={{ bgcolor: 'primary.main' }}>
          {getActivityIcon(activity.type)}
        </Avatar>
      </ListItemAvatar>
      <ListItemText
        primary={activity.title}
        secondary={
          <Box>
            <Typography variant="body2" color="textSecondary">
              {activity.description}
            </Typography>
            <Typography variant="caption" color="textSecondary">
              {activity.timestamp}
            </Typography>
          </Box>
        }
      />
      <ListItemSecondaryAction>
        {activity.status && (
          <Chip
            label={activity.status}
            size="small"
            color={getStatusColor(activity.status)}
            variant="outlined"
          />
        )}
      </ListItemSecondaryAction>
    </ListItem>
  );
};

// Main Dashboard Component
const DashboardPage: React.FC = () => {
  const theme = useTheme();
  const { user } = useAuth();
  const [tabValue, setTabValue] = useState(0);

  // Chart data
  const claimsChartData = {
    labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
    datasets: [
      {
        label: 'Claims Submitted',
        data: [65, 78, 90, 81, 96, 105],
        borderColor: theme.palette.primary.main,
        backgroundColor: theme.palette.primary.main + '20',
        tension: 0.4,
      },
      {
        label: 'Claims Approved',
        data: [45, 52, 67, 58, 73, 82],
        borderColor: theme.palette.success.main,
        backgroundColor: theme.palette.success.main + '20',
        tension: 0.4,
      },
    ],
  };

  const landUseChartData = {
    labels: ['Forest', 'Agricultural', 'Water Bodies', 'Built-up', 'Others'],
    datasets: [
      {
        data: [45, 30, 10, 8, 7],
        backgroundColor: [
          theme.palette.success.main,
          theme.palette.warning.main,
          theme.palette.info.main,
          theme.palette.error.main,
          theme.palette.grey[400],
        ],
      },
    ],
  };

  const stateWiseData = {
    labels: ['Madhya Pradesh', 'Tripura', 'Odisha', 'Telangana'],
    datasets: [
      {
        label: 'Total Claims',
        data: [450, 320, 280, 197],
        backgroundColor: theme.palette.primary.main,
      },
      {
        label: 'Approved Claims',
        data: [325, 245, 198, 124],
        backgroundColor: theme.palette.success.main,
      },
    ],
  };

  const getRoleBasedWelcome = () => {
    if (!user) return 'Welcome to FRA DSS Platform';
    
    switch (user.role) {
      case 'admin':
        return 'Administrator Dashboard';
      case 'government_official':
        return `${user.state} - Government Dashboard`;
      case 'field_worker':
        return `${user.district} - Field Operations`;
      case 'tribal_community':
        return `Welcome, ${user.full_name}`;
      default:
        return 'Welcome to FRA DSS Platform';
    }
  };

  const getRoleBasedStats = () => {
    // In a real app, these would be filtered based on user role and location
    return mockStats;
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  return (
    <>
      <Helmet>
        <title>Dashboard - FRA Decision Support System</title>
        <meta name="description" content="Comprehensive dashboard for Forest Rights Act implementation with real-time analytics and insights" />
      </Helmet>

      <Box sx={{ p: 3 }}>
        {/* Header */}
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
          <Box>
            <Typography variant="h4" component="h1" gutterBottom>
              {getRoleBasedWelcome()}
            </Typography>
            <Typography variant="body1" color="textSecondary">
              Monitor FRA implementation progress and system performance
            </Typography>
          </Box>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={() => window.location.reload()}
          >
            Refresh Data
          </Button>
        </Box>

        {/* Alert for pending actions */}
        {user?.role === 'field_worker' && (
          <Alert severity="info" sx={{ mb: 3 }}>
            You have 5 pending field verifications scheduled for this week.
            <Button size="small" sx={{ ml: 2 }}>
              View Tasks
            </Button>
          </Alert>
        )}

        {/* Stats Cards */}
        <Grid container spacing={3} mb={3}>
          <Grid item xs={12} sm={6} md={3}>
            <StatCard
              title="Total FRA Claims"
              value={getRoleBasedStats().totalClaims}
              icon={<ClaimIcon />}
              trend={12.5}
              color="primary"
            />
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <StatCard
              title="Approved Claims"
              value={getRoleBasedStats().approvedClaims}
              icon={<CheckCircleIcon />}
              trend={8.2}
              color="success"
            />
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <StatCard
              title="Documents Processed"
              value={getRoleBasedStats().documentsProcessed}
              icon={<DocumentIcon />}
              trend={15.3}
              color="info"
            />
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <StatCard
              title="Land Area Mapped"
              value={`${getRoleBasedStats().landAreaMapped.toLocaleString()} ha`}
              icon={<MapIcon />}
              trend={22.1}
              color="warning"
              subtitle="Hectares"
            />
          </Grid>
        </Grid>

        {/* Charts and Analytics */}
        <Grid container spacing={3} mb={3}>
          {/* Claims Trend */}
          <Grid item xs={12} lg={8}>
            <Card>
              <CardContent>
                <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                  <Typography variant="h6">Claims Progress Trend</Typography>
                  <Tabs value={tabValue} onChange={handleTabChange} size="small">
                    <Tab label="6 Months" />
                    <Tab label="1 Year" />
                    <Tab label="All Time" />
                  </Tabs>
                </Box>
                <Box height={300}>
                  <Line
                    data={claimsChartData}
                    options={{
                      responsive: true,
                      maintainAspectRatio: false,
                      plugins: {
                        legend: {
                          position: 'top' as const,
                        },
                      },
                      scales: {
                        y: {
                          beginAtZero: true,
                        },
                      },
                    }}
                  />
                </Box>
              </CardContent>
            </Card>
          </Grid>

          {/* Land Use Distribution */}
          <Grid item xs={12} lg={4}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Land Use Distribution
                </Typography>
                <Box height={300} display="flex" alignItems="center" justifyContent="center">
                  <Doughnut
                    data={landUseChartData}
                    options={{
                      responsive: true,
                      maintainAspectRatio: false,
                      plugins: {
                        legend: {
                          position: 'bottom' as const,
                        },
                      },
                    }}
                  />
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        {/* State-wise Performance and Recent Activity */}
        <Grid container spacing={3}>
          {/* State-wise Performance */}
          {user?.role === 'admin' && (
            <Grid item xs={12} lg={8}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    State-wise Performance
                  </Typography>
                  <Box height={300}>
                    <Bar
                      data={stateWiseData}
                      options={{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                          legend: {
                            position: 'top' as const,
                          },
                        },
                        scales: {
                          y: {
                            beginAtZero: true,
                          },
                        },
                      }}
                    />
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          )}

          {/* Recent Activity */}
          <Grid item xs={12} lg={user?.role === 'admin' ? 4 : 6}>
            <Card>
              <CardContent>
                <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                  <Typography variant="h6">Recent Activity</Typography>
                  <Button size="small" endIcon={<ArrowForwardIcon />}>
                    View All
                  </Button>
                </Box>
                <List disablePadding>
                  {mockActivities.map((activity, index) => (
                    <React.Fragment key={activity.id}>
                      <ActivityItem activity={activity} />
                      {index < mockActivities.length - 1 && <Divider />}
                    </React.Fragment>
                  ))}
                </List>
              </CardContent>
            </Card>
          </Grid>

          {/* Quick Actions */}
          <Grid item xs={12} lg={user?.role === 'admin' ? 12 : 6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Quick Actions
                </Typography>
                <Grid container spacing={2}>
                  <Grid item xs={6} sm={3}>
                    <Button
                      variant="outlined"
                      fullWidth
                      startIcon={<ClaimIcon />}
                      sx={{ py: 1.5 }}
                    >
                      New Claim
                    </Button>
                  </Grid>
                  <Grid item xs={6} sm={3}>
                    <Button
                      variant="outlined"
                      fullWidth
                      startIcon={<DocumentIcon />}
                      sx={{ py: 1.5 }}
                    >
                      Upload Document
                    </Button>
                  </Grid>
                  <Grid item xs={6} sm={3}>
                    <Button
                      variant="outlined"
                      fullWidth
                      startIcon={<MapIcon />}
                      sx={{ py: 1.5 }}
                    >
                      View Map
                    </Button>
                  </Grid>
                  <Grid item xs={6} sm={3}>
                    <Button
                      variant="outlined"
                      fullWidth
                      startIcon={<PeopleIcon />}
                      sx={{ py: 1.5 }}
                    >
                      Manage Users
                    </Button>
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        {/* System Health */}
        {user?.role === 'admin' && (
          <Card sx={{ mt: 3 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                System Health
              </Typography>
              <Grid container spacing={3}>
                <Grid item xs={12} sm={6} md={3}>
                  <Box>
                    <Typography variant="body2" color="textSecondary">
                      Document Processing
                    </Typography>
                    <LinearProgress
                      variant="determinate"
                      value={95}
                      color="success"
                      sx={{ mt: 1, mb: 1 }}
                    />
                    <Typography variant="caption">95% Accuracy</Typography>
                  </Box>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <Box>
                    <Typography variant="body2" color="textSecondary">
                      System Uptime
                    </Typography>
                    <LinearProgress
                      variant="determinate"
                      value={99.8}
                      color="success"
                      sx={{ mt: 1, mb: 1 }}
                    />
                    <Typography variant="caption">99.8% Uptime</Typography>
                  </Box>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <Box>
                    <Typography variant="body2" color="textSecondary">
                      Data Quality
                    </Typography>
                    <LinearProgress
                      variant="determinate"
                      value={92}
                      color="info"
                      sx={{ mt: 1, mb: 1 }}
                    />
                    <Typography variant="caption">92% Quality Score</Typography>
                  </Box>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <Box>
                    <Typography variant="body2" color="textSecondary">
                      User Satisfaction
                    </Typography>
                    <LinearProgress
                      variant="determinate"
                      value={88}
                      color="warning"
                      sx={{ mt: 1, mb: 1 }}
                    />
                    <Typography variant="caption">4.4/5 Rating</Typography>
                  </Box>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        )}
      </Box>
    </>
  );
};

export default DashboardPage;