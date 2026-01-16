import React, { useState, useEffect } from 'react';
import {
  Box,
  Button,
  Card,
  CardContent,
  Grid,
  Typography,
  Alert,
  CircularProgress,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper as MuiPaper,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from '@mui/material';
import {
  Security,
  CheckCircle,
  Pending,
  Schedule,
  Warning,
  Refresh,
} from '@mui/icons-material';
import api from '../../services/api';

const GateQueue = () => {
  const [queueData, setQueueData] = useState({
    waiting_count: 0,
    checking_count: 0,
    verified_count: 0,
    completed_today: 0,
    recent_queue: [],
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [asns, setAsns] = useState([]);

  // Create form state
  const [createForm, setCreateForm] = useState({
    asn: '',
    vehicle_number: '',
    trailer_number: '',
    driver_name: '',
    driver_id: '',
    driver_phone: '',
  });

  useEffect(() => {
    fetchDashboardData();
    fetchAvailableASNs();
  }, []);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      const response = await api.get('/gate/dashboard/');
      setQueueData(response.data);
    } catch (error) {
      console.error('Error fetching gate dashboard:', error);
      setError('Failed to load gate dashboard');
    } finally {
      setLoading(false);
    }
  };

  const fetchAvailableASNs = async () => {
    try {
      const response = await api.get('/asns/', {
        params: { status: 'APPROVED,IN_TRANSIT' }
      });
      setAsns(response.data.results || response.data);
    } catch (error) {
      console.error('Error fetching ASNs:', error);
    }
  };

  const handleCreateQueueEntry = async () => {
    if (!createForm.asn || !createForm.vehicle_number || !createForm.driver_name) {
      return;
    }

    try {
      await api.post('/gate-queue/', createForm);
      setCreateDialogOpen(false);
      setCreateForm({
        asn: '',
        vehicle_number: '',
        trailer_number: '',
        driver_name: '',
        driver_id: '',
        driver_phone: '',
      });
      fetchDashboardData(); // Refresh data
    } catch (error) {
      console.error('Error creating queue entry:', error);
      setError('Failed to create queue entry');
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'WAITING':
        return 'warning';
      case 'CHECKING_IN':
        return 'info';
      case 'VERIFIED':
        return 'primary';
      case 'COMPLETED':
        return 'success';
      case 'REJECTED':
        return 'error';
      default:
        return 'default';
    }
  };

  const StatCard = ({ title, value, icon, color = 'primary' }) => (
    <Card sx={{ height: '100%' }}>
      <CardContent sx={{ textAlign: 'center' }}>
        <Box sx={{ color: `${color}.main`, mb: 1 }}>
          {icon}
        </Box>
        <Typography variant="h4" component="div" sx={{ mb: 1 }}>
          {value}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {title}
        </Typography>
      </CardContent>
    </Card>
  );

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

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1">
          Gate Check-in System
        </Typography>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button
            variant="outlined"
            startIcon={<Refresh />}
            onClick={fetchDashboardData}
          >
            Refresh
          </Button>
          <Button
            variant="contained"
            startIcon={<Security />}
            onClick={() => setCreateDialogOpen(true)}
          >
            New Arrival
          </Button>
        </Box>
      </Box>

      {/* Statistics Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Waiting"
            value={queueData.waiting_count}
            icon={<Pending sx={{ fontSize: 40 }} />}
            color="warning"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Checking In"
            value={queueData.checking_count}
            icon={<Security sx={{ fontSize: 40 }} />}
            color="info"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Verified"
            value={queueData.verified_count}
            icon={<CheckCircle sx={{ fontSize: 40 }} />}
            color="primary"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Completed Today"
            value={queueData.completed_today}
            icon={<Schedule sx={{ fontSize: 40 }} />}
            color="success"
          />
        </Grid>
      </Grid>

      {/* Recent Activity */}
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Recent Gate Activity
          </Typography>

          {queueData.recent_queue && queueData.recent_queue.length > 0 ? (
            <TableContainer component={MuiPaper} variant="outlined">
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Queue #</TableCell>
                    <TableCell>ASN</TableCell>
                    <TableCell>Vendor</TableCell>
                    <TableCell>Vehicle</TableCell>
                    <TableCell>Driver</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Created</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {queueData.recent_queue.map((entry) => (
                    <TableRow key={entry.id} hover>
                      <TableCell>
                        <Typography variant="subtitle2" sx={{ fontWeight: 'bold' }}>
                          {entry.queue_number}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">
                          {entry.asn_number}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">
                          {entry.vendor_name}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">
                          {entry.vehicle_number}
                        </Typography>
                        {entry.trailer_number && (
                          <Typography variant="caption" color="text.secondary">
                            Trailer: {entry.trailer_number}
                          </Typography>
                        )}
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">
                          {entry.driver_name}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={entry.status}
                          size="small"
                          color={getStatusColor(entry.status)}
                          variant="outlined"
                        />
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">
                          {new Date(entry.created_at).toLocaleString()}
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          ) : (
            <Typography color="text.secondary" sx={{ textAlign: 'center', py: 4 }}>
              No recent gate activity
            </Typography>
          )}
        </CardContent>
      </Card>

      {/* Create Queue Entry Dialog */}
      <Dialog
        open={createDialogOpen}
        onClose={() => setCreateDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>New Vehicle Arrival</DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12}>
              <FormControl fullWidth required>
                <InputLabel>ASN</InputLabel>
                <Select
                  value={createForm.asn}
                  onChange={(e) => setCreateForm({ ...createForm, asn: e.target.value })}
                  label="ASN"
                >
                  {asns.map((asn) => (
                    <MenuItem key={asn.id} value={asn.id}>
                      {asn.asn_number} - {asn.vendor_name} ({asn.total_items} items)
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Vehicle Number"
                value={createForm.vehicle_number}
                onChange={(e) => setCreateForm({ ...createForm, vehicle_number: e.target.value })}
                required
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Trailer Number (Optional)"
                value={createForm.trailer_number}
                onChange={(e) => setCreateForm({ ...createForm, trailer_number: e.target.value })}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Driver Name"
                value={createForm.driver_name}
                onChange={(e) => setCreateForm({ ...createForm, driver_name: e.target.value })}
                required
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Driver ID (Optional)"
                value={createForm.driver_id}
                onChange={(e) => setCreateForm({ ...createForm, driver_id: e.target.value })}
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Driver Phone"
                value={createForm.driver_phone}
                onChange={(e) => setCreateForm({ ...createForm, driver_phone: e.target.value })}
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleCreateQueueEntry}
            variant="contained"
            disabled={!createForm.asn || !createForm.vehicle_number || !createForm.driver_name}
          >
            Create Queue Entry
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default GateQueue;
