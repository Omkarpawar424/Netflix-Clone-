import React, { useState } from 'react';
import { useNavigate, useLocation, Link as RouterLink } from 'react-router-dom';
import {
  Box,
  Paper,
  TextField,
  Button,
  Typography,
  Link,
  Alert,
  InputAdornment,
  IconButton,
  Divider,
  Card,
  CardContent,
  Grid,
  useTheme,
  alpha,
} from '@mui/material';
import {
  Visibility,
  VisibilityOff,
  Email,
  Lock,
  Person,
  Security,
  Forest,
  Map,
  Analytics,
} from '@mui/icons-material';
import { Helmet } from 'react-helmet-async';
import { useForm, Controller } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import * as yup from 'yup';
import toast from 'react-hot-toast';

import { useAuth } from '../../contexts/AuthContext';
import { LoginCredentials } from '../../services/authService';

// Validation schema
const loginSchema = yup.object().shape({
  username: yup
    .string()
    .required('Username is required')
    .min(3, 'Username must be at least 3 characters'),
  password: yup
    .string()
    .required('Password is required')
    .min(8, 'Password must be at least 8 characters'),
});

const LoginPage: React.FC = () => {
  const theme = useTheme();
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAuth();
  
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  
  const from = location.state?.from?.pathname || '/dashboard';

  const {
    control,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginCredentials>({
    resolver: yupResolver(loginSchema),
    defaultValues: {
      username: '',
      password: '',
    },
  });

  const onSubmit = async (data: LoginCredentials) => {
    setIsLoading(true);
    try {
      await login(data);
      navigate(from, { replace: true });
    } catch (error) {
      // Error is handled in AuthContext
    } finally {
      setIsLoading(false);
    }
  };

  const handleShowPasswordToggle = () => {
    setShowPassword(!showPassword);
  };

  const features = [
    {
      icon: <Forest color="primary" />,
      title: 'Forest Rights Management',
      description: 'Digitize and manage FRA claims with AI-powered document processing',
    },
    {
      icon: <Map color="primary" />,
      title: 'Interactive WebGIS',
      description: 'Visualize forest rights, land use, and community assets on interactive maps',
    },
    {
      icon: <Analytics color="primary" />,
      title: 'Decision Support System',
      description: 'Get intelligent recommendations and cross-reference with government schemes',
    },
  ];

  const userRoles = [
    {
      role: 'Administrator',
      description: 'Full system control and configuration',
      icon: <Security color="primary" />,
    },
    {
      role: 'Government Official',
      description: 'Comprehensive data access and analysis',
      icon: <Person color="primary" />,
    },
    {
      role: 'Field Worker',
      description: 'Data entry and field verification',
      icon: <Map color="primary" />,
    },
    {
      role: 'Tribal Community',
      description: 'Basic information retrieval and claim submission',
      icon: <Forest color="primary" />,
    },
  ];

  return (
    <>
      <Helmet>
        <title>Login - FRA Decision Support System</title>
        <meta name="description" content="Login to the Forest Rights Act Decision Support System and WebGIS Platform" />
      </Helmet>

      <Box
        sx={{
          minHeight: '100vh',
          background: `linear-gradient(135deg, ${alpha(theme.palette.primary.main, 0.1)} 0%, ${alpha(theme.palette.secondary.main, 0.1)} 100%)`,
          display: 'flex',
          alignItems: 'center',
          py: 4,
        }}
      >
        <Grid container maxWidth="xl" sx={{ mx: 'auto', px: 2 }}>
          {/* Left side - Login form */}
          <Grid item xs={12} md={6} lg={5}>
            <Box
              sx={{
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'center',
                minHeight: { md: '80vh' },
                px: { xs: 2, md: 4 },
              }}
            >
              <Paper
                elevation={8}
                sx={{
                  p: 4,
                  borderRadius: 3,
                  maxWidth: 480,
                  mx: 'auto',
                  width: '100%',
                }}
              >
                {/* Header */}
                <Box textAlign="center" mb={4}>
                  <Typography
                    variant="h3"
                    component="h1"
                    gutterBottom
                    sx={{
                      fontWeight: 700,
                      background: `linear-gradient(135deg, ${theme.palette.primary.main} 0%, ${theme.palette.secondary.main} 100%)`,
                      backgroundClip: 'text',
                      WebkitBackgroundClip: 'text',
                      WebkitTextFillColor: 'transparent',
                    }}
                  >
                    FRA DSS
                  </Typography>
                  <Typography variant="h6" color="textSecondary" gutterBottom>
                    Decision Support System
                  </Typography>
                  <Typography variant="body2" color="textSecondary">
                    Sign in to access the Forest Rights Act platform
                  </Typography>
                </Box>

                {/* Demo credentials alert */}
                <Alert severity="info" sx={{ mb: 3 }}>
                  <Typography variant="body2">
                    <strong>Demo Credentials:</strong>
                    <br />
                    Admin: admin / admin123
                    <br />
                    Official: official / official123
                    <br />
                    Worker: worker / worker123
                  </Typography>
                </Alert>

                {/* Login form */}
                <form onSubmit={handleSubmit(onSubmit)}>
                  <Controller
                    name="username"
                    control={control}
                    render={({ field }) => (
                      <TextField
                        {...field}
                        fullWidth
                        label="Username"
                        variant="outlined"
                        margin="normal"
                        error={!!errors.username}
                        helperText={errors.username?.message}
                        InputProps={{
                          startAdornment: (
                            <InputAdornment position="start">
                              <Person color="action" />
                            </InputAdornment>
                          ),
                        }}
                      />
                    )}
                  />

                  <Controller
                    name="password"
                    control={control}
                    render={({ field }) => (
                      <TextField
                        {...field}
                        fullWidth
                        label="Password"
                        type={showPassword ? 'text' : 'password'}
                        variant="outlined"
                        margin="normal"
                        error={!!errors.password}
                        helperText={errors.password?.message}
                        InputProps={{
                          startAdornment: (
                            <InputAdornment position="start">
                              <Lock color="action" />
                            </InputAdornment>
                          ),
                          endAdornment: (
                            <InputAdornment position="end">
                              <IconButton
                                onClick={handleShowPasswordToggle}
                                edge="end"
                                aria-label="toggle password visibility"
                              >
                                {showPassword ? <VisibilityOff /> : <Visibility />}
                              </IconButton>
                            </InputAdornment>
                          ),
                        }}
                      />
                    )}
                  />

                  <Button
                    type="submit"
                    fullWidth
                    variant="contained"
                    size="large"
                    disabled={isLoading}
                    sx={{
                      mt: 3,
                      mb: 2,
                      py: 1.5,
                      borderRadius: 2,
                      background: `linear-gradient(135deg, ${theme.palette.primary.main} 0%, ${theme.palette.secondary.main} 100%)`,
                      '&:hover': {
                        background: `linear-gradient(135deg, ${theme.palette.primary.dark} 0%, ${theme.palette.secondary.dark} 100%)`,
                      },
                    }}
                  >
                    {isLoading ? 'Signing in...' : 'Sign In'}
                  </Button>
                </form>

                <Divider sx={{ my: 3 }}>
                  <Typography variant="body2" color="textSecondary">
                    OR
                  </Typography>
                </Divider>

                {/* Register link */}
                <Box textAlign="center">
                  <Typography variant="body2" color="textSecondary">
                    Don't have an account?{' '}
                    <Link
                      component={RouterLink}
                      to="/register"
                      color="primary"
                      sx={{ fontWeight: 600 }}
                    >
                      Register here
                    </Link>
                  </Typography>
                </Box>

                {/* Forgot password */}
                <Box textAlign="center" mt={2}>
                  <Link
                    href="#"
                    color="textSecondary"
                    variant="body2"
                    sx={{ textDecoration: 'none' }}
                  >
                    Forgot your password?
                  </Link>
                </Box>
              </Paper>
            </Box>
          </Grid>

          {/* Right side - Features and information */}
          <Grid item xs={12} md={6} lg={7}>
            <Box
              sx={{
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'center',
                minHeight: { md: '80vh' },
                px: { xs: 2, md: 4 },
                mt: { xs: 4, md: 0 },
              }}
            >
              {/* Platform overview */}
              <Box mb={4}>
                <Typography variant="h3" component="h2" gutterBottom sx={{ fontWeight: 700 }}>
                  AI-Powered Forest Rights Platform
                </Typography>
                <Typography variant="h6" color="textSecondary" paragraph>
                  Comprehensive Decision Support System for Forest Rights Act implementation
                  across Madhya Pradesh, Tripura, Odisha, and Telangana
                </Typography>
              </Box>

              {/* Key features */}
              <Grid container spacing={3} mb={4}>
                {features.map((feature, index) => (
                  <Grid item xs={12} sm={6} lg={4} key={index}>
                    <Card
                      sx={{
                        height: '100%',
                        transition: 'transform 0.2s',
                        '&:hover': {
                          transform: 'translateY(-4px)',
                        },
                      }}
                    >
                      <CardContent>
                        <Box display="flex" alignItems="center" mb={2}>
                          {feature.icon}
                          <Typography variant="h6" sx={{ ml: 1, fontWeight: 600 }}>
                            {feature.title}
                          </Typography>
                        </Box>
                        <Typography variant="body2" color="textSecondary">
                          {feature.description}
                        </Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                ))}
              </Grid>

              {/* User roles */}
              <Box>
                <Typography variant="h5" gutterBottom sx={{ fontWeight: 600 }}>
                  Multi-Role Access System
                </Typography>
                <Grid container spacing={2}>
                  {userRoles.map((roleInfo, index) => (
                    <Grid item xs={12} sm={6} key={index}>
                      <Box
                        sx={{
                          p: 2,
                          border: `1px solid ${theme.palette.divider}`,
                          borderRadius: 2,
                          display: 'flex',
                          alignItems: 'flex-start',
                        }}
                      >
                        <Box sx={{ mr: 2, mt: 0.5 }}>
                          {roleInfo.icon}
                        </Box>
                        <Box>
                          <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                            {roleInfo.role}
                          </Typography>
                          <Typography variant="body2" color="textSecondary">
                            {roleInfo.description}
                          </Typography>
                        </Box>
                      </Box>
                    </Grid>
                  ))}
                </Grid>
              </Box>

              {/* Performance metrics */}
              <Box
                sx={{
                  mt: 4,
                  p: 3,
                  bgcolor: alpha(theme.palette.primary.main, 0.1),
                  borderRadius: 2,
                }}
              >
                <Typography variant="h6" gutterBottom sx={{ fontWeight: 600 }}>
                  Platform Performance
                </Typography>
                <Grid container spacing={3}>
                  <Grid item xs={4}>
                    <Box textAlign="center">
                      <Typography variant="h4" color="primary" sx={{ fontWeight: 700 }}>
                        95%+
                      </Typography>
                      <Typography variant="caption" color="textSecondary">
                        Document Accuracy
                      </Typography>
                    </Box>
                  </Grid>
                  <Grid item xs={4}>
                    <Box textAlign="center">
                      <Typography variant="h4" color="primary" sx={{ fontWeight: 700 }}>
                        24/7
                      </Typography>
                      <Typography variant="caption" color="textSecondary">
                        System Availability
                      </Typography>
                    </Box>
                  </Grid>
                  <Grid item xs={4}>
                    <Box textAlign="center">
                      <Typography variant="h4" color="primary" sx={{ fontWeight: 700 }}>
                        4 States
                      </Typography>
                      <Typography variant="caption" color="textSecondary">
                        Multi-State Coverage
                      </Typography>
                    </Box>
                  </Grid>
                </Grid>
              </Box>
            </Box>
          </Grid>
        </Grid>
      </Box>
    </>
  );
};

export default LoginPage;