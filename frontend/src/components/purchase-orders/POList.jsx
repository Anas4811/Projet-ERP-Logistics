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
  ShoppingCart,
  Warning,
} from '@mui/icons-material';
import api from '../../services/api';

const POList = () => {
  const navigate = useNavigate();
  const [purchaseOrders, setPurchaseOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [vendorFilter, setVendorFilter] = useState('');
  const [vendors, setVendors] = useState([]);

  const fetchPurchaseOrders = useCallback(async () => {
    try {
      setLoading(true);
      const params = {};
      if (searchTerm) params.search = searchTerm;
      if (statusFilter) params.status = statusFilter;
      if (vendorFilter) params.vendor = vendorFilter;

      const response = await api.get('/purchase-orders/', { params });
      setPurchaseOrders(response.data.results || response.data);
    } catch (error) {
      console.error('Error fetching purchase orders:', error);
      setError('Failed to load purchase orders');
    } finally {
      setLoading(false);
    }
  }, [searchTerm, statusFilter, vendorFilter]);

  useEffect(() => {
    fetchPurchaseOrders();
    fetchVendors();
  }, [fetchPurchaseOrders]);

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
      case 'DRAFT':
        return 'default';
      case 'PENDING_APPROVAL':
        return 'warning';
      case 'APPROVED':
        return 'info';
      case 'ORDERED':
        return 'primary';
      case 'PARTIALLY_RECEIVED':
        return 'secondary';
      case 'RECEIVED':
        return 'success';
      case 'REJECTED':
        return 'error';
      case 'CANCELLED':
        return 'error';
      default:
        return 'default';
    }
  };

  const getPriorityColor = (priority) => {
    switch (priority) {
      case 'LOW':
        return 'success';
      case 'MEDIUM':
        return 'warning';
      case 'HIGH':
        return 'error';
      case 'URGENT':
        return 'error';
      default:
        return 'default';
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
          Purchase Orders Management
        </Typography>
        <Button
          variant="contained"
          startIcon={<Add />}
          onClick={() => navigate('/purchase-orders/create')}
        >
          Create Purchase Order
        </Button>
      </Box>

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} md={4}>
              <TextField
                fullWidth
                placeholder="Search POs by number, vendor..."
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
                  <MenuItem value="DRAFT">Draft</MenuItem>
                  <MenuItem value="PENDING_APPROVAL">Pending Approval</MenuItem>
                  <MenuItem value="APPROVED">Approved</MenuItem>
                  <MenuItem value="ORDERED">Ordered</MenuItem>
                  <MenuItem value="PARTIALLY_RECEIVED">Partially Received</MenuItem>
                  <MenuItem value="RECEIVED">Received</MenuItem>
                  <MenuItem value="REJECTED">Rejected</MenuItem>
                  <MenuItem value="CANCELLED">Cancelled</MenuItem>
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

      {purchaseOrders.length === 0 ? (
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <ShoppingCart sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
          <Typography variant="h6" color="text.secondary">
            No purchase orders found
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            {searchTerm || statusFilter || vendorFilter ? 'Try adjusting your filters' : 'Start by creating your first purchase order'}
          </Typography>
          <Button
            variant="contained"
            startIcon={<Add />}
            onClick={() => navigate('/purchase-orders/create')}
          >
            Create Purchase Order
          </Button>
        </Paper>
      ) : (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>PO Number</TableCell>
                <TableCell>Vendor</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Priority</TableCell>
                <TableCell>Order Date</TableCell>
                <TableCell>Expected Delivery</TableCell>
                <TableCell align="right">Total Amount</TableCell>
                <TableCell>Issues</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {purchaseOrders.map((po) => (
                <TableRow key={po.id} hover>
                  <TableCell>
                    <Box>
                      <Typography variant="subtitle2" sx={{ fontWeight: 'bold' }}>
                        {po.po_number}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {po.item_count} items
                      </Typography>
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2">
                      {po.vendor_name}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={po.status.replace('_', ' ')}
                      size="small"
                      color={getStatusColor(po.status)}
                      variant="outlined"
                    />
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={po.priority}
                      size="small"
                      color={getPriorityColor(po.priority)}
                      variant="filled"
                    />
                  </TableCell>
                  <TableCell>
                    {new Date(po.order_date).toLocaleDateString()}
                  </TableCell>
                  <TableCell>
                    {po.expected_delivery_date ? (
                      <Box>
                        <Typography variant="body2">
                          {new Date(po.expected_delivery_date).toLocaleDateString()}
                        </Typography>
                        {po.is_overdue && (
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
                  <TableCell align="right">
                    <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                      ${po.total_amount?.toFixed(2)}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    {po.is_overdue && (
                      <Warning sx={{ color: 'error.main', fontSize: 20 }} />
                    )}
                  </TableCell>
                  <TableCell align="right">
                    <IconButton
                      size="small"
                      onClick={() => navigate(`/purchase-orders/${po.id}`)}
                      color="primary"
                      title="View Details"
                    >
                      <Visibility />
                    </IconButton>
                    <IconButton
                      size="small"
                      onClick={() => navigate(`/purchase-orders/${po.id}/edit`)}
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
          Showing {purchaseOrders.length} purchase orders
        </Typography>
      </Box>
    </Box>
  );
};

export default POList;
