import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { Box, CircularProgress, Typography } from '@mui/material';
import { useAuth } from '../../contexts/AuthContext';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requiredRole?: string | string[];
  requiredPermission?: string;
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  requiredRole,
  requiredPermission,
}) => {
  const { user, loading } = useAuth();
  const location = useLocation();

  // Show loading spinner while checking authentication
  if (loading) {
    return (
      <Box
        display="flex"
        flexDirection="column"
        justifyContent="center"
        alignItems="center"
        minHeight="100vh"
        bgcolor="background.default"
      >
        <CircularProgress size={60} />
        <Typography variant="h6" sx={{ mt: 2 }}>
          Loading...
        </Typography>
      </Box>
    );
  }

  // Redirect to login if not authenticated
  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Check role-based access
  if (requiredRole) {
    const roles = Array.isArray(requiredRole) ? requiredRole : [requiredRole];
    if (!roles.includes(user.role)) {
      return (
        <Box
          display="flex"
          flexDirection="column"
          justifyContent="center"
          alignItems="center"
          minHeight="100vh"
          bgcolor="background.default"
          p={3}
        >
          <Typography variant="h4" color="error" gutterBottom>
            Access Denied
          </Typography>
          <Typography variant="body1" color="textSecondary" textAlign="center">
            You don't have permission to access this page.
            <br />
            Required role: {roles.join(' or ')}
            <br />
            Your role: {user.role}
          </Typography>
        </Box>
      );
    }
  }

  // Check permission-based access (simplified)
  if (requiredPermission) {
    const rolePermissions = {
      admin: ['*'], // All permissions
      government_official: [
        'read_claims',
        'write_claims',
        'verify_claims',
        'generate_reports',
        'view_analytics',
        'manage_field_workers',
      ],
      field_worker: [
        'read_assigned_claims',
        'update_verification',
        'upload_documents',
        'gps_marking',
        'photo_upload',
      ],
      tribal_community: [
        'view_own_claims',
        'submit_claims',
        'upload_documents',
        'check_status',
      ],
    };

    const userPermissions = rolePermissions[user.role as keyof typeof rolePermissions] || [];

    if (!userPermissions.includes('*') && !userPermissions.includes(requiredPermission)) {
      return (
        <Box
          display="flex"
          flexDirection="column"
          justifyContent="center"
          alignItems="center"
          minHeight="100vh"
          bgcolor="background.default"
          p={3}
        >
          <Typography variant="h4" color="error" gutterBottom>
            Access Denied
          </Typography>
          <Typography variant="body1" color="textSecondary" textAlign="center">
            You don't have the required permission to access this page.
            <br />
            Required permission: {requiredPermission}
          </Typography>
        </Box>
      );
    }
  }

  // Check account status
  if (user.status === 'pending_approval') {
    return (
      <Box
        display="flex"
        flexDirection="column"
        justifyContent="center"
        alignItems="center"
        minHeight="100vh"
        bgcolor="background.default"
        p={3}
      >
        <Typography variant="h4" color="warning.main" gutterBottom>
          Account Pending Approval
        </Typography>
        <Typography variant="body1" color="textSecondary" textAlign="center">
          Your account is pending approval by an administrator.
          <br />
          Please wait for approval or contact support.
        </Typography>
      </Box>
    );
  }

  if (user.status === 'suspended') {
    return (
      <Box
        display="flex"
        flexDirection="column"
        justifyContent="center"
        alignItems="center"
        minHeight="100vh"
        bgcolor="background.default"
        p={3}
      >
        <Typography variant="h4" color="error" gutterBottom>
          Account Suspended
        </Typography>
        <Typography variant="body1" color="textSecondary" textAlign="center">
          Your account has been suspended.
          <br />
          Please contact support for assistance.
        </Typography>
      </Box>
    );
  }

  if (user.status === 'inactive') {
    return (
      <Box
        display="flex"
        flexDirection="column"
        justifyContent="center"
        alignItems="center"
        minHeight="100vh"
        bgcolor="background.default"
        p={3}
      >
        <Typography variant="h4" color="error" gutterBottom>
          Account Inactive
        </Typography>
        <Typography variant="body1" color="textSecondary" textAlign="center">
          Your account is inactive.
          <br />
          Please contact support to reactivate your account.
        </Typography>
      </Box>
    );
  }

  // User is authenticated and authorized
  return <>{children}</>;
};

export default ProtectedRoute;