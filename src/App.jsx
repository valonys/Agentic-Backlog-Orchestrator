import React, { useMemo, useRef, useState } from 'react';
import axios from 'axios';
import {
  Container,
  Box,
  Typography,
  Button,
  Paper,
  Alert,
  LinearProgress,
  CircularProgress,
  Chip,
  Tabs,
  Tab,
  Card,
  CardContent,
  Tooltip,
  IconButton,
  Menu,
  Select,
  MenuItem,
  TextField,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Divider
} from '@mui/material';
import {
  Upload as UploadIcon,
  Refresh as RefreshIcon,
  CheckCircle,
  Download as DownloadIcon,
  Error as ErrorIcon,
  Warning,
  Info,
  SmartToy as ChatIcon
} from '@mui/icons-material';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  LabelList,
  Legend
} from 'recharts';
import EquipmentDetail from './components/EquipmentDetail';
import ChatInterface from './components/ChatInterface';
import DashboardEnhancements, { getISOWeekNumber, getISOWeeksInYear } from './components/DashboardEnhancements';

const API_URL = import.meta.env.VITE_API_URL || (import.meta.env.DEV ? 'http://localhost:8000' : '');
const FONT_FAMILY = '"Tw Cen MT", "Tw Cen MT Condensed", Arial, sans-serif';
const SITES = ['GIR', 'DAL', 'PAZ', 'CLV'];
const PRIMARY_TABS = ['Pressure Safety Device', 'Pressure Vessel (VII)', 'FU Items'];

const createSiteEntry = () => ({
  file: null,
  backlog: null,
  performance: null,
  pending: null,
  sowProgress: null,
  metadata: null
});

function App() {
  const [siteData, setSiteData] = useState(() => {
    const base = {};
    SITES.forEach(site => {
      base[site] = createSiteEntry();
    });
    return base;
  });
  const [activeSite, setActiveSite] = useState(null);
  const [activeView, setActiveView] = useState('backlog');
  const [activeCategory, setActiveCategory] = useState(PRIMARY_TABS[0]);
  const [otherClass, setOtherClass] = useState('All');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [saving, setSaving] = useState(false);
  const [equipmentDetailOpen, setEquipmentDetailOpen] = useState(false);
  const [selectedTagId, setSelectedTagId] = useState(null);
  const [chatOpen, setChatOpen] = useState(false);
  const fileInputRef = useRef(null);
  const [menuAnchor, setMenuAnchor] = useState(null);
  const [menuSite, setMenuSite] = useState(null);
  const fileOpsOpen = Boolean(menuAnchor);

  const activeSiteData = activeSite ? siteData[activeSite] : null;
  const backlogData = activeSiteData?.backlog || null;
  const performanceData = activeSiteData?.performance || null;
  const pendingData = activeSiteData?.pending || null;
  const sowProgress = activeSiteData?.sowProgress || null;
  const metadata = activeSiteData?.metadata || null;
  const database = activeSiteData?.file || null;
  const hasDashboardData = Boolean(backlogData || pendingData || performanceData);
  const menuTargetSite = menuSite || activeSite;
  const menuTargetData = menuTargetSite ? siteData[menuTargetSite] : null;
  const menuDatabase = menuTargetData?.file || null;
  const menuHasData = Boolean(menuTargetData && (menuTargetData.backlog || menuTargetData.pending || menuTargetData.performance));

  const updateSiteData = (site, updates) => {
    if (!site) return;
    setSiteData(prev => ({
      ...prev,
      [site]:
        typeof updates === 'function'
          ? updates(prev[site])
          : { ...prev[site], ...updates }
    }));
  };

  const resetSite = (site) => {
    if (!site) return;
    setSiteData(prev => ({
      ...prev,
      [site]: createSiteEntry()
    }));
  };

  const selectSite = (site) => {
    setActiveSite(site);
    setActiveView('backlog');
    setActiveCategory(PRIMARY_TABS[0]);
    setOtherClass('All');
    setError(null);
    setSuccess(null);
  };

  const handleSiteButtonClick = (site, anchorEl) => {
    selectSite(site);
    setMenuSite(site);
    setMenuAnchor(anchorEl);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const closeMenu = () => {
    setMenuAnchor(null);
    setMenuSite(null);
  };

  const handleFileSelect = (e) => {
    if (!activeSite) {
      setError('Select a site button before choosing a file.');
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
      return;
    }

    const file = e.target.files[0];
    if (!file) return;

    const prefix = file.name.slice(0, 3).toUpperCase();
    if (prefix !== activeSite) {
      setError(`"${file.name}" belongs to the ${prefix || 'unknown'} site. Switch to the ${prefix || 'matching'} tab.`);
      setSuccess(null);
      e.target.value = '';
      return;
    }

    updateSiteData(activeSite, {
      file,
      backlog: null,
      performance: null,
      pending: null,
      sowProgress: null,
      metadata: null
    });
    setError(null);
    setSuccess(null);
  };

  const handleProcess = async () => {
    closeMenu();
    if (!activeSite) {
      setError('Select a site from FILE OPERATIONS first.');
      return;
    }
    const siteFile = siteData[activeSite]?.file;
    if (!siteFile) {
      setError(`Please select a ${activeSite} file first.`);
      return;
    }

    const prefix = siteFile.name.slice(0, 3).toUpperCase();
    if (prefix !== activeSite) {
      setError(`"${siteFile.name}" belongs to the ${prefix || 'unknown'} site. Switch to the ${prefix || 'matching'} tab.`);
      return;
    }

    setLoading(true);
    setError(null);
    setSuccess(null);

    const formData = new FormData();
    formData.append('database', siteFile);

    try {
      const res = await axios.post(`${API_URL}/process-backlog`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 180000
      });

      const data = res.data;
      const sowData = data.dashboard?.sow_progress;
      updateSiteData(activeSite, {
        backlog: data.dashboard?.backlog || [],
        performance: data.dashboard?.performance || [],
        pending: data.dashboard?.pending || [],
        sowProgress: sowData || null,
        metadata: {
        itemsProcessed: data.items_processed,
        message: data.message,
        timestamp: new Date(data.timestamp).toLocaleString()
        }
      });
      setSuccess(`${activeSite}: ${data.message}`);
    } catch (err) {
      console.error('Processing error:', err);
      const errorMsg = err.response?.data?.detail || err.message || 'Processing failed';
      setError(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  const handleLoadFromCache = async () => {
    closeMenu();
    if (!activeSite) {
      setError('Select a site from FILE OPERATIONS to load cached data.');
      return;
    }

    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      // Load cache filtered by active site
      const listRes = await axios.get(`${API_URL}/cache/list`, {
        params: { site: activeSite }
      });
      const cachedFiles = listRes.data.files;

      if (!cachedFiles || cachedFiles.length === 0) {
        setError(`No cached files found for ${activeSite} site. Please upload and process a ${activeSite} file first.`);
        setLoading(false);
        return;
      }

      const mostRecent = cachedFiles[0];
      
      // Validate that the cached file matches the active site
      const filenamePrefix = mostRecent.filename.slice(0, 3).toUpperCase();
      if (filenamePrefix !== activeSite) {
        setError(`Cached file "${mostRecent.filename}" belongs to ${filenamePrefix} site, not ${activeSite}. Switch to the ${filenamePrefix} tab or upload a ${activeSite} file.`);
        setLoading(false);
        return;
      }

      const res = await axios.get(`${API_URL}/cache/${mostRecent.file_hash}`);

      const data = res.data;
      const sowData = data.dashboard?.sow_progress;
      updateSiteData(activeSite, {
        backlog: data.dashboard?.backlog || [],
        performance: data.dashboard?.performance || [],
        pending: data.dashboard?.pending || [],
        sowProgress: sowData || null,
        metadata: {
          itemsProcessed: data.items_processed,
          message: data.message,
          timestamp: new Date(data.timestamp).toLocaleString()
        }
      });
      setSuccess(`✓ ${activeSite}: ${data.message} (from cache: ${mostRecent.filename})`);
    } catch (err) {
      console.error('Load from cache error:', err);
      const errorMsg = err.response?.data?.detail || err.message || 'Failed to load from cache';
      setError(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    closeMenu();
    if (!activeSite) {
      setError('Select a site to reset.');
      return;
    }
    resetSite(activeSite);
    setError(null);
    setSuccess(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const dashboard = useMemo(() => {
    if (!activeSite) return null;
    if (activeView === 'backlog') return backlogData;
    if (activeView === 'pending') return pendingData;
    if (activeView === 'performance') return performanceData;
    return backlogData;
  }, [activeSite, activeView, backlogData, pendingData, performanceData]);

  const otherClasses = useMemo(() => {
    if (!dashboard) return ['All'];
    // For all views (backlog, pending, performance), get other classes
    const set = new Set(
      dashboard
        ?.map(d => d.Category || 'Uncategorized')
        .filter(c => !PRIMARY_TABS.includes(c))
    );
    const list = Array.from(set).sort();
    return ['All', ...list];
  }, [dashboard]);

  const filtered = useMemo(() => {
    if (!dashboard) return [];
    // Apply category filtering for all views (backlog, pending, performance)
    if (PRIMARY_TABS.includes(activeCategory)) {
      return dashboard.filter(d => (d.Category || 'Uncategorized') === activeCategory);
    }
    const others = dashboard.filter(d => !PRIMARY_TABS.includes(d.Category || 'Uncategorized'));
    if (otherClass === 'All') return others;
    return others.filter(d => (d.Category || 'Uncategorized') === otherClass);
  }, [dashboard, activeView, activeCategory, otherClass]);

  const updateStatus = async (tagId, newStatus, note) => {
    try {
      setSaving(true);
      await axios.post(`${API_URL}/items/${encodeURIComponent(tagId)}/status`, {
        tag_id: tagId,
        new_status: newStatus,
        note
      });
    } catch (e) {
      console.error('Save status failed', e);
      setError(e.response?.data?.detail || e.message || 'Failed to save status');
    } finally {
      setSaving(false);
    }
  };

  const exportToCSV = () => {
    // Export only the filtered data (current sub-tab selection)
    if (!filtered || filtered.length === 0) return;
    const headers = Object.keys(filtered[0]).filter(k => k !== 'color');
    const csvContent = [
      headers.join(','),
      ...filtered.map(row => 
        headers.map(h => `"${row[h]}"`).join(',')
      )
    ].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    const categoryName = activeCategory === 'Other Items' ? otherClass : activeCategory;
    a.download = `${activeSite || 'data'}-${activeView}-${categoryName || 'all'}-${Date.now()}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  const getRiskStats = () => {
    if (!dashboard) return null;
    return {
      high: dashboard.filter(d => d['Risk Level'] === 'High').length,
      medium: dashboard.filter(d => d['Risk Level'] === 'Medium').length,
      low: dashboard.filter(d => d['Risk Level'] === 'Low').length,
      total: dashboard.length
    };
  };

  const getSECEStats = useMemo(() => {
    if (!dashboard || dashboard.length === 0) return null;
    const sceCount = dashboard.filter(d => d.SECE === 'Yes' || d.SECE === true).length;
    const nonSceCount = dashboard.filter(d => d.SECE === 'No' || d.SECE === false || !d.SECE).length;
    return {
      sce: sceCount,
      nonSce: nonSceCount,
      total: dashboard.length
    };
  }, [dashboard]);

  const stats = getRiskStats();

  const kpis = useMemo(() => {
    if (!dashboard || dashboard.length === 0) return null;
    if (activeView === 'backlog') {
      const total = dashboard.length;
      const high = dashboard.filter(d => d['Risk Level'] === 'High').length;
      const medium = dashboard.filter(d => d['Risk Level'] === 'Medium').length;
      const low = dashboard.filter(d => d['Risk Level'] === 'Low').length;
      return {
        total,
        high,
        medium,
        low,
        highPct: ((high / total) * 100).toFixed(1),
        mediumPct: ((medium / total) * 100).toFixed(1),
        lowPct: ((low / total) * 100).toFixed(1)
      };
    } else if (activeView === 'pending') {
      const total = dashboard.length;
      const high = dashboard.filter(d => d['Risk Level'] === 'High').length;
      const medium = dashboard.filter(d => d['Risk Level'] === 'Medium').length;
      const low = dashboard.filter(d => d['Risk Level'] === 'Low').length;
      const approved = dashboard.filter(d => (d['Order Status'] || '').toUpperCase() === 'APPR').length;
      const workReleased = dashboard.filter(d => (d['Order Status'] || '').toUpperCase() === 'WREL').length;
      const initiated = dashboard.filter(d => (d['Order Status'] || '').toUpperCase() === 'INIT').length;
      const otherStatuses = total - approved - workReleased - initiated;
      return {
        total,
        high,
        medium,
        low,
        highPct: total > 0 ? ((high / total) * 100).toFixed(1) : '0.0',
        mediumPct: total > 0 ? ((medium / total) * 100).toFixed(1) : '0.0',
        lowPct: total > 0 ? ((low / total) * 100).toFixed(1) : '0.0',
        approved,
        workReleased,
        initiated,
        otherStatuses
      };
    } else {
      // Performance: Calculate all metrics in a single pass for better performance
      const total = dashboard.length;
      let orderCompleted = 0;
      let jobDoneCompl = 0;
      
      // Single pass through dashboard array (optimized for large datasets)
      for (const d of dashboard) {
        const orderStatus = (d['Order Status'] || '').toUpperCase();
        if (orderStatus === 'QCAP' || orderStatus === 'EXDO') {
          orderCompleted++;
        }
        const jobDone = (d['Job Done'] || '').toLowerCase();
        if (jobDone.includes('compl')) {
          jobDoneCompl++;
        }
      }
      
      // Calculate ISO week number and total weeks in year
      const today = new Date();
      const currentWeekNumber = getISOWeekNumber(today);
      const totalWeeksInYear = getISOWeeksInYear(today.getFullYear());
      const ytdProgressPct = Math.min(100, Math.round((currentWeekNumber / totalWeeksInYear) * 100));
      
      return {
        total,
        orderCompleted,
        orderCompletedPct: total > 0 ? ((orderCompleted / total) * 100).toFixed(1) : '0.0',
        jobDoneCompl,
        jobDoneComplPct: total > 0 ? ((jobDoneCompl / total) * 100).toFixed(1) : '0.0',
        week: currentWeekNumber,
        totalWeeks: totalWeeksInYear,
        ytdProgressPct
      };
    }
  }, [dashboard, activeView]);

  const getRiskIcon = (risk) => {
    switch (risk) {
      case 'High': return <ErrorIcon color="error" />;
      case 'Medium': return <Warning color="warning" />;
      case 'Low': return <CheckCircle color="success" />;
      default: return <Info color="info" />;
    }
  };

  const handleTagClick = (tagId) => {
    setSelectedTagId(tagId);
    setEquipmentDetailOpen(true);
  };

  return (
    <Box
      sx={{
        minHeight: '100vh',
        backgroundImage: 'url(/images/fpso-background.jpg)',
        backgroundSize: 'cover',
        backgroundPosition: 'center',
        backgroundRepeat: 'no-repeat',
        backgroundAttachment: 'fixed',
        position: 'relative',
        '&::before': {
          content: '""',
          position: 'fixed',
          inset: 0,
          background: 'rgba(255,255,255,0.25)',
          zIndex: 0
        }
      }}
    >
      {/* Fixed Header with Logo and Title */}
      <Box
        sx={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          zIndex: 1000,
          backgroundColor: 'rgba(0, 0, 0, 0.03)',
          backdropFilter: 'blur(1px)',
          py: 1.5,
          px: 2,
          minHeight: 80
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative', px: 3, minHeight: 80 }}>
          <Box
            sx={{
              position: 'absolute',
              right: 16,
              top: '50%',
              transform: 'translateY(-50%)',
              backgroundColor: 'transparent',
              display: 'flex',
              alignItems: 'center',
              height: 80,
              maxHeight: 80
            }}
          >
            <Box
              component="img"
              src="https://raw.githubusercontent.com/valonys/reparos/9c16b16a1686f8f84af033d5c8212d3326dc17a5/TE_Logo.png"
              alt="TotalEnergies Logo"
              sx={{ 
                height: 80,
                maxHeight: 80,
                width: 'auto',
                objectFit: 'contain',
                display: 'block',
                maskImage: 'radial-gradient(ellipse 100% 100% at center, black 70%, transparent 100%)',
                WebkitMaskImage: 'radial-gradient(ellipse 100% 100% at center, black 70%, transparent 100%)'
              }}
            />
          </Box>
          <Typography 
            variant="h2" 
            component="h1" 
            fontWeight="bold" 
            sx={{ 
              fontSize: 20,
              fontFamily: FONT_FAMILY,
              color: 'white',
              textShadow: '2px 2px 4px rgba(0,0,0,0.5)',
              textAlign: 'center'
            }}
          >
            B17 Topside Inspection - TAG is All You Need
        </Typography>
        </Box>
      </Box>

      {/* Fixed Sidebar with Site Buttons */}
      <Box
        sx={{
          position: 'fixed',
          left: 0,
          top: 80,
          bottom: 0,
          width: 180,
          zIndex: 999,
          backgroundColor: 'rgba(0, 0, 0, 0.03)',
          backdropFilter: 'blur(1px)',
          py: 2,
          px: 2,
          display: 'flex',
          flexDirection: 'column',
          gap: 1.5,
          overflowY: 'auto'
        }}
      >
        {SITES.map(site => {
          const siteColors = {
            'GIR': { bg: '#ff9800', text: '#fff' }, // Orange
            'DAL': { bg: '#42a5f5', text: '#fff' }, // Light blue
            'PAZ': { bg: '#9c27b0', text: '#fff' }, // Purple/violet
            'CLV': { bg: '#2e7d32', text: '#fff' }  // Dark green
          };
          const colors = siteColors[site] || { bg: '#1976d2', text: '#fff' };
          return (
            <Button
              key={site}
              variant="contained"
              onClick={(e) => handleSiteButtonClick(site, e.currentTarget)}
              fullWidth
              sx={{
                backgroundColor: colors.bg,
                color: colors.text,
                ...(site === activeSite ? {
                  boxShadow: `0 4px 8px ${colors.bg}80`,
                  transform: 'scale(1.05)',
                  fontWeight: 'bold'
                } : {
                  opacity: 0.85
                }),
                '&:hover': {
                  backgroundColor: colors.bg,
                  opacity: site === activeSite ? 0.95 : 1,
                  transform: site === activeSite ? 'scale(1.05)' : 'scale(1.02)'
                }
              }}
            >
              {site}
            </Button>
          );
        })}
        </Box>

      <Container maxWidth={false} sx={{ py: 4, pt: 12, pl: 3, pr: 3, fontFamily: FONT_FAMILY, position: 'relative', zIndex: 1, marginLeft: '180px', width: 'calc(100% - 180px)', boxSizing: 'border-box', paddingTop: '100px' }}>

        <Box sx={{ flex: 1 }}>
      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {success && (
        <Alert severity="success" sx={{ mb: 3 }} onClose={() => setSuccess(null)}>
          {success}
        </Alert>
      )}

          {loading && <LinearProgress sx={{ mb: 3 }} />}

          {activeSite && hasDashboardData && (
            <Paper elevation={2} sx={{ mb: 3, bgcolor: 'rgba(255, 255, 255, 0.85)', backdropFilter: 'blur(10px)' }}>
              <Tabs
                value={activeView}
                onChange={(e, newValue) => {
                  setActiveView(newValue);
                  // Reset to first primary tab when switching views
                  if (!PRIMARY_TABS.includes(activeCategory)) {
                    setActiveCategory(PRIMARY_TABS[0]);
                  }
                }}
                centered
                sx={{ borderBottom: 1, borderColor: 'divider' }}
              >
                <Tab
                  label={`Backlog (${backlogData?.length || 0})`}
                  value="backlog"
                  sx={{ fontWeight: 'bold', fontSize: '1rem', fontFamily: FONT_FAMILY }}
                />
                <Tab
                  label={`Pending (${pendingData?.length || 0})`}
                  value="pending"
                  sx={{ fontWeight: 'bold', fontSize: '1rem', fontFamily: FONT_FAMILY }}
                />
                <Tab
                  label={`Performance (${performanceData?.length || 0})`}
                  value="performance"
                  sx={{ fontWeight: 'bold', fontSize: '1rem', fontFamily: FONT_FAMILY }}
                />
              </Tabs>
            </Paper>
          )}

          {dashboard && (
            <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1, mb: 2 }}>
              <Tooltip title="Chat with Engineering Agents">
                <IconButton 
                  onClick={() => setChatOpen(true)} 
                  color="primary"
                  sx={{ 
                    bgcolor: 'rgba(25, 118, 210, 0.1)',
                    '&:hover': { bgcolor: 'rgba(25, 118, 210, 0.2)' }
                  }}
                >
                  <ChatIcon />
                </IconButton>
              </Tooltip>
              <Tooltip title="Export to CSV">
                <IconButton onClick={exportToCSV} color="primary">
                  <DownloadIcon />
                </IconButton>
              </Tooltip>
              <Tooltip title="Reset Site Data">
                <IconButton onClick={handleReset} color="secondary" disabled={!activeSite}>
                  <RefreshIcon />
                </IconButton>
              </Tooltip>
            </Box>
          )}

      {stats && (
            <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 1.5, mb: 3 }}>
              <Card sx={{ bgcolor: 'rgba(255, 255, 255, 0.85)', backdropFilter: 'blur(10px)' }}>
                <CardContent sx={{ p: 1.5, '&:last-child': { pb: 1.5 } }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <ErrorIcon color="error" />
                <Typography variant="h6">High Risk</Typography>
              </Box>
              <Typography variant="h3" sx={{ mt: 1 }}>{stats.high}</Typography>
              <Typography variant="body2" color="text.secondary">
                {((stats.high / stats.total) * 100).toFixed(1)}% of total
              </Typography>
            </CardContent>
          </Card>
              <Card sx={{ bgcolor: 'rgba(255, 255, 255, 0.85)', backdropFilter: 'blur(10px)' }}>
                <CardContent sx={{ p: 1.5, '&:last-child': { pb: 1.5 } }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Warning color="warning" />
                <Typography variant="h6">Medium Risk</Typography>
              </Box>
              <Typography variant="h3" sx={{ mt: 1 }}>{stats.medium}</Typography>
              <Typography variant="body2" color="text.secondary">
                {((stats.medium / stats.total) * 100).toFixed(1)}% of total
              </Typography>
            </CardContent>
          </Card>
              <Card sx={{ bgcolor: 'rgba(255, 255, 255, 0.85)', backdropFilter: 'blur(10px)' }}>
                <CardContent sx={{ p: 1.5, '&:last-child': { pb: 1.5 } }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <CheckCircle color="success" />
                <Typography variant="h6">Low Risk</Typography>
              </Box>
              <Typography variant="h3" sx={{ mt: 1 }}>{stats.low}</Typography>
              <Typography variant="body2" color="text.secondary">
                {((stats.low / stats.total) * 100).toFixed(1)}% of total
              </Typography>
            </CardContent>
          </Card>
              <Card sx={{ bgcolor: 'rgba(255, 255, 255, 0.85)', backdropFilter: 'blur(10px)' }}>
                <CardContent sx={{ p: 1.5, '&:last-child': { pb: 1.5 } }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Info color="info" />
                <Typography variant="h6">Total Items</Typography>
              </Box>
              <Typography variant="h3" sx={{ mt: 1 }}>{stats.total}</Typography>
              <Typography variant="body2" color="text.secondary">
                    Processed: {metadata?.timestamp || '–'}
              </Typography>
            </CardContent>
          </Card>
        </Box>
      )}

          {kpis && activeView === 'backlog' && (
            <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 1.5, mb: 2 }}>
              <Card sx={{ bgcolor: 'rgba(255, 255, 255, 0.85)', backdropFilter: 'blur(10px)' }}>
                <CardContent sx={{ p: 1.5, '&:last-child': { pb: 1.5 } }}>
                  <Typography variant="h6">Total Backlog</Typography>
                  <Typography variant="h3">{kpis.total}</Typography>
                  <Typography variant="body2" color="text.secondary">Items requiring attention</Typography>
                </CardContent>
              </Card>
              <Card sx={{ bgcolor: 'rgba(255, 255, 255, 0.85)', backdropFilter: 'blur(10px)' }}>
                <CardContent sx={{ p: 1.5, '&:last-child': { pb: 1.5 } }}>
                  <Typography variant="h6">High Risk</Typography>
                  <Typography variant="h3" color="error.main">{kpis.high}</Typography>
                  <Typography variant="body2" color="text.secondary">{kpis.highPct}% of backlog</Typography>
                </CardContent>
              </Card>
              <Card sx={{ bgcolor: 'rgba(255, 255, 255, 0.85)', backdropFilter: 'blur(10px)' }}>
                <CardContent sx={{ p: 1.5, '&:last-child': { pb: 1.5 } }}>
                  <Typography variant="h6">Medium Risk</Typography>
                  <Typography variant="h3" color="warning.main">{kpis.medium}</Typography>
                  <Typography variant="body2" color="text.secondary">{kpis.mediumPct}% of backlog</Typography>
                </CardContent>
              </Card>
              <Card sx={{ bgcolor: 'rgba(255, 255, 255, 0.85)', backdropFilter: 'blur(10px)' }}>
                <CardContent sx={{ p: 1.5, '&:last-child': { pb: 1.5 } }}>
                  <Typography variant="h6">Low Risk</Typography>
                  <Typography variant="h3" color="success.main">{kpis.low}</Typography>
                  <Typography variant="body2" color="text.secondary">{kpis.lowPct}% of backlog</Typography>
                </CardContent>
              </Card>
            </Box>
          )}

          {kpis && activeView === 'pending' && (
            <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 1.5, mb: 2 }}>
              <Card sx={{ bgcolor: 'rgba(255, 255, 255, 0.85)', backdropFilter: 'blur(10px)' }}>
                <CardContent sx={{ p: 1.5, '&:last-child': { pb: 1.5 } }}>
                  <Typography variant="h6">Total Pending</Typography>
                  <Typography variant="h3">{kpis.total}</Typography>
                  <Typography variant="body2" color="text.secondary">Items awaiting action</Typography>
                </CardContent>
              </Card>
              <Card sx={{ bgcolor: 'rgba(255, 255, 255, 0.85)', backdropFilter: 'blur(10px)' }}>
                <CardContent sx={{ p: 1.5, '&:last-child': { pb: 1.5 } }}>
                  <Typography variant="h6">High Risk</Typography>
                  <Typography variant="h3" color="error.main">{kpis.high}</Typography>
                  <Typography variant="body2" color="text.secondary">{kpis.highPct}% of pending</Typography>
                </CardContent>
              </Card>
              <Card sx={{ bgcolor: 'rgba(255, 255, 255, 0.85)', backdropFilter: 'blur(10px)' }}>
                <CardContent sx={{ p: 1.5, '&:last-child': { pb: 1.5 } }}>
                  <Typography variant="h6">Medium Risk</Typography>
                  <Typography variant="h3" color="warning.main">{kpis.medium}</Typography>
                  <Typography variant="body2" color="text.secondary">{kpis.mediumPct}% of pending</Typography>
                </CardContent>
              </Card>
              <Card sx={{ bgcolor: 'rgba(255, 255, 255, 0.85)', backdropFilter: 'blur(10px)' }}>
                <CardContent sx={{ p: 1.5, '&:last-child': { pb: 1.5 } }}>
                  <Typography variant="h6">Low Risk</Typography>
                  <Typography variant="h3" color="success.main">{kpis.low}</Typography>
                  <Typography variant="body2" color="text.secondary">{kpis.lowPct}% of pending</Typography>
                </CardContent>
              </Card>
            </Box>
          )}

          {kpis && activeView === 'performance' && (
            <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 1.5, mb: 2 }}>
              <Card sx={{ bgcolor: 'rgba(255, 255, 255, 0.85)', backdropFilter: 'blur(10px)' }}>
                <CardContent sx={{ p: 1.5, '&:last-child': { pb: 1.5 } }}>
                  <Typography variant="h6">Total Items</Typography>
                  <Typography variant="h3">{kpis.total}</Typography>
                  <Typography variant="body2" color="text.secondary">Performance scope</Typography>
                </CardContent>
              </Card>
              <Card sx={{ bgcolor: 'rgba(255, 255, 255, 0.85)', backdropFilter: 'blur(10px)' }}>
                <CardContent sx={{ p: 1.5, '&:last-child': { pb: 1.5 } }}>
                  <Typography variant="h6">Completed (QCAP/EXDO)</Typography>
                  <Typography variant="h3">{kpis.orderCompleted}</Typography>
                  <Typography variant="body2" color="text.secondary">{kpis.orderCompletedPct}% of total</Typography>
                </CardContent>
              </Card>
              <Card sx={{ bgcolor: 'rgba(255, 255, 255, 0.85)', backdropFilter: 'blur(10px)' }}>
                <CardContent sx={{ p: 1.5, '&:last-child': { pb: 1.5 } }}>
                  <Typography variant="h6">Job Done: Compl</Typography>
                  <Typography variant="h3">{kpis.jobDoneCompl}</Typography>
                  <Typography variant="body2" color="text.secondary">{kpis.jobDoneComplPct}% of total</Typography>
                </CardContent>
              </Card>
              <Card sx={{ bgcolor: 'rgba(255, 255, 255, 0.85)', backdropFilter: 'blur(10px)' }}>
                <CardContent sx={{ p: 1.5, '&:last-child': { pb: 1.5 } }}>
                  <Typography variant="h6">YTD Progress</Typography>
                  <Typography variant="h3">{kpis.ytdProgressPct}%</Typography>
                  <Typography variant="body2" color="text.secondary">Week {kpis.week} of {kpis.totalWeeks}</Typography>
                </CardContent>
              </Card>
            </Box>
          )}

          {/* Enhanced Dashboard Visualizations */}
          {dashboard && dashboard.length > 0 && (
            <DashboardEnhancements dashboardData={dashboard} activeView={activeView} />
          )}

          {/* Charts Grid - Compact layout for 4 charts (2x2) - Narrow width */}
          <Box sx={{ 
            display: 'grid', 
            gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)', lg: 'repeat(2, 1fr)' }, 
            gap: 1.5, 
            mb: 3, 
            maxWidth: '70%',
            margin: '0 auto'
          }}>
            {sowProgress && (
              <Paper elevation={3} sx={{ p: 1.5, bgcolor: 'rgba(255, 255, 255, 0.85)', backdropFilter: 'blur(10px)', maxWidth: '100%' }}>
                <Typography variant="h6" gutterBottom sx={{ mb: 1, fontWeight: 'bold', fontSize: 12 }}>
                  {activeSite} SOW Progress - {sowProgress.month || 'N/A'}
                </Typography>
                <Box sx={{ width: '100%', height: 220, maxWidth: '100%' }}>
                  <ResponsiveContainer width="100%" height={220}>
                    <BarChart data={[{
                      month: sowProgress.month || 'N/A',
                      Plan: (Number(sowProgress.plan) || 0) * 2,
                      Backlog: (Number(sowProgress.backlog) || 0) * 2,
                      'Site Perf': (Number(sowProgress.site_perf) || 0) * 2,
                      planOrig: Number(sowProgress.plan) || 0,
                      backlogOrig: Number(sowProgress.backlog) || 0,
                      sitePerfOrig: Number(sowProgress.site_perf) || 0
                    }]} barSize={40} margin={{ top: 10, right: 10, left: 25, bottom: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="month" tick={{ fontSize: 10 }} />
                      <YAxis label={{ value: 'WO', angle: -90, position: 'insideLeft', style: { fontSize: 10 } }} domain={[0, 'dataMax + 50']} tick={{ fontSize: 10 }} width={30} />
                      <RechartsTooltip formatter={(value) => [Math.round(value / 2), '']} />
                      <Bar dataKey="Plan" stackId="a" fill="#1976d2" name="Plan">
                        <LabelList dataKey="planOrig" position="inside" fill="white" style={{ fontSize: 9, fontWeight: 'bold' }} />
                      </Bar>
                      <Bar dataKey="Backlog" stackId="a" fill="#d32f2f" name="Backlog">
                        <LabelList dataKey="backlogOrig" position="inside" fill="white" style={{ fontSize: 9, fontWeight: 'bold' }} />
                      </Bar>
                      <Bar dataKey="Site Perf" stackId="a" fill="#388e3c" name="Site Perf">
                        <LabelList dataKey="sitePerfOrig" position="inside" fill="white" style={{ fontSize: 9, fontWeight: 'bold' }} />
                      </Bar>
                      <Legend wrapperStyle={{ fontSize: 10, paddingTop: 5 }} iconSize={10} />
                    </BarChart>
                  </ResponsiveContainer>
                </Box>
                <Box sx={{ mt: 1, display: 'flex', gap: 2, justifyContent: 'center', flexWrap: 'wrap' }}>
                  <Typography variant="body2" sx={{ fontSize: 10 }}>
                    <strong>Plan:</strong> {sowProgress.plan || 0} | <strong>Backlog:</strong> {sowProgress.backlog || 0} | <strong>Perf:</strong> {sowProgress.site_perf || 0}
                  </Typography>
                </Box>
              </Paper>
            )}
            {getSECEStats && dashboard && dashboard.length > 0 && (
              <Paper elevation={3} sx={{ p: 1.5, bgcolor: 'rgba(255, 255, 255, 0.85)', backdropFilter: 'blur(10px)', maxWidth: '100%' }}>
                <Typography variant="h6" gutterBottom sx={{ mb: 1, fontWeight: 'bold', fontSize: 12 }}>
                  {activeSite} SECE - {activeView.charAt(0).toUpperCase() + activeView.slice(1)}
                </Typography>
                <Box sx={{ width: '100%', height: 220, maxWidth: '100%' }}>
                  <ResponsiveContainer width="100%" height={220}>
                    <BarChart data={[{
                      category: activeView.charAt(0).toUpperCase() + activeView.slice(1),
                      'SCE': (Number(getSECEStats.sce) || 0) * 2,
                      'Non SCE': (Number(getSECEStats.nonSce) || 0) * 2,
                      sceOrig: Number(getSECEStats.sce) || 0,
                      nonSceOrig: Number(getSECEStats.nonSce) || 0
                    }]} barSize={40} margin={{ top: 10, right: 10, left: 25, bottom: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="category" tick={{ fontSize: 10 }} />
                      <YAxis label={{ value: 'Items', angle: -90, position: 'insideLeft', style: { fontSize: 10 } }} domain={[0, 'dataMax + 50']} tick={{ fontSize: 10 }} width={30} />
                      <RechartsTooltip formatter={(value) => [Math.round(value / 2), '']} />
                      <Bar dataKey="SCE" stackId="a" fill="#d32f2f" name="SCE">
                        <LabelList dataKey="sceOrig" position="inside" fill="white" style={{ fontSize: 9, fontWeight: 'bold' }} />
                      </Bar>
                      <Bar dataKey="Non SCE" stackId="a" fill="#42a5f5" name="Non SCE">
                        <LabelList dataKey="nonSceOrig" position="inside" fill="white" style={{ fontSize: 9, fontWeight: 'bold' }} />
                      </Bar>
                      <Legend wrapperStyle={{ fontSize: 10, paddingTop: 5 }} iconSize={10} />
                    </BarChart>
                  </ResponsiveContainer>
                </Box>
                <Box sx={{ mt: 1, display: 'flex', gap: 2, justifyContent: 'center', flexWrap: 'wrap' }}>
                  <Typography variant="body2" sx={{ fontSize: 10 }}>
                    <strong>SCE:</strong> {getSECEStats.sce || 0} | <strong>Non SCE:</strong> {getSECEStats.nonSce || 0} | <strong>Total:</strong> {getSECEStats.total || 0}
                  </Typography>
                </Box>
              </Paper>
            )}
            {/* Placeholder slots for 2 more charts - ready to add */}
          </Box>

          {(activeView === 'backlog' || activeView === 'pending' || activeView === 'performance') && dashboard && dashboard.length > 0 && (
            <Paper elevation={1} sx={{ mb: 2, bgcolor: 'rgba(255, 255, 255, 0.85)', backdropFilter: 'blur(10px)' }}>
              <Tabs
                value={activeCategory}
                onChange={(_, v) => {
                  setActiveCategory(v);
                  if (v !== 'Other Items') setOtherClass('All');
                }}
                variant="scrollable"
                scrollButtons="auto"
              >
                {PRIMARY_TABS.map(cat => (
                  <Tab key={cat} value={cat} label={cat} />
                ))}
                <Tab value="Other Items" label="Other Items" />
              </Tabs>
              {activeCategory === 'Other Items' && (
                <Box sx={{ p: 2, display: 'flex', gap: 2, alignItems: 'center' }}>
                  <Typography variant="body2" color="text.secondary">Filter other classes:</Typography>
                  <Select size="small" value={otherClass} onChange={(e) => setOtherClass(e.target.value)}>
                    {otherClasses.map(c => (
                      <MenuItem key={c} value={c}>{c}</MenuItem>
                    ))}
                  </Select>
                </Box>
              )}
            </Paper>
          )}

          {filtered && filtered.length > 0 && (
            <TableContainer component={Paper} elevation={3} sx={{ bgcolor: 'rgba(255, 255, 255, 0.85)', backdropFilter: 'blur(10px)', width: '100%', maxWidth: '100%', overflowX: 'auto' }}>
          <Table stickyHeader>
            <TableHead>
              <TableRow>
                    {(() => {
                      const baseKeys = Object.keys(filtered[0]).filter(k => k !== 'color');
                      let keys = [...baseKeys];
                      
                      // For BACKLOG, PENDING, PERFORMANCE with primary tabs: remove Category, Description, Location and add Functional Location
                      if ((activeView === 'backlog' || activeView === 'pending' || activeView === 'performance') && PRIMARY_TABS.includes(activeCategory)) {
                        ['Category', 'Description'].forEach(rem => {
                          const idx = keys.indexOf(rem);
                          if (idx >= 0) keys.splice(idx, 1);
                        });
                        const locIdx = keys.indexOf('Location');
                        if (locIdx >= 0) keys.splice(locIdx, 1);
                        if (!keys.includes('Functional Location')) keys.splice(3, 0, 'Functional Location');
                      }
                      
                      // For PENDING: remove Backlog?, Category, Description, Location, and Days in Backlog columns (only if not using primary tabs)
                      if (activeView === 'pending' && !PRIMARY_TABS.includes(activeCategory)) {
                        const backlogIdx = keys.indexOf('Backlog?');
                        if (backlogIdx >= 0) keys.splice(backlogIdx, 1);
                        const categoryIdx = keys.indexOf('Category');
                        if (categoryIdx >= 0) keys.splice(categoryIdx, 1);
                        const descIdx = keys.indexOf('Description');
                        if (descIdx >= 0) keys.splice(descIdx, 1);
                        const locIdx = keys.indexOf('Location');
                        if (locIdx >= 0) keys.splice(locIdx, 1);
                        const daysIdx = keys.indexOf('Days in Backlog');
                        if (daysIdx >= 0) keys.splice(daysIdx, 1);
                      }
                      
                      return keys.map(key => (
                        <TableCell key={key} sx={{ fontWeight: 'bold', backgroundColor: 'primary.main', color: 'white' }}>
                      {key}
                        </TableCell>
                      ));
                    })()}
                    <TableCell sx={{ fontWeight: 'bold', backgroundColor: 'primary.main', color: 'white' }}>
                      Update Status
                    </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
                  {filtered.map((row, idx) => (
                    <TableRow key={idx} sx={{ backgroundColor: row.color || 'white', '&:hover': { opacity: 0.9 } }}>
                      {(() => {
                        const entries = Object.entries(row).filter(([k]) => k !== 'color');
                        let keys = entries.map(([k]) => k);
                        
                        // For BACKLOG, PENDING, PERFORMANCE with primary tabs: filter columns
                        if ((activeView === 'backlog' || activeView === 'pending' || activeView === 'performance') && PRIMARY_TABS.includes(activeCategory)) {
                          keys = keys.filter(k => k !== 'Category' && k !== 'Description' && k !== 'Location');
                          if (!keys.includes('Functional Location')) keys.splice(3, 0, 'Functional Location');
                        }
                        
                        // For PENDING: remove Backlog?, Category, Description, Location, and Days in Backlog columns (only if not using primary tabs)
                        if (activeView === 'pending' && !PRIMARY_TABS.includes(activeCategory)) {
                          keys = keys.filter(k => k !== 'Backlog?' && k !== 'Category' && k !== 'Description' && k !== 'Location' && k !== 'Days in Backlog');
                        }
                        
                        return keys.map((k) => {
                          const val = row[k];
                          return (
                            <TableCell key={k}>
                              {k === 'Tag ID' ? (
                                <Button variant="text" onClick={() => handleTagClick(val)} sx={{ textTransform: 'none', textDecoration: 'underline' }}>
                                  {val}
                                </Button>
                              ) : k === 'Risk Level' ? (
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            {getRiskIcon(val)}
                            <Typography>{val}</Typography>
                          </Box>
                              ) : k === 'SECE' ? (
                                <Chip label={val} color={val === 'Yes' ? 'error' : 'default'} size="small" />
                              ) : k === 'Action' ? (
                                <Chip label={val} color={val === 'Escalate' ? 'error' : 'primary'} size="small" variant="outlined" />
                              ) : (
                                val
                              )}
                            </TableCell>
                          );
                        });
                      })()}
                      <TableCell>
                        <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                          <Select
                            size="small"
                            value={row.Status || 'Overdue'}
                            onChange={(e) => updateStatus(row['Tag ID'], e.target.value)}
                          >
                            <MenuItem value="Overdue">Overdue</MenuItem>
                            <MenuItem value="In Progress">In Progress</MenuItem>
                            <MenuItem value="Blocked">Blocked</MenuItem>
                            <MenuItem value="Completed">Completed</MenuItem>
                          </Select>
                          <TextField
                            size="small"
                            placeholder="Add note"
                            onKeyDown={(e) => {
                              if (e.key === 'Enter') {
                                updateStatus(row['Tag ID'], (row.Status || 'Overdue'), e.currentTarget.value);
                                e.currentTarget.value = '';
                              }
                            }}
                          />
                        </Box>
                      </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

          {dashboard && filtered.length === 0 && (
        <Alert severity="info">
              No items found in this category.
        </Alert>
      )}
        </Box>
    </Container>

      <Menu
        anchorEl={menuAnchor}
        open={fileOpsOpen}
        onClose={closeMenu}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
        transformOrigin={{ vertical: 'top', horizontal: 'right' }}
      >
        <Box sx={{ p: 2, width: 320 }}>
          <Typography variant="h6" fontWeight="bold" gutterBottom>
            {menuTargetSite ? `${menuTargetSite} FILE OPS` : 'FILE OPERATIONS'}
          </Typography>
          <Divider sx={{ mb: 2 }} />
          {menuTargetSite ? (
            <>
              <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
                {menuTargetSite} Uploads
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                Accepts .xls / .xlsx / .xlsm from the "{menuTargetSite}" site. The first three letters of the filename must match the site tab (e.g., {menuTargetSite}_TopSide…).
              </Typography>
              <input
                key={menuTargetSite}
                id={`file-input-${menuTargetSite}`}
                type="file"
                accept=".xls,.xlsx,.xlsm"
                onChange={handleFileSelect}
                style={{ display: 'none' }}
                ref={fileInputRef}
              />
              <label htmlFor={`file-input-${menuTargetSite}`}>
                <Button
                  variant="outlined"
                  component="span"
                  startIcon={<UploadIcon />}
                  fullWidth
                  sx={{ mb: 2 }}
                >
                  {menuDatabase ? 'Replace File' : 'Select Excel File'}
                </Button>
              </label>
              {menuDatabase && (
                <Box sx={{ mb: 2 }}>
                  <Chip
                    label={menuDatabase.name}
                    onDelete={handleReset}
                    color="primary"
                    variant="outlined"
                    sx={{ mb: 1, maxWidth: '100%' }}
                  />
                  <Typography variant="caption" color="text.secondary">
                    {`${(menuDatabase.size / 1024).toFixed(1)} KB`} • Last selected just now
                  </Typography>
                </Box>
              )}
                <Button
                  variant="outlined"
                  onClick={handleLoadFromCache}
                  disabled={loading}
                  startIcon={<RefreshIcon />}
                  fullWidth
                  color="secondary"
                  sx={{ mb: 2 }}
                >
                  Load {menuTargetSite} Cache
                </Button>
                <Button
                  variant="contained"
                  onClick={handleProcess}
                  disabled={!menuDatabase || loading}
                  startIcon={loading ? <CircularProgress size={20} /> : <CheckCircle />}
                  fullWidth
                  sx={{ mb: 2 }}
                >
                  {loading ? 'Processing...' : `Process ${menuTargetSite}`}
                </Button>
                <Button
                  variant="text"
                  color="secondary"
                  fullWidth
                  onClick={handleReset}
                  disabled={!menuDatabase && !menuHasData}
                >
                  Clear {menuTargetSite} Data
                </Button>
                <Typography variant="caption" color="text.secondary">
                  Tip: Use the cache for faster reloads; processing will re-parse "Data Base" sheet starting at B5:X.
                </Typography>
            </>
          ) : (
            <Alert severity="info">
              Choose a site on the left before using File Operations.
            </Alert>
          )}
        </Box>
      </Menu>

    <EquipmentDetail
        open={equipmentDetailOpen}
        tagId={selectedTagId}
        onClose={() => {
          setEquipmentDetailOpen(false);
          setSelectedTagId(null);
        }}
        onSave={() => {}}
      />
      
      <ChatInterface
        open={chatOpen}
        onClose={() => setChatOpen(false)}
        activeSite={activeSite}
        dashboardData={dashboard}
      />

      {/* Footer */}
      <Box
        component="footer"
        sx={{
          position: 'fixed',
          bottom: 0,
          left: 0,
          right: 0,
          py: 0.8,
          px: 2,
          backgroundColor: 'rgba(0,0,0,0.75)',
          backdropFilter: 'blur(4px)',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          zIndex: 1200,
        }}
      >
        <Typography
          variant="caption"
          sx={{
            fontFamily: '"Tw Cen MT", "Tw Cen MT Condensed", Arial, sans-serif',
            color: 'rgba(255,255,255,0.7)',
            letterSpacing: '0.5px',
            fontSize: '0.85rem',
          }}
        >
          Powered by FO/STP/INS/MET &nbsp;|&nbsp; Contact: Ataliba Miguel
        </Typography>
      </Box>
    </Box>
  );
}

export default App;
