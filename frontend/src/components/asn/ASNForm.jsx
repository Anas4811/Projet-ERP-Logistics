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
import api from '../../services/api';

const ASNForm = () => {
  const navigate = useNavigate();
  const { id } = useParams();
  const isEditing = Boolean(id);

  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [purchaseOrders, setPurchaseOrders] = useState([]);
  const [itemDialogOpen, setItemDialogOpen] = useState(false);
  const [editingItem, setEditingItem] = useState(null);
  // ASN state for editing

  // Form state
  const [formData, setFormData] = useState({
    purchase_order: '',
    expected_ship_date: new Date().toISOString().split('T')[0],
    expected_arrival_date: '',
    carrier_name: '',
    tracking_number: '',
    vehicle_number: '',
    driver_name: '',
    driver_phone: '',
    notes: '',
    special_instructions: '',
  });

  // Items state
  const [asnItems, setAsnItems] = useState([]);

  // Item form state
  const [itemForm, setItemForm] = useState({
    purchase_order_item: '',
    quantity_expected: '',
    item_code: '',
    item_description: '',
    unit_price: '',
    batch_number: '',
    expiry_date: '',
    notes: '',
  });

  const fetchASN = useCallback(async () => {
    try {
      setLoading(true);
      const response = await api.get(`/asns/${id}/`);
      const asnData = response.data;

      // Set form data
      const formFields = [
        'purchase_order', 'expected_ship_date', 'expected_arrival_date',
        'carrier_name', 'tracking_number', 'vehicle_number', 'driver_name',
        'driver_phone', 'notes', 'special_instructions'
      ];

      const newFormData = {};
      formFields.forEach(field => {
        if (asnData[field] !== undefined) {
          newFormData[field] = asnData[field] || '';
        }
      });
      setFormData(newFormData);

      // Set items
      setAsnItems(asnData.items || []);
    } catch (error) {
      console.error('Error fetching ASN:', error);
      setError('Failed to load ASN');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchPurchaseOrders();
    if (isEditing) {
      fetchASN();
    }
  }, [isEditing, fetchASN]);

  const fetchPurchaseOrders = async () => {
    try {
      const response = await api.get('/purchase-orders/', {
        params: { status: 'APPROVED' }
      });
      setPurchaseOrders(response.data.results || response.data);
    } catch (error) {
      console.error('Error fetching POs:', error);
    }
  };

  const handleFormChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value,
    }));
  };

  const handlePOChange = async (poId) => {
    setFormData(prev => ({
      ...prev,
      purchase_order: poId,
    }));

    if (poId) {
      try {
        const response = await api.get(`/purchase-orders/${poId}/`);
        const po = response.data;

        // Auto-populate items from PO if not editing
        if (!isEditing && po.items) {
          const autoItems = po.items.map(poItem => ({
            purchase_order_item: poItem.id,
            quantity_expected: poItem.quantity_ordered - poItem.quantity_received,
            item_code: poItem.item_code,
            item_description: poItem.item_description,
            unit_price: poItem.unit_price,
            batch_number: '',
            expiry_date: '',
            notes: '',
          }));
          setAsnItems(autoItems);
        }
      } catch (error) {
        console.error('Error fetching PO details:', error);
      }
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError('');

    try {
      const submitData = {
        ...formData,
        items: asnItems,
      };

      if (isEditing) {
        await api.put(`/asns/${id}/`, submitData);
      } else {
        await api.post('/asns/', submitData);
      }

      navigate('/asn');
    } catch (error) {
      console.error('Error saving ASN:', error);
      if (error.response?.data) {
        setError(Object.values(error.response.data).flat().join(', '));
      } else {
        setError('Failed to save ASN');
      }
    } finally {
      setSaving(false);
    }
  };

  const handleAddItem = () => {
    setEditingItem(null);
    setItemForm({
      purchase_order_item: '',
      quantity_expected: '',
      item_code: '',
      item_description: '',
      unit_price: '',
      batch_number: '',
      expiry_date: '',
      notes: '',
    });
    setItemDialogOpen(true);
  };

  const handleEditItem = (item) => {
    setEditingItem(item);
    setItemForm({
      purchase_order_item: item.purchase_order_item || '',
      quantity_expected: item.quantity_expected || '',
      item_code: item.item_code || '',
      item_description: item.item_description || '',
      unit_price: item.unit_price || '',
      batch_number: item.batch_number || '',
      expiry_date: item.expiry_date || '',
      notes: item.notes || '',
    });
    setItemDialogOpen(true);
  };

  const handleDeleteItem = (index) => {
    const newItems = [...asnItems];
    newItems.splice(index, 1);
    setAsnItems(newItems);
  };

  const handleSaveItem = () => {
    if (!itemForm.item_code || !itemForm.item_description || !itemForm.quantity_expected) {
      return;
    }

    const newItem = {
      ...itemForm,
      quantity_expected: parseFloat(itemForm.quantity_expected),
      unit_price: itemForm.unit_price ? parseFloat(itemForm.unit_price) : 0,
    };

    if (editingItem) {
      const index = asnItems.findIndex(item => item === editingItem);
      if (index !== -1) {
        const updatedItems = [...asnItems];
        updatedItems[index] = newItem;
        setAsnItems(updatedItems);
      }
    } else {
      setAsnItems([...asnItems, newItem]);
    }

    setItemDialogOpen(false);
  };

  const calculateTotalQuantity = () => {
    return asnItems.reduce((total, item) => total + item.quantity_expected, 0);
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
          onClick={() => navigate('/asn')}
          sx={{ mr: 2 }}
        >
          Back to ASNs
        </Button>
        <Typography variant="h4" component="h1">
          {isEditing ? 'Edit ASN' : 'Create ASN'}
        </Typography>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      <form onSubmit={handleSubmit}>
        <Grid container spacing={3}>
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  ASN Details
                </Typography>
                <Grid container spacing={2}>
                  <Grid item xs={12} sm={6}>
                    <FormControl fullWidth required>
                      <InputLabel>Purchase Order</InputLabel>
                      <Select
                        name="purchase_order"
                        value={formData.purchase_order}
                        onChange={(e) => handlePOChange(e.target.value)}
                        label="Purchase Order"
                        disabled={isEditing}
                      >
                        {purchaseOrders.map((po) => (
                          <MenuItem key={po.id} value={po.id}>
                            {po.po_number} - {po.vendor_name}
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      label="Carrier Name"
                      name="carrier_name"
                      value={formData.carrier_name}
                      onChange={handleFormChange}
                    />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      label="Expected Ship Date"
                      name="expected_ship_date"
                      type="date"
                      value={formData.expected_ship_date}
                      onChange={handleFormChange}
                      InputLabelProps={{ shrink: true }}
                      required
                    />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      label="Expected Arrival Date"
                      name="expected_arrival_date"
                      type="date"
                      value={formData.expected_arrival_date}
                      onChange={handleFormChange}
                      InputLabelProps={{ shrink: true }}
                      required
                    />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      label="Tracking Number"
                      name="tracking_number"
                      value={formData.tracking_number}
                      onChange={handleFormChange}
                    />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      label="Vehicle Number"
                      name="vehicle_number"
                      value={formData.vehicle_number}
                      onChange={handleFormChange}
                    />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      label="Driver Name"
                      name="driver_name"
                      value={formData.driver_name}
                      onChange={handleFormChange}
                    />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      label="Driver Phone"
                      name="driver_phone"
                      value={formData.driver_phone}
                      onChange={handleFormChange}
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
                      onChange={handleFormChange}
                    />
                  </Grid>
                  <Grid item xs={12}>
                    <TextField
                      fullWidth
                      label="Notes"
                      name="notes"
                      multiline
                      rows={2}
                      value={formData.notes}
                      onChange={handleFormChange}
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
                    Shipment Items ({asnItems.length}) - Total Quantity: {calculateTotalQuantity()}
                  </Typography>
                  <Button
                    variant="contained"
                    startIcon={<Add />}
                    onClick={handleAddItem}
                  >
                    Add Item
                  </Button>
                </Box>

                {asnItems.length === 0 ? (
                  <Typography color="text.secondary" sx={{ textAlign: 'center', py: 4 }}>
                    No items added yet. Click "Add Item" to get started.
                  </Typography>
                ) : (
                  <TableContainer component={MuiPaper} variant="outlined">
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell>Item Code</TableCell>
                          <TableCell>Description</TableCell>
                          <TableCell align="right">Quantity</TableCell>
                          <TableCell align="right">Unit Price</TableCell>
                          <TableCell>Batch/Lot</TableCell>
                          <TableCell align="right">Actions</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {asnItems.map((item, index) => (
                          <TableRow key={index}>
                            <TableCell>{item.item_code}</TableCell>
                            <TableCell>{item.item_description}</TableCell>
                            <TableCell align="right">{item.quantity_expected}</TableCell>
                            <TableCell align="right">${item.unit_price?.toFixed(2)}</TableCell>
                            <TableCell>{item.batch_number || 'N/A'}</TableCell>
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
            disabled={saving || asnItems.length === 0}
            size="large"
          >
            {saving ? 'Saving...' : 'Save ASN'}
          </Button>
          <Button
            variant="outlined"
            onClick={() => navigate('/asn')}
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
                label="Quantity Expected"
                type="number"
                value={itemForm.quantity_expected}
                onChange={(e) => setItemForm({ ...itemForm, quantity_expected: e.target.value })}
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
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Batch/Lot Number"
                value={itemForm.batch_number}
                onChange={(e) => setItemForm({ ...itemForm, batch_number: e.target.value })}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Expiry Date"
                type="date"
                value={itemForm.expiry_date}
                onChange={(e) => setItemForm({ ...itemForm, expiry_date: e.target.value })}
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
            disabled={!itemForm.item_code || !itemForm.item_description || !itemForm.quantity_expected}
          >
            {editingItem ? 'Update Item' : 'Add Item'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default ASNForm;
