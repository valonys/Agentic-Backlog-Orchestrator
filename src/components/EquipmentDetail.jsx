import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Grid,
  Box,
  Typography,
  Paper,
  Divider,
  Chip,
  Alert,
  CircularProgress,
  Tabs,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton
} from '@mui/material';
import {
  Save as SaveIcon,
  Close as CloseIcon,
  Add as AddIcon,
  Edit as EditIcon
} from '@mui/icons-material';

const API_URL = import.meta.env.VITE_API_URL || (import.meta.env.DEV ? 'http://localhost:8000' : '');

function EquipmentDetail({ open, tagId, onClose, onSave }) {
  const [equipment, setEquipment] = useState(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [editing, setEditing] = useState(false);
  const [activeTab, setActiveTab] = useState(0);
  const [formData, setFormData] = useState({
    tag_id: tagId || '',
    functional_location: '',
    equipment_category: '',
    description: '',
    system: '',
    location: '',
    manufacturing_details: '',
    fluid_service: '',
    backlog_tracker: '',
    inspections_done: '',
    history_comments: ''
  });
  const [newInspection, setNewInspection] = useState({
    inspection_date: '',
    inspection_type: '',
    result: '',
    inspector: '',
    notes: ''
  });

  useEffect(() => {
    if (open && tagId) {
      loadEquipment();
    }
  }, [open, tagId]);

  const loadEquipment = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await axios.get(`${API_URL}/equipment/${encodeURIComponent(tagId)}`);
      const data = res.data;
      setEquipment(data);
      
      // Populate form with equipment data
      setFormData({
        tag_id: data.equipment.tag_id || tagId,
        functional_location: data.equipment.functional_location || '',
        equipment_category: data.equipment.equipment_category || '',
        description: data.equipment.description || '',
        system: data.equipment.system || '',
        location: data.equipment.location || '',
        manufacturing_details: data.equipment.manufacturing_details || '',
        fluid_service: data.equipment.fluid_service || '',
        backlog_tracker: data.equipment.backlog_tracker || '',
        inspections_done: data.equipment.inspections_done || '',
        history_comments: data.equipment.history_comments || ''
      });
    } catch (err) {
      if (err.response?.status === 404) {
        // Equipment doesn't exist yet, initialize with tag_id
        setFormData(prev => ({ ...prev, tag_id: tagId }));
        setEditing(true);
      } else {
        setError(err.response?.data?.detail || err.message || 'Failed to load equipment');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setSuccess(null);
    
    try {
      await axios.post(`${API_URL}/equipment`, formData);
      setSuccess('Equipment data saved successfully');
      setEditing(false);
      await loadEquipment();
      if (onSave) onSave();
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to save equipment');
    } finally {
      setSaving(false);
    }
  };

  const handleAddInspection = async () => {
    if (!newInspection.inspection_date) {
      setError('Inspection date is required');
      return;
    }
    
    setSaving(true);
    setError(null);
    
    try {
      await axios.post(`${API_URL}/equipment/${encodeURIComponent(tagId)}/inspection`, {
        ...newInspection,
        tag_id: tagId
      });
      setSuccess('Inspection record added successfully');
      setNewInspection({
        inspection_date: '',
        inspection_type: '',
        result: '',
        inspector: '',
        notes: ''
      });
      await loadEquipment();
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to add inspection');
    } finally {
      setSaving(false);
    }
  };

  const handleInputChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  if (!open) return null;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="lg" fullWidth>
      <DialogTitle>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Typography variant="h6">Equipment Details - {tagId}</Typography>
          <Box>
            {!editing && (
              <IconButton onClick={() => setEditing(true)} size="small" sx={{ mr: 1 }}>
                <EditIcon />
              </IconButton>
            )}
            <IconButton onClick={onClose} size="small">
              <CloseIcon />
            </IconButton>
          </Box>
        </Box>
      </DialogTitle>
      
      <DialogContent>
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
            <CircularProgress />
          </Box>
        ) : (
          <>
            {error && (
              <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
                {error}
              </Alert>
            )}
            
            {success && (
              <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess(null)}>
                {success}
              </Alert>
            )}

            <Tabs value={activeTab} onChange={(e, v) => setActiveTab(v)} sx={{ mb: 2 }}>
              <Tab label="Master Data" />
              <Tab label="Inspection History" />
              <Tab label="Status History" />
            </Tabs>

            {activeTab === 0 && (
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Tag ID"
                    value={formData.tag_id}
                    disabled
                    variant="outlined"
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Functional Location"
                    value={formData.functional_location}
                    onChange={(e) => handleInputChange('functional_location', e.target.value)}
                    disabled={!editing}
                    variant="outlined"
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Equipment Category"
                    value={formData.equipment_category}
                    onChange={(e) => handleInputChange('equipment_category', e.target.value)}
                    disabled={!editing}
                    variant="outlined"
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="System"
                    value={formData.system}
                    onChange={(e) => handleInputChange('system', e.target.value)}
                    disabled={!editing}
                    variant="outlined"
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Location"
                    value={formData.location}
                    onChange={(e) => handleInputChange('location', e.target.value)}
                    disabled={!editing}
                    variant="outlined"
                  />
                </Grid>
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label="Description"
                    value={formData.description}
                    onChange={(e) => handleInputChange('description', e.target.value)}
                    disabled={!editing}
                    multiline
                    rows={2}
                    variant="outlined"
                  />
                </Grid>
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label="Manufacturing Details"
                    value={formData.manufacturing_details}
                    onChange={(e) => handleInputChange('manufacturing_details', e.target.value)}
                    disabled={!editing}
                    multiline
                    rows={3}
                    variant="outlined"
                  />
                </Grid>
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label="Fluid Service"
                    value={formData.fluid_service}
                    onChange={(e) => handleInputChange('fluid_service', e.target.value)}
                    disabled={!editing}
                    multiline
                    rows={2}
                    variant="outlined"
                  />
                </Grid>
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label="Backlog Tracker"
                    value={formData.backlog_tracker}
                    onChange={(e) => handleInputChange('backlog_tracker', e.target.value)}
                    disabled={!editing}
                    multiline
                    rows={2}
                    variant="outlined"
                  />
                </Grid>
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label="Inspections Done"
                    value={formData.inspections_done}
                    onChange={(e) => handleInputChange('inspections_done', e.target.value)}
                    disabled={!editing}
                    multiline
                    rows={2}
                    variant="outlined"
                  />
                </Grid>
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label="History Comments"
                    value={formData.history_comments}
                    onChange={(e) => handleInputChange('history_comments', e.target.value)}
                    disabled={!editing}
                    multiline
                    rows={4}
                    variant="outlined"
                  />
                </Grid>
              </Grid>
            )}

            {activeTab === 1 && (
              <Box>
                <Paper sx={{ p: 2, mb: 2 }}>
                  <Typography variant="h6" gutterBottom>Add New Inspection</Typography>
                  <Grid container spacing={2}>
                    <Grid item xs={12} sm={6}>
                      <TextField
                        fullWidth
                        label="Inspection Date"
                        type="date"
                        value={newInspection.inspection_date}
                        onChange={(e) => setNewInspection(prev => ({ ...prev, inspection_date: e.target.value }))}
                        InputLabelProps={{ shrink: true }}
                      />
                    </Grid>
                    <Grid item xs={12} sm={6}>
                      <TextField
                        fullWidth
                        label="Inspection Type"
                        value={newInspection.inspection_type}
                        onChange={(e) => setNewInspection(prev => ({ ...prev, inspection_type: e.target.value }))}
                      />
                    </Grid>
                    <Grid item xs={12} sm={6}>
                      <TextField
                        fullWidth
                        label="Result"
                        value={newInspection.result}
                        onChange={(e) => setNewInspection(prev => ({ ...prev, result: e.target.value }))}
                      />
                    </Grid>
                    <Grid item xs={12} sm={6}>
                      <TextField
                        fullWidth
                        label="Inspector"
                        value={newInspection.inspector}
                        onChange={(e) => setNewInspection(prev => ({ ...prev, inspector: e.target.value }))}
                      />
                    </Grid>
                    <Grid item xs={12}>
                      <TextField
                        fullWidth
                        label="Notes"
                        value={newInspection.notes}
                        onChange={(e) => setNewInspection(prev => ({ ...prev, notes: e.target.value }))}
                        multiline
                        rows={2}
                      />
                    </Grid>
                    <Grid item xs={12}>
                      <Button
                        variant="contained"
                        startIcon={<AddIcon />}
                        onClick={handleAddInspection}
                        disabled={saving}
                      >
                        Add Inspection
                      </Button>
                    </Grid>
                  </Grid>
                </Paper>

                <TableContainer component={Paper}>
                  <Table>
                    <TableHead>
                      <TableRow>
                        <TableCell>Date</TableCell>
                        <TableCell>Type</TableCell>
                        <TableCell>Result</TableCell>
                        <TableCell>Inspector</TableCell>
                        <TableCell>Notes</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {equipment?.inspection_history?.length > 0 ? (
                        equipment.inspection_history.map((insp, idx) => (
                          <TableRow key={idx}>
                            <TableCell>{insp.inspection_date || 'N/A'}</TableCell>
                            <TableCell>{insp.inspection_type || 'N/A'}</TableCell>
                            <TableCell>
                              <Chip
                                label={insp.result || 'N/A'}
                                color={insp.result?.toLowerCase() === 'pass' ? 'success' : 'default'}
                                size="small"
                              />
                            </TableCell>
                            <TableCell>{insp.inspector || 'N/A'}</TableCell>
                            <TableCell>{insp.notes || 'N/A'}</TableCell>
                          </TableRow>
                        ))
                      ) : (
                        <TableRow>
                          <TableCell colSpan={5} align="center">
                            No inspection records found
                          </TableCell>
                        </TableRow>
                      )}
                    </TableBody>
                  </Table>
                </TableContainer>
              </Box>
            )}

            {activeTab === 2 && (
              <TableContainer component={Paper}>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Timestamp</TableCell>
                      <TableCell>Status</TableCell>
                      <TableCell>Note</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {equipment?.status_history?.length > 0 ? (
                      equipment.status_history.map((status, idx) => (
                        <TableRow key={idx}>
                          <TableCell>
                            {new Date(status.timestamp).toLocaleString()}
                          </TableCell>
                          <TableCell>
                            <Chip label={status.new_status} size="small" />
                          </TableCell>
                          <TableCell>{status.note || 'N/A'}</TableCell>
                        </TableRow>
                      ))
                    ) : (
                      <TableRow>
                        <TableCell colSpan={3} align="center">
                          No status history found
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </>
        )}
      </DialogContent>
      
      <DialogActions>
        {editing && (
          <>
            <Button onClick={() => { setEditing(false); loadEquipment(); }}>
              Cancel
            </Button>
            <Button
              onClick={handleSave}
              variant="contained"
              startIcon={saving ? <CircularProgress size={20} /> : <SaveIcon />}
              disabled={saving}
            >
              Save
            </Button>
          </>
        )}
        {!editing && (
          <Button onClick={onClose}>Close</Button>
        )}
      </DialogActions>
    </Dialog>
  );
}

export default EquipmentDetail;

