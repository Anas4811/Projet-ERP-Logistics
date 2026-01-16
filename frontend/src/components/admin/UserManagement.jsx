import React from 'react';
import { Box, Typography, Paper, Button } from '@mui/material';
import { AdminPanelSettings } from '@mui/icons-material';

const UserManagement = () => {
  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        User Management
      </Typography>
      <Paper sx={{ p: 4, textAlign: 'center' }}>
        <AdminPanelSettings sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
        <Typography variant="h6" color="text.secondary">
          User & Role Management
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
          Manage users, roles, and permissions
        </Typography>
        <Button variant="contained">
          Coming Soon
        </Button>
      </Paper>
    </Box>
  );
};

export default UserManagement;
