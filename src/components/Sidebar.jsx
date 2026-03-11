import React, { useState } from 'react';
import {
  Drawer,
  Box,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Divider,
  Button,
  Chip,
  Alert,
  CircularProgress,
  LinearProgress,
  IconButton,
  Tooltip
} from '@mui/material';
import {
  Upload as UploadIcon,
  Refresh as RefreshIcon,
  CheckCircle,
  Download as DownloadIcon,
  Close as CloseIcon
} from '@mui/icons-material';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function Sidebar({ open, onClose, onFileSelect, onProcess, onLoadCache, database, loading, success, error, onReset }) {
  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      onFileSelect({ target: { files: [file] } });
    }
  };

  return (
    <Drawer
      anchor="left"
      open={open}
      onClose={onClose}
      sx={{
        width: 320,
        flexShrink: 0,
        '& .MuiDrawer-paper': {
          width: 320,
          boxSizing: 'border-box',
          pt: 2
        }
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', px: 2, mb: 2 }}>
        <h3>File Operations</h3>
        <IconButton onClick={onClose} size="small">
          <CloseIcon />
        </IconButton>
      </Box>
      <Divider />
      
      <Box sx={{ p: 2 }}>
        {/* File Upload */}
        <Box sx={{ mb: 3 }}>
          <input
            type="file"
            accept=".xls,.xlsx,.xlsm"
            onChange={handleFileChange}
            style={{ display: 'none' }}
            id="sidebar-file-input"
          />
          <label htmlFor="sidebar-file-input">
            <Button
              variant="outlined"
              component="span"
              fullWidth
              startIcon={<UploadIcon />}
              size="large"
              sx={{ mb: 2 }}
            >
              Select Excel File
            </Button>
          </label>

          {database && (
            <Chip
              label={database.name}
              onDelete={onReset}
              color="primary"
              variant="outlined"
              fullWidth
              sx={{ mb: 2 }}
            />
          )}

          <Button
            variant="contained"
            onClick={onProcess}
            disabled={!database || loading}
            fullWidth
            startIcon={loading ? <CircularProgress size={20} /> : <CheckCircle />}
            size="large"
            sx={{ mb: 2 }}
          >
            {loading ? 'Processing...' : 'Process Backlog'}
          </Button>

          {loading && <LinearProgress sx={{ mb: 2 }} />}
        </Box>

        <Divider sx={{ my: 2 }} />

        {/* Cache Operations */}
        <Box>
          <Button
            variant="outlined"
            onClick={onLoadCache}
            disabled={loading}
            fullWidth
            startIcon={<RefreshIcon />}
            size="large"
            color="secondary"
            sx={{ mb: 2 }}
          >
            Load from Cache
          </Button>
        </Box>

        {/* Status Messages */}
        {error && (
          <Alert severity="error" sx={{ mt: 2 }} onClose={() => {}}>
            {error}
          </Alert>
        )}

        {success && (
          <Alert severity="success" sx={{ mt: 2 }} onClose={() => {}}>
            {success}
          </Alert>
        )}
      </Box>
    </Drawer>
  );
}

export default Sidebar;

