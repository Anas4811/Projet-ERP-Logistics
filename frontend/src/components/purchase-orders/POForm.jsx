import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  Box,
  Button,
  Card,
  CardContent,
  Grid,
  TextField,
  Typography,
  Alert,
  CircularProgress,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper as MuiPaper,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material';
import {
  Save,
  ArrowBack,
  Add,
  Delete,
  Edit,
} from '@mui/icons-material';
// Form validation will be handled manually for now
import api from '../../services/api';

// Form validation will be handled in handleSubmit

const POForm = () => {
  const navigate = useNavigate();
  const { id } = useParams();
  const isEditing = Boolean(id);

  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [vendors, setVendors] = useState([]);
  const [lineItems, setLineItems] = useState([]);
  const [itemDialogOpen, setItemDialogOpen] = useState(false);
  const [editingItem, setEditingItem] = useState(null);

  // Item form state
  const [itemForm, setItemForm] = useState({
    item_code: '',
    item_description: '',
    quantity_ordered: '',
    unit_price: '',
    expected_delivery_date: '',
    notes: '',
  });

  useEffect(() => {
    fetchVendors();
    if (isEditing) {
      fetchPO();
    }
  }, [id]);

  const fetchVendors = async () => {
    try {
      const response = await api.get('/vendors/');
      setVendors(response.data.results || response.data);
    } catch (error) {
      console.error('Error fetching vendors:', error);
    }
  };

  const fetchPO = useCallback(async () => {
    try {
      setLoading(true);
      const response = await api.get(`/purchase-orders/${id}/`);
      const poData = response.data;

      // Set form data
      const newFormData = {};
      Object.keys(poData).forEach(key => {
        if (key !== 'items' && key !== 'vendor_name') {
          newFormData[key] = poData[key] || '';
        }
      });

      // Set vendor
      if (poData.vendor) {
        newFormData.vendor = poData.vendor;
      }

      setFormData(newFormData);

      // Set line items
      setLineItems(poData.items || []);
    } catch (error) {
      console.error('Error fetching PO:', error);
      setError('Failed to load purchase order');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchVendors();
    if (isEditing) {
      fetchPO();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isEditing, fetchPO]);

// Form state management
  const [formData, setFormData] = useState({
    vendor: '',
    order_date: new Date().toISOString().split('T')[0],
    expected_delivery_date: '',
    priority: 'MEDIUM',
    shipping_address: '',
    special_instructions: '',
    internal_notes: '',
  });

  const [formErrors, setFormErrors] = useState({});

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value,
    }));
    // Clear error when user starts typing
    if (formErrors[name]) {
      setFormErrors(prev => ({
        ...prev,
        [name]: '',
      }));
    }
  };

  const handleFormSubmit = async (e) => {
    e.preventDefault();

    // Basic validation
    const errors = {};
    if (!formData.vendor) errors.vendor = 'Vendor is required';
    if (!formData.order_date) errors.order_date = 'Order date is required';
    if (!formData.priority) errors.priority = 'Priority is required';
    if (lineItems.length === 0) {
      setError('Please add at least one line item');
      return;
    }

    if (Object.keys(errors).length > 0) {
      setFormErrors(errors);
      return;
    }

    setSaving(true);
    setError('');
    setFormErrors({});

    try {
      const submitData = {
        ...formData,
        items: lineItems,
      };

      if (isEditing) {
        await api.put(`/purchase-orders/${id}/`, submitData);
      } else {
        await api.post('/purchase-orders/', submitData);
      }

      navigate('/purchase-orders');
    } catch (error) {
      console.error('Error saving PO:', error);
      if (error.response?.data) {
        setError(Object.values(error.response.data).flat().join(', '));
      } else {
        setError('Failed to save purchase order');
      }
    } finally {
      setSaving(false);
    }
  };

  const handleAddItem = () => {
    setEditingItem(null);
    setItemForm({
      item_code: '',
      item_description: '',
      quantity_ordered: '',
      unit_price: '',
      expected_delivery_date: '',
      notes: '',
    });
    setItemDialogOpen(true);
  };

  const handleEditItem = (item) => {
    setEditingItem(item);
    setItemForm({
      item_code: item.item_code || '',
      item_description: item.item_description || '',
      quantity_ordered: item.quantity_ordered || '',
      unit_price: item.unit_price || '',
      expected_delivery_date: item.expected_delivery_date || '',
      notes: item.notes || '',
    });
    setItemDialogOpen(true);
  };

  const handleDeleteItem = (index) => {
    const newItems = [...lineItems];
    newItems.splice(index, 1);
    setLineItems(newItems);
  };

  const handleSaveItem = () => {
    if (!itemForm.item_code || !itemForm.item_description || !itemForm.quantity_ordered || !itemForm.unit_price) {
      return;
    }

    const newItem = {
      ...itemForm,
      quantity_ordered: parseFloat(itemForm.quantity_ordered),
      unit_price: parseFloat(itemForm.unit_price),
    };

    if (editingItem) {
      const index = lineItems.findIndex(item => item === editingItem);
      if (index !== -1) {
        const updatedItems = [...lineItems];
        updatedItems[index] = newItem;
        setLineItems(updatedItems);
      }
    } else {
      setLineItems([...lineItems, newItem]);
    }

    setItemDialogOpen(false);
  };

  const calculateTotal = () => {
    return lineItems.reduce((total, item) => {
      return total + (item.quantity_ordered * item.unit_price);
    }, 0);
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <Button
          startIcon={<ArrowBack />}
          onClick={() => navigate('/purchase-orders')}
          sx={{ mr: 2 }}
        >
          Back to Purchase Orders
        </Button>
        <Typography variant="h4" component="h1">
          {isEditing ? 'Edit Purchase Order' : 'Create Purchase Order'}
        </Typography>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      <form onSubmit={handleFormSubmit}>
        <Grid container spacing={3}>
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Purchase Order Details
                </Typography>
                <Grid container spacing={2}>
                  <Grid item xs={12} sm={6}>
                    <FormControl fullWidth required error={Boolean(formErrors.vendor)}>
                      <InputLabel>Vendor</InputLabel>
                      <Select
                        name="vendor"
                        value={formData.vendor}
                        onChange={handleChange}
                      >
                        {vendors.map((vendor) => (
                          <MenuItem key={vendor.id} value={vendor.id}>
                            {vendor.name} ({vendor.vendor_code})
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <FormControl fullWidth required error={Boolean(formErrors.priority)}>
                      <InputLabel>Priority</InputLabel>
                      <Select
                        name="priority"
                        value={formData.priority}
                        onChange={handleChange}
                      >
                        <MenuItem value="LOW">Low</MenuItem>
                        <MenuItem value="MEDIUM">Medium</MenuItem>
                        <MenuItem value="HIGH">High</MenuItem>
                        <MenuItem value="URGENT">Urgent</MenuItem>
                      </Select>
                    </FormControl>
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      label="Order Date"
                      name="order_date"
                      type="date"
                      value={formData.order_date}
                      onChange={handleChange}
                      error={Boolean(formErrors.order_date)}
                      helperText={formErrors.order_date}
                      InputLabelProps={{ shrink: true }}
                      required
                    />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      label="Expected Delivery Date"
                      name="expected_delivery_date"
                      type="date"
                      value={formData.expected_delivery_date}
                      onChange={handleChange}
                      error={Boolean(formErrors.expected_delivery_date)}
                      helperText={formErrors.expected_delivery_date}
                      InputLabelProps={{ shrink: true }}
                    />
                  </Grid>
                  <Grid item xs={12}>
                    <TextField
                      fullWidth
                      label="Shipping Address"
                      name="shipping_address"
                      multiline
                      rows={2}
                      value={formData.shipping_address}
                      onChange={handleChange}
                    />
                  </Grid>
                  <Grid item xs={12}>
                    <TextField
                      fullWidth
                      label="Special Instructions"
                      name="special_instructions"
                      multiline
                      rows={2}
                      value={formData.special_instructions}
                      onChange={handleChange}
                    />
                  </Grid>
                  <Grid item xs={12}>
                    <TextField
                      fullWidth
                      label="Internal Notes"
                      name="internal_notes"
                      multiline
                      rows={2}
                      value={formData.internal_notes}
                      onChange={handleChange}
                    />
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                  <Typography variant="h6">
                    Line Items ({lineItems.length})
                  </Typography>
                  <Button
                    variant="contained"
                    startIcon={<Add />}
                    onClick={handleAddItem}
                  >
                    Add Item
                  </Button>
                </Box>

                {lineItems.length === 0 ? (
                  <Typography color="text.secondary" sx={{ textAlign: 'center', py: 4 }}>
                    No items added yet. Click "Add Item" to get started.
                  </Typography>
                ) : (
                  <TableContainer component={MuiPaper} variant="outlined">
                    <Table>
                      <TableHead>
                        <TableRow>
                          <TableCell>Item Code</TableCell>
                          <TableCell>Description</TableCell>
                          <TableCell align="right">Quantity</TableCell>
                          <TableCell align="right">Unit Price</TableCell>
                          <TableCell align="right">Total</TableCell>
                          <TableCell align="right">Actions</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {lineItems.map((item, index) => (
                          <TableRow key={index}>
                            <TableCell>{item.item_code}</TableCell>
                            <TableCell>{item.item_description}</TableCell>
                            <TableCell align="right">{item.quantity_ordered}</TableCell>
                            <TableCell align="right">${item.unit_price?.toFixed(2)}</TableCell>
                            <TableCell align="right">
                              ${(item.quantity_ordered * item.unit_price)?.toFixed(2)}
                            </TableCell>
                            <TableCell align="right">
                              <IconButton size="small" onClick={() => handleEditItem(item)}>
                                <Edit />
                              </IconButton>
                              <IconButton size="small" onClick={() => handleDeleteItem(index)}>
                                <Delete />
                              </IconButton>
                            </TableCell>
                          </TableRow>
                        ))}
                        <TableRow>
                          <TableCell colSpan={4} align="right">
                            <strong>Total:</strong>
                          </TableCell>
                          <TableCell align="right">
                            <strong>${calculateTotal().toFixed(2)}</strong>
                          </TableCell>
                          <TableCell />
                        </TableRow>
                      </TableBody>
                    </Table>
                  </TableContainer>
                )}
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        <Box sx={{ mt: 3, display: 'flex', gap: 2 }}>
          <Button
            type="submit"
            variant="contained"
            startIcon={saving ? <CircularProgress size={20} /> : <Save />}
            disabled={saving}
            size="large"
          >
            {saving ? 'Saving...' : 'Save Purchase Order'}
          </Button>
          <Button
            variant="outlined"
            onClick={() => navigate('/purchase-orders')}
            disabled={saving}
            size="large"
          >
            Cancel
          </Button>
        </Box>
      </form>

      {/* Item Dialog */}
      <Dialog open={itemDialogOpen} onClose={() => setItemDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>
          {editingItem ? 'Edit Item' : 'Add Item'}
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Item Code"
                value={itemForm.item_code}
                onChange={(e) => setItemForm({ ...itemForm, item_code: e.target.value })}
                required
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Quantity Ordered"
                type="number"
                value={itemForm.quantity_ordered}
                onChange={(e) => setItemForm({ ...itemForm, quantity_ordered: e.target.value })}
                required
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Item Description"
                value={itemForm.item_description}
                onChange={(e) => setItemForm({ ...itemForm, item_description: e.target.value })}
                required
                multiline
                rows={2}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Unit Price"
                type="number"
                step="0.01"
                value={itemForm.unit_price}
                onChange={(e) => setItemForm({ ...itemForm, unit_price: e.target.value })}
                required
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Expected Delivery Date"
                type="date"
                value={itemForm.expected_delivery_date}
                onChange={(e) => setItemForm({ ...itemForm, expected_delivery_date: e.target.value })}
                InputLabelProps={{ shrink: true }}
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Notes"
                value={itemForm.notes}
                onChange={(e) => setItemForm({ ...itemForm, notes: e.target.value })}
                multiline
                rows={2}
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setItemDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleSaveItem}
            variant="contained"
            disabled={!itemForm.item_code || !itemForm.item_description || !itemForm.quantity_ordered || !itemForm.unit_price}
          >
            {editingItem ? 'Update Item' : 'Add Item'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default POForm;
