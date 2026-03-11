import React, { useMemo } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  Paper
} from '@mui/material';
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
  Legend
} from 'recharts';
import {
  Error as ErrorIcon,
  Warning as WarningIcon,
  Shield as ShieldIcon,
  AccessTime as ClockIcon
} from '@mui/icons-material';

const FONT_FAMILY = '"Tw Cen MT", "Tw Cen MT Condensed", Arial, sans-serif';

// Color palette for pie chart
const COLORS = [
  '#1976d2', // Blue
  '#d32f2f', // Red
  '#388e3c', // Green
  '#ff9800', // Orange
  '#9c27b0', // Purple
  '#00bcd4', // Cyan
  '#ffc107', // Amber
  '#795548'  // Brown
];

/**
 * Return the ISO week number for a given date.
 */
function getISOWeekNumber(date) {
  const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
  d.setUTCDate(d.getUTCDate() + 4 - (d.getUTCDay() || 7));
  const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
  return Math.ceil(((d - yearStart) / 86400000 + 1) / 7);
}

/**
 * Return the total number of ISO weeks in a given year.
 * A year has 53 weeks if Jan 1 is Thursday, or Dec 31 is Thursday.
 */
function getISOWeeksInYear(year) {
  const jan1 = new Date(year, 0, 1);
  const dec31 = new Date(year, 11, 31);
  return (jan1.getDay() === 4 || dec31.getDay() === 4) ? 53 : 52;
}

/**
 * Enhanced dashboard components for better visualization
 * Adds SECE tracking, overdue items, discipline breakdown, and critical items spotlight
 */
export function DashboardEnhancements({ dashboardData, activeView }) {
  // Calculate enhanced KPIs
  const enhancedKPIs = useMemo(() => {
    if (!dashboardData || dashboardData.length === 0) return null;

    // SECE count (Safety & Environmental Critical Equipment)
    // SECE STATUS from Excel is "SCE" for critical items, blank for non-SCE
    // Dashboard items carry "SECE": "Yes"/"No" and "SECE Status": original value
    const seceCount = dashboardData.filter(item =>
      item.SECE === 'Yes' || item.SECE === true ||
      ['SCE', 'SECE'].includes((item['SECE Status'] || '').toUpperCase())
    ).length;

    // Overdue count (Days in Backlog > 0 or Days Overdue > 0)
    const overdueCount = dashboardData.filter(item =>
      Number(item['Days in Backlog'] || item['Days Overdue'] || 0) > 0
    ).length;

    // Discipline breakdown by Item Class — view-aware
    const disciplineBreakdown = {};
    dashboardData.forEach(item => {
      const itemClass = item['Item Class'] || item.Category || 'Other';
      disciplineBreakdown[itemClass] = (disciplineBreakdown[itemClass] || 0) + 1;
    });

    // Convert to array for pie chart (limit to top 7 + "Other")
    const disciplineArray = Object.entries(disciplineBreakdown)
      .map(([name, value]) => ({ name, value }))
      .sort((a, b) => b.value - a.value);

    const topDisciplines = disciplineArray.slice(0, 7);
    const otherCount = disciplineArray.slice(7).reduce((sum, d) => sum + d.value, 0);
    if (otherCount > 0) {
      topDisciplines.push({ name: 'Other', value: otherCount });
    }

    // Critical items (High-risk SECE items that are overdue)
    const criticalItems = dashboardData
      .filter(item =>
        item['Risk Level'] === 'High' &&
        (item.SECE === 'Yes' || item.SECE === true ||
         ['SCE', 'SECE'].includes((item['SECE Status'] || '').toUpperCase())) &&
        Number(item['Days in Backlog'] || item['Days Overdue'] || 0) > 0
      )
      .sort((a, b) => Number(b['Days in Backlog'] || b['Days Overdue'] || 0) - Number(a['Days in Backlog'] || a['Days Overdue'] || 0))
      .slice(0, 5); // Top 5

    return {
      seceCount,
      overdueCount,
      disciplineBreakdown: topDisciplines,
      criticalItems
    };
  }, [dashboardData, activeView]);

  if (!enhancedKPIs) return null;

  // View-aware pie chart title
  const pieTitle = activeView === 'backlog'
    ? 'Backlog Distribution by Item Class'
    : activeView === 'pending'
    ? 'Pending Distribution by Item Class'
    : 'Performance Distribution by Item Class';

  return (
    <Box>
      {/* Additional KPI Cards */}
      <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 1.5, mb: 3 }}>
        {/* SECE Count Card */}
        <Card sx={{ bgcolor: 'rgba(255, 255, 255, 0.9)', backdropFilter: 'blur(10px)' }}>
          <CardContent sx={{ p: 1.5, '&:last-child': { pb: 1.5 } }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <ShieldIcon sx={{ color: '#ff9800' }} />
              <Typography variant="h6" sx={{ fontFamily: FONT_FAMILY, fontSize: 14 }}>
                SECE Items
              </Typography>
            </Box>
            <Typography variant="h3" sx={{ mt: 1, fontFamily: FONT_FAMILY }}>
              {enhancedKPIs.seceCount}
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ fontFamily: FONT_FAMILY, fontSize: 12 }}>
              Safety & Environmental Critical
            </Typography>
          </CardContent>
        </Card>

        {/* Overdue Items Card */}
        <Card sx={{ bgcolor: 'rgba(255, 255, 255, 0.9)', backdropFilter: 'blur(10px)' }}>
          <CardContent sx={{ p: 1.5, '&:last-child': { pb: 1.5 } }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <ClockIcon sx={{ color: '#d32f2f' }} />
              <Typography variant="h6" sx={{ fontFamily: FONT_FAMILY, fontSize: 14 }}>
                Overdue Items
              </Typography>
            </Box>
            <Typography variant="h3" sx={{ mt: 1, fontFamily: FONT_FAMILY }}>
              {enhancedKPIs.overdueCount}
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ fontFamily: FONT_FAMILY, fontSize: 12 }}>
              Past due date
            </Typography>
          </CardContent>
        </Card>

        {/* Completion Rate Card (for backlog view) */}
        {activeView === 'backlog' && dashboardData && (
          <Card sx={{ bgcolor: 'rgba(255, 255, 255, 0.9)', backdropFilter: 'blur(10px)' }}>
            <CardContent sx={{ p: 1.5, '&:last-child': { pb: 1.5 } }}>
              <Typography variant="h6" sx={{ fontFamily: FONT_FAMILY, fontSize: 14 }}>
                Backlog Rate
              </Typography>
              <Typography variant="h3" sx={{ mt: 1, fontFamily: FONT_FAMILY }}>
                {((enhancedKPIs.overdueCount / dashboardData.length) * 100).toFixed(1)}%
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ fontFamily: FONT_FAMILY, fontSize: 12 }}>
                Overdue / Total
              </Typography>
            </CardContent>
          </Card>
        )}
      </Box>

      {/* Visualizations Grid */}
      <Box sx={{
        display: 'flex',
        justifyContent: 'center',
        gap: 2,
        mb: 3,
        flexWrap: 'wrap'
      }}>
        {/* Discipline Breakdown Pie Chart — centered */}
        {enhancedKPIs.disciplineBreakdown.length > 0 && (
          <Paper elevation={3} sx={{
            p: 2,
            bgcolor: 'rgba(255, 255, 255, 0.9)',
            backdropFilter: 'blur(10px)',
            width: { xs: '100%', lg: '48%' },
            maxWidth: 560
          }}>
            <Typography variant="h6" gutterBottom sx={{ fontFamily: FONT_FAMILY, fontWeight: 'bold', fontSize: 14, textAlign: 'center' }}>
              {pieTitle}
            </Typography>
            <Box sx={{ width: '100%', height: 300, display: 'flex', justifyContent: 'center' }}>
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={enhancedKPIs.disciplineBreakdown}
                    cx="50%"
                    cy="45%"
                    labelLine={true}
                    label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                    outerRadius={90}
                    innerRadius={0}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {enhancedKPIs.disciplineBreakdown.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <RechartsTooltip
                    formatter={(value, name) => [`${value} items`, name]}
                  />
                  <Legend
                    wrapperStyle={{ fontSize: 11, fontFamily: FONT_FAMILY }}
                    iconSize={10}
                  />
                </PieChart>
              </ResponsiveContainer>
            </Box>
          </Paper>
        )}

        {/* Critical Items Spotlight */}
        {enhancedKPIs.criticalItems.length > 0 && (
          <Paper elevation={3} sx={{
            p: 2,
            bgcolor: 'rgba(255, 255, 255, 0.9)',
            backdropFilter: 'blur(10px)',
            width: { xs: '100%', lg: '48%' },
            maxWidth: 560
          }}>
            <Typography variant="h6" gutterBottom sx={{ fontFamily: FONT_FAMILY, fontWeight: 'bold', fontSize: 14 }}>
              Critical Items Spotlight
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5, fontFamily: FONT_FAMILY, fontSize: 11 }}>
              High-risk SECE items that are overdue
            </Typography>
            <TableContainer sx={{ maxHeight: 240 }}>
              <Table size="small" stickyHeader>
                <TableHead>
                  <TableRow>
                    <TableCell sx={{ fontFamily: FONT_FAMILY, fontSize: 11, fontWeight: 'bold', p: 0.5 }}>
                      Tag
                    </TableCell>
                    <TableCell sx={{ fontFamily: FONT_FAMILY, fontSize: 11, fontWeight: 'bold', p: 0.5 }}>
                      Item Class
                    </TableCell>
                    <TableCell align="right" sx={{ fontFamily: FONT_FAMILY, fontSize: 11, fontWeight: 'bold', p: 0.5 }}>
                      Days Overdue
                    </TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {enhancedKPIs.criticalItems.map((item, idx) => (
                    <TableRow key={idx} hover>
                      <TableCell sx={{ fontFamily: FONT_FAMILY, fontSize: 11, p: 0.5 }}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                          <ErrorIcon sx={{ fontSize: 14, color: '#d32f2f' }} />
                          {item['Tag ID'] || item.Tag || 'N/A'}
                        </Box>
                      </TableCell>
                      <TableCell sx={{ fontFamily: FONT_FAMILY, fontSize: 10, p: 0.5 }}>
                        {item.Category || item['Item Class'] || 'N/A'}
                      </TableCell>
                      <TableCell align="right" sx={{ fontFamily: FONT_FAMILY, fontSize: 11, p: 0.5 }}>
                        <Chip
                          label={item['Days in Backlog'] || item['Days Overdue'] || 0}
                          size="small"
                          color="error"
                          sx={{ height: 18, fontSize: 10, fontFamily: FONT_FAMILY }}
                        />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Paper>
        )}
      </Box>
    </Box>
  );
}

export { getISOWeekNumber, getISOWeeksInYear };
export default DashboardEnhancements;
