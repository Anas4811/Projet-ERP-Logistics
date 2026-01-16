import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Grid,
  IconButton,
  InputAdornment,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
  Alert,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from '@mui/material';
import {
  Add,
  Search,
  Edit,
  Visibility,
  LocalShipping,
  Warning,
  CheckCircle,
  Schedule,
} from '@mui/icons-material';
import api from '../../services/api';

const ASNList = () => {
  const navigate = useNavigate();
  const [asns, setAsns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [vendorFilter, setVendorFilter] = useState('');
  const [vendors, setVendors] = useState([]);

  const fetchASNs = useCallback(async () => {
    try {
      setLoading(true);
      const params = {};
      if (searchTerm) params.search = searchTerm;
      if (statusFilter) params.status = statusFilter;
      if (vendorFilter) params.vendor = vendorFilter;

      const response = await api.get('/asns/', { params });
      setAsns(response.data.results || response.data);
    } catch (error) {
      console.error('Error fetching ASNs:', error);
      setError('Failed to load ASNs');
    } finally {
      setLoading(false);
    }
  }, [searchTerm, statusFilter, vendorFilter]);

  useEffect(() => {
    fetchASNs();
    fetchVendors();
  }, [fetchASNs]);

  const fetchVendors = async () => {
    try {
      const response = await api.get('/vendors/');
      setVendors(response.data.results || response.data);
    } catch (error) {
      console.error('Error fetching vendors:', error);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'CREATED':
        return 'default';
      case 'APPROVED':
        return 'info';
      case 'IN_TRANSIT':
        return 'primary';
      case 'ARRIVED':
        return 'warning';
      case 'RECEIVED':
        return 'success';
      case 'CANCELLED':
        return 'error';
      case 'REJECTED':
        return 'error';
      default:
        return 'default';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'CREATED':
        return <Schedule sx={{ fontSize: 16 }} />;
      case 'APPROVED':
        return <CheckCircle sx={{ fontSize: 16 }} />;
      case 'IN_TRANSIT':
        return <LocalShipping sx={{ fontSize: 16 }} />;
      case 'ARRIVED':
        return <Warning sx={{ fontSize: 16 }} />;
      case 'RECEIVED':
        return <CheckCircle sx={{ fontSize: 16 }} />;
      default:
        return null;
    }
  };

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
          ASN & Shipment Tracking
        </Typography>
        <Button
          variant="contained"
          startIcon={<Add />}
          onClick={() => navigate('/asn/create')}
        >
          Create ASN
        </Button>
      </Box>

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} md={4}>
              <TextField
                fullWidth
                placeholder="Search ASNs by number, PO, vendor..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <Search />
                    </InputAdornment>
                  ),
                }}
              />
            </Grid>
            <Grid item xs={12} md={3}>
              <FormControl fullWidth>
                <InputLabel>Status</InputLabel>
                <Select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  label="Status"
                >
                  <MenuItem value="">All Statuses</MenuItem>
                  <MenuItem value="CREATED">Created</MenuItem>
                  <MenuItem value="APPROVED">Approved</MenuItem>
                  <MenuItem value="IN_TRANSIT">In Transit</MenuItem>
                  <MenuItem value="ARRIVED">Arrived</MenuItem>
                  <MenuItem value="RECEIVED">Received</MenuItem>
                  <MenuItem value="CANCELLED">Cancelled</MenuItem>
                  <MenuItem value="REJECTED">Rejected</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} md={3}>
              <FormControl fullWidth>
                <InputLabel>Vendor</InputLabel>
                <Select
                  value={vendorFilter}
                  onChange={(e) => setVendorFilter(e.target.value)}
                  label="Vendor"
                >
                  <MenuItem value="">All Vendors</MenuItem>
                  {vendors.map((vendor) => (
                    <MenuItem key={vendor.id} value={vendor.id}>
                      {vendor.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} md={2}>
              <Button
                fullWidth
                variant="outlined"
                onClick={() => {
                  setSearchTerm('');
                  setStatusFilter('');
                  setVendorFilter('');
                }}
              >
                Clear Filters
              </Button>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {asns.length === 0 ? (
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <LocalShipping sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
          <Typography variant="h6" color="text.secondary">
            No ASNs found
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            {searchTerm || statusFilter || vendorFilter ? 'Try adjusting your filters' : 'Start by creating your first ASN'}
          </Typography>
          <Button
            variant="contained"
            startIcon={<Add />}
            onClick={() => navigate('/asn/create')}
          >
            Create ASN
          </Button>
        </Paper>
      ) : (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>ASN Number</TableCell>
                <TableCell>PO Number</TableCell>
                <TableCell>Vendor</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Carrier</TableCell>
                <TableCell>Expected Arrival</TableCell>
                <TableCell>Actual Arrival</TableCell>
                <TableCell align="right">Items</TableCell>
                <TableCell align="right">Quantity</TableCell>
                <TableCell>Issues</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {asns.map((asn) => (
                <TableRow key={asn.id} hover>
                  <TableCell>
                    <Box>
                      <Typography variant="subtitle2" sx={{ fontWeight: 'bold' }}>
                        {asn.asn_number}
                      </Typography>
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2">
                      {asn.po_number}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2">
                      {asn.vendor_name}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={asn.status.replace('_', ' ')}
                      size="small"
                      color={getStatusColor(asn.status)}
                      variant="outlined"
                      icon={getStatusIcon(asn.status)}
                    />
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2">
                      {asn.carrier_name || 'N/A'}
                    </Typography>
                    {asn.tracking_number && (
                      <Typography variant="caption" color="text.secondary">
                        {asn.tracking_number}
                      </Typography>
                    )}
                  </TableCell>
                  <TableCell>
                    {asn.expected_arrival_date ? (
                      <Box>
                        <Typography variant="body2">
                          {new Date(asn.expected_arrival_date).toLocaleDateString()}
                        </Typography>
                        {asn.is_overdue && (
                          <Typography variant="caption" color="error">
                            Overdue
                          </Typography>
                        )}
                      </Box>
                    ) : (
                      <Typography variant="body2" color="text.secondary">
                        Not set
                      </Typography>
                    )}
                  </TableCell>
                  <TableCell>
                    {asn.actual_arrival_date ? (
                      <Typography variant="body2">
                        {new Date(asn.actual_arrival_date).toLocaleDateString()}
                      </Typography>
                    ) : (
                      <Typography variant="body2" color="text.secondary">
                        Pending
                      </Typography>
                    )}
                  </TableCell>
                  <TableCell align="right">
                    <Typography variant="body2">
                      {asn.total_items}
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    <Typography variant="body2">
                      {asn.total_quantity}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    {asn.is_overdue && (
                      <Warning sx={{ color: 'error.main', fontSize: 20 }} />
                    )}
                  </TableCell>
                  <TableCell align="right">
                    <IconButton
                      size="small"
                      onClick={() => navigate(`/asn/${asn.id}`)}
                      color="primary"
                      title="View Details"
                    >
                      <Visibility />
                    </IconButton>
                    <IconButton
                      size="small"
                      onClick={() => navigate(`/asn/${asn.id}/edit`)}
                      color="secondary"
                      title="Edit"
                    >
                      <Edit />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      <Box sx={{ mt: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="body2" color="text.secondary">
          Showing {asns.length} ASNs
        </Typography>
      </Box>
    </Box>
  );
};

export default ASNList;
