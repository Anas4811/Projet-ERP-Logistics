import React, { useState, useEffect, useCallback } from 'react';
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  CircularProgress,
  Alert,
  Chip,
} from '@mui/material';
import {
  Business,
  ShoppingCart,
  LocalShipping,
  Security,
  Warning,
  CheckCircle,
} from '@mui/icons-material';
import { useAuth } from '../hooks/useAuth';
import api from '../services/api';

const Dashboard = () => {
  const { user, hasRole } = useAuth();
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchDashboardStats = useCallback(async () => {
    try {
      setLoading(true);
      const endpoints = [];

      // Add endpoints based on user roles
      if (hasRole('admin') || hasRole('warehouse') || hasRole('operator')) {
        endpoints.push(
          api.get('/vendors/dashboard/'),
          api.get('/purchase-orders/dashboard/'),
          api.get('/asns/dashboard/')
        );
      }

      if (hasRole('admin') || hasRole('warehouse') || hasRole('operator') || hasRole('driver')) {
        endpoints.push(api.get('/gate/dashboard/'));
      }

      const responses = await Promise.all(endpoints);

      const dashboardData = {};
        responses.forEach((response) => {
        if (response.config.url.includes('vendors')) {
          dashboardData.vendors = response.data;
        } else if (response.config.url.includes('purchase-orders')) {
          dashboardData.pos = response.data;
        } else if (response.config.url.includes('asns')) {
          dashboardData.asns = response.data;
        } else if (response.config.url.includes('gate')) {
          dashboardData.gate = response.data;
        }
      });

      setStats(dashboardData);
    } catch (error) {
      console.error('Dashboard error:', error);
      setError('Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  }, [hasRole]);

  useEffect(() => {
    fetchDashboardStats();
  }, [fetchDashboardStats]);

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mt: 2 }}>
        {error}
      </Alert>
    );
  }

  const StatCard = ({ title, value, icon, color = 'primary', subtitle }) => (
    <Card sx={{ height: '100%' }}>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <Box sx={{ color: `${color}.main`, mr: 1 }}>
            {icon}
          </Box>
          <Typography variant="h6" component="div">
            {title}
          </Typography>
        </Box>
        <Typography variant="h4" component="div" sx={{ mb: 1 }}>
          {value || 0}
        </Typography>
        {subtitle && (
          <Typography variant="body2" color="text.secondary">
            {subtitle}
          </Typography>
        )}
      </CardContent>
    </Card>
  );

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Welcome to ERP Logistics Dashboard
      </Typography>

      <Box sx={{ mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          User Information
        </Typography>
        <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
          {user?.roles?.map((role) => (
            <Chip
              key={role.id}
              label={role.name}
              color="primary"
              variant="outlined"
            />
          ))}
        </Box>
        <Typography variant="body1">
          Welcome back, {user?.first_name} {user?.last_name} ({user?.email})
        </Typography>
      </Box>

      <Grid container spacing={3}>
        {/* Vendor Stats */}
        {(hasRole('admin') || hasRole('warehouse') || hasRole('operator')) && stats.vendors && (
          <>
            <Grid item xs={12} sm={6} md={3}>
              <StatCard
                title="Total Vendors"
                value={stats.vendors.total_vendors}
                icon={<Business />}
                color="primary"
                subtitle={`${stats.vendors.active_vendors} active`}
              />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <StatCard
                title="Pending POs"
                value={stats.vendors.total_pos}
                icon={<ShoppingCart />}
                color="warning"
                subtitle={`${stats.vendors.pending_pos} pending approval`}
              />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <StatCard
                title="Overdue POs"
                value={stats.vendors.overdue_pos}
                icon={<Warning />}
                color="error"
                subtitle="Require attention"
              />
            </Grid>
          </>
        )}

        {/* PO Stats */}
        {stats.pos && (
          <>
            <Grid item xs={12} sm={6} md={3}>
              <StatCard
                title="Active POs"
                value={stats.pos.total_pos}
                icon={<ShoppingCart />}
                color="info"
                subtitle={`${stats.pos.pending_pos} pending`}
              />
            </Grid>
          </>
        )}

        {/* ASN Stats */}
        {(hasRole('admin') || hasRole('warehouse') || hasRole('operator') || hasRole('driver')) && stats.asns && (
          <>
            <Grid item xs={12} sm={6} md={3}>
              <StatCard
                title="Total ASNs"
                value={stats.asns.total_asns}
                icon={<LocalShipping />}
                color="secondary"
                subtitle={`${stats.asns.in_transit} in transit`}
              />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <StatCard
                title="Expected Today"
                value={stats.asns.expected_today}
                icon={<CheckCircle />}
                color="success"
                subtitle="Arrivals expected"
              />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <StatCard
                title="Overdue ASNs"
                value={stats.asns.overdue}
                icon={<Warning />}
                color="error"
                subtitle="Require attention"
              />
            </Grid>
          </>
        )}

        {/* Gate Stats */}
        {stats.gate && (
          <>
            <Grid item xs={12} sm={6} md={3}>
              <StatCard
                title="Waiting Queue"
                value={stats.gate.waiting_count}
                icon={<Security />}
                color="warning"
                subtitle="Vehicles waiting"
              />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <StatCard
                title="Processing"
                value={stats.gate.checking_count}
                icon={<Security />}
                color="info"
                subtitle="Being checked"
              />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <StatCard
                title="Completed Today"
                value={stats.gate.completed_today}
                icon={<CheckCircle />}
                color="success"
                subtitle="Processed today"
              />
            </Grid>
          </>
        )}
      </Grid>

      {/* Recent Activity */}
      {stats.gate?.recent_queue && stats.gate.recent_queue.length > 0 && (
        <Box sx={{ mt: 4 }}>
          <Typography variant="h6" gutterBottom>
            Recent Gate Activity
          </Typography>
          <Grid container spacing={2}>
            {stats.gate.recent_queue.slice(0, 6).map((item) => (
              <Grid item xs={12} md={6} lg={4} key={item.id}>
                <Card>
                  <CardContent>
                    <Typography variant="subtitle1">
                      Queue {item.queue_number}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {item.vendor_name} - {item.vehicle_number}
                    </Typography>
                    <Chip
                      label={item.status}
                      size="small"
                      color={
                        item.status === 'COMPLETED' ? 'success' :
                        item.status === 'WAITING' ? 'warning' :
                        item.status === 'VERIFIED' ? 'info' : 'default'
                      }
                      sx={{ mt: 1 }}
                    />
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        </Box>
      )}
    </Box>
  );
};

export default Dashboard;
