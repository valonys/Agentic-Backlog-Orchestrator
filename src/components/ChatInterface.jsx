import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  Drawer,
  Box,
  Typography,
  TextField,
  IconButton,
  Paper,
  Chip,
  Divider,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Tooltip,
  Collapse,
  Link
} from '@mui/material';
import {
  Send as SendIcon,
  Close as CloseIcon,
  Remove as MinimizeIcon,
  HelpOutline as HelpIcon,
  AutoAwesome as SparkleIcon,
  ContentCopy as CopyIcon,
  ThumbUp as ThumbUpIcon,
  ThumbDown as ThumbDownIcon,
  Settings as SettingsIcon,
  Check as CheckIcon
} from '@mui/icons-material';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const FONT_FAMILY = '"Tw Cen MT", "Tw Cen MT Condensed", Arial, sans-serif';

// Professional aliases for model selection — maps provider to display name
const MODEL_ALIASES = {
  'deepseek':   'Methodical Analysis',
  'anthropic':  'Deep Analysis',
  'gemini':     'Transverse Analysis',
  'openrouter': 'Standard Analysis',
};

/**
 * Return a professional alias for a model entry.
 * Uses the provider-level alias + short model hint.
 */
function getModelAlias(model) {
  const providerAlias = MODEL_ALIASES[model.provider] || model.provider_label || model.provider;
  // Append a short model hint for disambiguation within the same provider
  const shortName = (model.label || '').replace(/^.*\//, '');
  return `${providerAlias} (${shortName})`;
}

const DISCIPLINES = [
  { value: 'all',       label: 'All Agents',         color: '#1976d2' },
  { value: 'topsides',  label: 'Topsides Engineer',  color: '#1976d2' },
  { value: 'fuims',     label: 'FUIMS Engineer',      color: '#42a5f5' },
  { value: 'psv',       label: 'PSV Engineer',        color: '#d32f2f' },
  { value: 'subsea',    label: 'Subsea Engineer',     color: '#388e3c' },
  { value: 'pipeline',  label: 'Pipeline Engineer',   color: '#f57c00' },
  { value: 'corrosion', label: 'Corrosion Engineer',  color: '#7b1fa2' },
  { value: 'methods',   label: 'Methods Engineer',    color: '#c2185b' }
];

// Suggested starter prompts shown in the empty state
const SUGGESTED_PROMPTS = [
  'Summarize open notifications for this site',
  'What are the top overdue inspection items?',
  'Show corrosion findings from last quarter',
  'List all PSV items past due date'
];

// ─── Typing Indicator (3 animated dots) ──────────────────────────────────────
function TypingDots() {
  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: '4px', py: 0.5, px: 0.5 }}>
      {[0, 1, 2].map(i => (
        <Box
          key={i}
          sx={{
            width: 7,
            height: 7,
            borderRadius: '50%',
            bgcolor: '#9c27b0',
            opacity: 0.7,
            animation: 'bounce 1.2s infinite ease-in-out',
            animationDelay: `${i * 0.2}s`,
            '@keyframes bounce': {
              '0%, 80%, 100%': { transform: 'scale(0.7)', opacity: 0.4 },
              '40%': { transform: 'scale(1)', opacity: 1 }
            }
          }}
        />
      ))}
    </Box>
  );
}

// ─── Blinking streaming cursor ────────────────────────────────────────────────
function StreamingCursor() {
  return (
    <Box
      component="span"
      sx={{
        display: 'inline-block',
        width: '2px',
        height: '1em',
        bgcolor: '#1a73e8',
        verticalAlign: 'text-bottom',
        ml: '2px',
        animation: 'blink 0.9s step-end infinite',
        '@keyframes blink': {
          '0%, 100%': { opacity: 1 },
          '50%': { opacity: 0 }
        }
      }}
    />
  );
}

// ─── Markdown renderer components (shared) ────────────────────────────────────
function markdownComponents(fontFamily) {
  return {
    p: ({ node, ...props }) => (
      <Typography
        variant="body2"
        component="p"
        sx={{ fontFamily, fontSize: '14px', color: '#202124', mb: 0.75, lineHeight: 1.65, '&:last-child': { mb: 0 } }}
        {...props}
      />
    ),
    ul: ({ node, ...props }) => (
      <Box
        component="ul"
        sx={{ pl: '20px', mb: 1, mt: 0.5, fontFamily, fontSize: '14px', color: '#202124', lineHeight: 1.65,
          '& li': { mb: '3px' },
          '& li::marker': { color: '#9c27b0' }
        }}
        {...props}
      />
    ),
    ol: ({ node, ...props }) => (
      <Box
        component="ol"
        sx={{ pl: '20px', mb: 1, mt: 0.5, fontFamily, fontSize: '14px', color: '#202124', lineHeight: 1.65,
          '& li': { mb: '3px' },
          '& li::marker': { color: '#9c27b0', fontWeight: 600 }
        }}
        {...props}
      />
    ),
    li: ({ node, ...props }) => (
      <li style={{ fontFamily, fontSize: '14px', color: '#202124', marginBottom: '3px' }} {...props} />
    ),
    strong: ({ node, ...props }) => (
      <strong style={{ fontWeight: 600, fontFamily, color: '#202124' }} {...props} />
    ),
    h1: ({ node, ...props }) => (
      <Typography variant="h6" sx={{ fontFamily, fontWeight: 600, mb: 1, mt: 1, color: '#202124', fontSize: '16px' }} {...props} />
    ),
    h2: ({ node, ...props }) => (
      <Typography variant="subtitle1" sx={{ fontFamily, fontWeight: 600, mb: 0.75, mt: 1, color: '#202124' }} {...props} />
    ),
    h3: ({ node, ...props }) => (
      <Typography variant="subtitle2" sx={{ fontFamily, fontWeight: 600, mb: 0.5, mt: 0.75, color: '#202124' }} {...props} />
    ),
    blockquote: ({ node, ...props }) => (
      <Box
        component="blockquote"
        sx={{ borderLeft: '3px solid #9c27b0', pl: 1.5, ml: 0, mb: 1, mt: 1, color: '#5f6368', fontStyle: 'italic', fontFamily }}
        {...props}
      />
    ),
    table: ({ node, ...props }) => (
      <Box component="div" sx={{ overflowX: 'auto', mb: 1.5, mt: 1 }}>
        <table style={{ borderCollapse: 'collapse', width: '100%', fontSize: '13px', fontFamily }} {...props} />
      </Box>
    ),
    th: ({ node, ...props }) => (
      <th style={{ border: '1px solid #dadce0', padding: '7px 11px', backgroundColor: '#f3eef9', fontWeight: 600, textAlign: 'left', fontFamily, color: '#202124' }} {...props} />
    ),
    td: ({ node, ...props }) => (
      <td style={{ border: '1px solid #dadce0', padding: '7px 11px', fontFamily, color: '#202124' }} {...props} />
    ),
    code: ({ node, inline, ...props }) =>
      inline ? (
        <code style={{ backgroundColor: 'rgba(0,0,0,0.05)', padding: '2px 5px', borderRadius: '4px', fontFamily: 'Consolas, Monaco, monospace', fontSize: '13px', color: '#d63031' }} {...props} />
      ) : (
        <Box
          component="pre"
          sx={{ bgcolor: '#1e1e2e', borderRadius: '8px', p: 1.5, mb: 1, mt: 1, overflowX: 'auto' }}
        >
          <code style={{ fontFamily: 'Consolas, Monaco, monospace', fontSize: '12.5px', color: '#cdd6f4', display: 'block' }} {...props} />
        </Box>
      )
  };
}

// ─── Single message bubble ────────────────────────────────────────────────────
function MessageBubble({ msg, agentTitle, fontFamily, mdComponents, onFeedback }) {
  const [copied, setCopied] = useState(false);
  const [hovered, setHovered] = useState(false);
  const [feedbackGiven, setFeedbackGiven] = useState(null); // 1 or -1

  const handleCopy = () => {
    navigator.clipboard.writeText(msg.text || '');
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  };

  const handleFeedback = (rating) => {
    if (feedbackGiven) return; // already rated
    setFeedbackGiven(rating);
    onFeedback?.(msg, rating);
  };

  const isAgent = msg.sender === 'agent';
  const isError = msg.sender === 'error';

  return (
    <Box
      sx={{
        mb: 2.5,
        display: 'flex',
        flexDirection: msg.sender === 'user' ? 'row-reverse' : 'row',
        alignItems: 'flex-start',
        gap: 1.5
      }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {/* Avatar icon — agent only */}
      {msg.sender !== 'user' && (
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: 28, height: 28, position: 'relative', mt: 0.25, flexShrink: 0 }}>
          <HelpIcon sx={{ color: '#9c27b0', fontSize: 22 }} />
          <SparkleIcon sx={{ color: '#9c27b0', fontSize: 10, position: 'absolute', top: -1, right: -1 }} />
        </Box>
      )}

      <Box sx={{ flex: 1, maxWidth: msg.sender === 'user' ? '78%' : '88%' }}>
        {/* Agent name label */}
        {isAgent && (
          <Typography variant="body2" sx={{ fontFamily, fontSize: '12px', color: '#5f6368', mb: 0.4, fontWeight: 500 }}>
            {agentTitle}
          </Typography>
        )}

        {/* Bubble */}
        <Paper
          elevation={0}
          sx={{
            p: '10px 14px',
            bgcolor: msg.sender === 'user'
              ? 'linear-gradient(135deg, #1a73e8 0%, #1558b0 100%)'
              : isError
              ? '#fce8e6'
              : '#f8f9fa',
            background: msg.sender === 'user'
              ? 'linear-gradient(135deg, #1a73e8 0%, #1558b0 100%)'
              : undefined,
            borderRadius: msg.sender === 'user'
              ? '18px 18px 4px 18px'
              : '4px 18px 18px 18px',
            fontFamily,
            position: 'relative',
            border: isAgent ? '1px solid #f0f0f0' : 'none',
            transition: 'box-shadow 0.15s ease',
            '&:hover': isAgent ? { boxShadow: '0 2px 8px rgba(0,0,0,0.08)' } : {}
          }}
        >
          {isAgent ? (
            <>
              <ReactMarkdown remarkPlugins={[remarkGfm]} components={mdComponents}>
                {msg.text}
              </ReactMarkdown>
              {msg.streaming && <StreamingCursor />}
            </>
          ) : (
            <Typography
              variant="body2"
              sx={{
                fontFamily,
                fontSize: '14px',
                color: msg.sender === 'user' ? '#ffffff' : isError ? '#c62828' : '#202124',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
                lineHeight: 1.6
              }}
            >
              {msg.text}
            </Typography>
          )}
        </Paper>

        {/* Timestamp + action buttons for agent messages */}
        {isAgent && !msg.streaming && (
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              gap: 0.5,
              mt: 0.5,
              opacity: hovered ? 1 : 0,
              transition: 'opacity 0.15s ease'
            }}
          >
            <Typography variant="caption" sx={{ fontFamily, fontSize: '11px', color: '#9aa0a6', mr: 0.5 }}>
              {msg.timestamp}
            </Typography>
            <Tooltip title={copied ? 'Copied!' : 'Copy'}>
              <IconButton size="small" onClick={handleCopy} sx={{ color: copied ? '#34a853' : '#9aa0a6', p: 0.3 }}>
                {copied ? <CheckIcon sx={{ fontSize: 14 }} /> : <CopyIcon sx={{ fontSize: 14 }} />}
              </IconButton>
            </Tooltip>
            <Tooltip title={feedbackGiven === 1 ? 'Thanks!' : 'Helpful'}>
              <IconButton
                size="small"
                onClick={() => handleFeedback(1)}
                disabled={feedbackGiven !== null}
                sx={{ color: feedbackGiven === 1 ? '#34a853' : '#9aa0a6', p: 0.3, '&:hover': { color: '#34a853' } }}
              >
                <ThumbUpIcon sx={{ fontSize: 14 }} />
              </IconButton>
            </Tooltip>
            <Tooltip title={feedbackGiven === -1 ? 'Thanks!' : 'Not helpful'}>
              <IconButton
                size="small"
                onClick={() => handleFeedback(-1)}
                disabled={feedbackGiven !== null}
                sx={{ color: feedbackGiven === -1 ? '#ea4335' : '#9aa0a6', p: 0.3, '&:hover': { color: '#ea4335' } }}
              >
                <ThumbDownIcon sx={{ fontSize: 14 }} />
              </IconButton>
            </Tooltip>
          </Box>
        )}
        {/* Timestamp for user messages */}
        {msg.sender === 'user' && (
          <Typography variant="caption" sx={{ fontFamily, fontSize: '11px', color: '#9aa0a6', mt: 0.4, display: 'block', textAlign: 'right' }}>
            {msg.timestamp}
          </Typography>
        )}
      </Box>
    </Box>
  );
}


// ─── Main Component ───────────────────────────────────────────────────────────
function ChatInterface({ open, onClose, activeSite, dashboardData }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [selectedDiscipline, setSelectedDiscipline] = useState('all');
  const [isMinimized, setIsMinimized] = useState(false);
  const [showSettings, setShowSettings] = useState(true); // Show settings by default
  const messagesEndRef = useRef(null);
  const messagesBoxRef = useRef(null);
  const inputRef = useRef(null);

  // Model selector
  const [models, setModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState('deepseek/deepseek-chat'); // Changed default to working DeepSeek

  useEffect(() => {
    axios.get(`${API_URL}/a2a/models`)
      .then(res => {
        setModels(res.data.models || []);
        if (res.data.default) setSelectedModel(res.data.default);
      })
      .catch(() => {});
  }, []);

  // ── Auto-scroll: fires both on message array changes AND during streaming ──
  const scrollToBottom = useCallback((smooth = true) => {
    messagesEndRef.current?.scrollIntoView({ behavior: smooth ? 'smooth' : 'auto' });
  }, []);

  useEffect(() => { scrollToBottom(); }, [messages, scrollToBottom]);

  useEffect(() => {
    if (open && inputRef.current) {
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [open]);

  // ── Send / stream ─────────────────────────────────────────────────────────
  const handleSend = async (overrideText) => {
    const text = (overrideText || input).trim();
    if (!text || loading) return;

    const userMessage = {
      id: Date.now(),
      text,
      sender: 'user',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    const streamingMessageId = Date.now() + 1;
    setMessages(prev => [...prev, {
      id: streamingMessageId,
      text: '',
      sender: 'agent',
      agent: selectedDiscipline,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      streaming: true
    }]);

    try {
      const response = await fetch(`${API_URL}/agentic-chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          discipline: selectedDiscipline === 'all' ? null : selectedDiscipline,
          site: activeSite || 'DAL',
          model_id: selectedModel,
          stream: true,
          context: dashboardData && Array.isArray(dashboardData) ? { total_items: dashboardData.length, has_backlog: true, active_view: 'backlog' } : null
        })
      });

      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let fullText = '';
      let agent = selectedDiscipline;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        for (const line of chunk.split('\n')) {
          if (!line.startsWith('data: ')) continue;
          try {
            const data = JSON.parse(line.substring(6));
            if (data.type === 'metadata') {
              agent = data.agent;
            } else if (data.type === 'content') {
              fullText += data.content;
              setMessages(prev =>
                prev.map(msg =>
                  msg.id === streamingMessageId ? { ...msg, text: fullText, agent } : msg
                )
              );
              // Scroll on every streamed chunk
              scrollToBottom(false);
            } else if (data.type === 'done') {
              setMessages(prev =>
                prev.map(msg =>
                  msg.id === streamingMessageId ? { ...msg, streaming: false } : msg
                )
              );
              setLoading(false);
            } else if (data.type === 'error') {
              setMessages(prev =>
                prev.map(msg =>
                  msg.id === streamingMessageId
                    ? { ...msg, text: `Error: ${data.error}`, streaming: false, sender: 'error' }
                    : msg
                )
              );
              setLoading(false);
            }
          } catch (e) {
            console.error('Failed to parse SSE data:', e);
          }
        }
      }
    } catch (error) {
      console.error('Streaming error:', error);
      setMessages(prev =>
        prev.map(msg =>
          msg.id === streamingMessageId
            ? { ...msg, text: 'Failed to get response from agent. Please try again.', streaming: false, sender: 'error' }
            : msg
        )
      );
      setLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const clearChat = () => setMessages([]);

  // ── Feedback handler ────────────────────────────────────────────────────────
  const handleFeedback = useCallback((msg, rating) => {
    // Find the preceding user message as the query
    const idx = messages.findIndex(m => m.id === msg.id);
    const userMsg = messages.slice(0, idx).reverse().find(m => m.sender === 'user');

    axios.post(`${API_URL}/chat/feedback`, {
      message_id: String(msg.id),
      query: userMsg?.text || '',
      response: msg.text || '',
      rating,
      discipline: msg.agent || selectedDiscipline,
      model_id: selectedModel,
      site: activeSite || 'DAL'
    }).catch(err => console.error('Feedback save failed:', err));
  }, [messages, selectedDiscipline, selectedModel, activeSite]);

  const getAgentTitle = () => {
    if (selectedDiscipline === 'all') return 'Engineering Support';
    const agent = DISCIPLINES.find(d => d.value === selectedDiscipline);
    return agent ? `${agent.label}` : 'Engineering Support';
  };

  const getGreetingMessage = () => {
    if (selectedDiscipline === 'all')
      return "Hi, I'm here to help with your engineering questions. How can I assist you today?";
    const agent = DISCIPLINES.find(d => d.value === selectedDiscipline);
    return `Hi, I'm your ${agent?.label || 'Engineering'} assistant. How can I assist you today?`;
  };

  const agentColor = DISCIPLINES.find(d => d.value === selectedDiscipline)?.color || '#9c27b0';
  const mdComponents = markdownComponents(FONT_FAMILY);

  return (
    <Drawer
      anchor="right"
      open={open}
      onClose={onClose}
      sx={{
        width: 430,
        flexShrink: 0,
        '& .MuiDrawer-paper': {
          width: 430,
          boxSizing: 'border-box',
          bgcolor: '#ffffff',
          fontFamily: FONT_FAMILY,
          boxShadow: '-4px 0 24px rgba(0,0,0,0.10)'
        }
      }}
    >
      <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', bgcolor: '#ffffff' }}>

        {/* ── Header ─────────────────────────────────────────────────────── */}
        <Box sx={{
          px: 2,
          py: 1.25,
          borderBottom: '1px solid #f0f0f0',
          bgcolor: '#ffffff',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          minHeight: '54px'
        }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.25 }}>
            {/* Brand mark */}
            <Box sx={{
              width: 32, height: 32, borderRadius: '8px',
              background: `linear-gradient(135deg, ${agentColor} 0%, #9c27b0 100%)`,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              flexShrink: 0
            }}>
              <SparkleIcon sx={{ color: '#fff', fontSize: 18 }} />
            </Box>
            <Box>
              <Typography sx={{ fontFamily: FONT_FAMILY, fontWeight: 600, fontSize: '14px', color: '#202124', lineHeight: 1.2 }}>
                {getAgentTitle()}
              </Typography>
              <Typography sx={{ fontFamily: FONT_FAMILY, fontSize: '11px', color: '#34a853', lineHeight: 1.2 }}>
                ● Online
              </Typography>
            </Box>
          </Box>

          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            <Tooltip title="Settings">
              <IconButton size="small" onClick={() => setShowSettings(s => !s)} sx={{ color: showSettings ? agentColor : '#5f6368', '&:hover': { bgcolor: 'rgba(0,0,0,0.04)' } }}>
                <SettingsIcon sx={{ fontSize: 18 }} />
              </IconButton>
            </Tooltip>
            <Tooltip title="Clear chat">
              <IconButton size="small" onClick={clearChat} sx={{ color: '#5f6368', fontSize: '12px', fontFamily: FONT_FAMILY, px: 0.75, '&:hover': { bgcolor: 'rgba(0,0,0,0.04)' } }}>
                <Typography sx={{ fontSize: '11px', fontFamily: FONT_FAMILY, fontWeight: 500 }}>Clear</Typography>
              </IconButton>
            </Tooltip>
            <Tooltip title="Minimize">
              <IconButton size="small" onClick={() => setIsMinimized(!isMinimized)} sx={{ color: '#5f6368', '&:hover': { bgcolor: 'rgba(0,0,0,0.04)' } }}>
                <MinimizeIcon sx={{ fontSize: 18 }} />
              </IconButton>
            </Tooltip>
            <Tooltip title="Close">
              <IconButton size="small" onClick={onClose} sx={{ color: '#5f6368', '&:hover': { bgcolor: 'rgba(0,0,0,0.04)' } }}>
                <CloseIcon sx={{ fontSize: 18 }} />
              </IconButton>
            </Tooltip>
          </Box>
        </Box>

        {/* ── Collapsible Settings Panel ──────────────────────────────────── */}
        <Collapse in={showSettings}>
          <Box sx={{ px: 2, pt: 1.5, pb: 1.5, borderBottom: '1px solid #f0f0f0', bgcolor: '#fafafa', display: 'flex', gap: 1.5 }}>
            <FormControl size="small" sx={{ flex: 1 }}>
              <InputLabel sx={{ fontFamily: FONT_FAMILY, fontSize: '13px' }}>Agent</InputLabel>
              <Select
                value={selectedDiscipline}
                onChange={(e) => { setSelectedDiscipline(e.target.value); setMessages([]); }}
                label="Agent"
                sx={{ fontFamily: FONT_FAMILY, fontSize: '13px' }}
              >
                {DISCIPLINES.map(disc => (
                  <MenuItem key={disc.value} value={disc.value} sx={{ fontFamily: FONT_FAMILY, fontSize: '13px' }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Box sx={{ width: 8, height: 8, borderRadius: '50%', bgcolor: disc.color, flexShrink: 0 }} />
                      {disc.label}
                    </Box>
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <FormControl size="small" sx={{ flex: 1 }}>
              <InputLabel sx={{ fontFamily: FONT_FAMILY, fontSize: '13px' }}>Model</InputLabel>
              <Select
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
                label="Model"
                sx={{ fontFamily: FONT_FAMILY, fontSize: '13px' }}
              >
                {models.length > 0 ? (
                  models.map(m => (
                    <MenuItem key={m.id} value={m.id} disabled={!m.available} sx={{ fontFamily: FONT_FAMILY, fontSize: '13px' }}>
                      {getModelAlias(m)}
                    </MenuItem>
                  ))
                ) : (
                  <MenuItem value="openrouter/gpt-4o-mini" sx={{ fontFamily: FONT_FAMILY, fontSize: '13px' }}>
                    Standard Analysis (gpt-4o-mini)
                  </MenuItem>
                )}
              </Select>
            </FormControl>
          </Box>
        </Collapse>

        {/* ── Messages Area ───────────────────────────────────────────────── */}
        {!isMinimized && (
          <Box ref={messagesBoxRef} sx={{ flex: 1, overflowY: 'auto', px: 2, pt: 2, pb: 1, bgcolor: '#ffffff',
            '&::-webkit-scrollbar': { width: '4px' },
            '&::-webkit-scrollbar-thumb': { bgcolor: '#dadce0', borderRadius: '4px' },
            '&::-webkit-scrollbar-track': { bgcolor: 'transparent' }
          }}>

            {/* Date separator */}
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2.5 }}>
              <Divider sx={{ flex: 1, borderColor: '#f0f0f0' }} />
              <Typography variant="caption" sx={{ px: 1.5, color: '#9aa0a6', fontFamily: FONT_FAMILY, fontSize: '11px', bgcolor: '#ffffff' }}>
                Today
              </Typography>
              <Divider sx={{ flex: 1, borderColor: '#f0f0f0' }} />
            </Box>

            {/* Greeting */}
            <Box sx={{ mb: 2.5 }}>
              <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1.5 }}>
                <Box sx={{ width: 28, height: 28, borderRadius: '8px', background: `linear-gradient(135deg, ${agentColor} 0%, #9c27b0 100%)`, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, mt: 0.25 }}>
                  <SparkleIcon sx={{ color: '#fff', fontSize: 16 }} />
                </Box>
                <Box sx={{ flex: 1 }}>
                  <Typography sx={{ fontFamily: FONT_FAMILY, fontSize: '12px', color: '#5f6368', mb: 0.4, fontWeight: 500 }}>
                    {getAgentTitle()}
                  </Typography>
                  <Paper elevation={0} sx={{ p: '10px 14px', bgcolor: '#f8f9fa', borderRadius: '4px 18px 18px 18px', border: '1px solid #f0f0f0' }}>
                    <Typography sx={{ fontFamily: FONT_FAMILY, fontSize: '14px', color: '#202124', lineHeight: 1.6 }}>
                      {getGreetingMessage()}
                    </Typography>
                  </Paper>
                </Box>
              </Box>
            </Box>

            {/* Suggested Prompts (shown when no messages yet) */}
            {messages.length === 0 && (
              <Box sx={{ mb: 3 }}>
                <Typography sx={{ fontFamily: FONT_FAMILY, fontSize: '12px', color: '#9aa0a6', mb: 1, ml: 0.5 }}>
                  Suggested
                </Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.75 }}>
                  {SUGGESTED_PROMPTS.map((prompt, i) => (
                    <Chip
                      key={i}
                      label={prompt}
                      onClick={() => handleSend(prompt)}
                      size="small"
                      sx={{
                        fontFamily: FONT_FAMILY,
                        fontSize: '13px',
                        bgcolor: '#f8f9fa',
                        color: '#202124',
                        border: '1px solid #e8eaed',
                        borderRadius: '8px',
                        height: 'auto',
                        py: 0.6,
                        px: 0.5,
                        justifyContent: 'flex-start',
                        cursor: 'pointer',
                        '& .MuiChip-label': { whiteSpace: 'normal', px: 1 },
                        '&:hover': { bgcolor: '#f3eef9', borderColor: agentColor, color: agentColor }
                      }}
                    />
                  ))}
                </Box>
              </Box>
            )}

            {/* Message list */}
            {messages.map((msg) => (
              <MessageBubble
                key={msg.id}
                msg={msg}
                agentTitle={DISCIPLINES.find(d => d.value === (msg.agent || 'all'))?.label || getAgentTitle()}
                fontFamily={FONT_FAMILY}
                mdComponents={mdComponents}
                onFeedback={handleFeedback}
              />
            ))}

            {/* Typing indicator — shown while waiting for first token */}
            {loading && messages[messages.length - 1]?.streaming && messages[messages.length - 1]?.text === '' && (
              <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1.5, mb: 2 }}>
                <Box sx={{ width: 28, height: 28, borderRadius: '8px', background: `linear-gradient(135deg, ${agentColor} 0%, #9c27b0 100%)`, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                  <SparkleIcon sx={{ color: '#fff', fontSize: 16 }} />
                </Box>
                <Box sx={{ flex: 1 }}>
                  <Typography sx={{ fontFamily: FONT_FAMILY, fontSize: '12px', color: '#5f6368', mb: 0.4, fontWeight: 500 }}>
                    {getAgentTitle()}
                  </Typography>
                  <Paper elevation={0} sx={{ p: '10px 14px', bgcolor: '#f8f9fa', borderRadius: '4px 18px 18px 18px', border: '1px solid #f0f0f0', display: 'inline-flex' }}>
                    <TypingDots />
                  </Paper>
                </Box>
              </Box>
            )}

            <div ref={messagesEndRef} />
          </Box>
        )}

        {/* ── Disclaimer ─────────────────────────────────────────────────── */}
        <Box sx={{ px: 2, py: 1, borderTop: '1px solid #f0f0f0', bgcolor: '#fafafa' }}>
          <Typography variant="caption" sx={{ fontFamily: FONT_FAMILY, fontSize: '10.5px', color: '#9aa0a6', lineHeight: 1.4, display: 'block' }}>
            AI responses may be inaccurate. Use is subject to our{' '}
            <Link href="#" sx={{ color: '#1a73e8', textDecoration: 'none', '&:hover': { textDecoration: 'underline' } }}>Terms</Link>,{' '}
            <Link href="#" sx={{ color: '#1a73e8', textDecoration: 'none', '&:hover': { textDecoration: 'underline' } }}>AI Policy</Link> and{' '}
            <Link href="#" sx={{ color: '#1a73e8', textDecoration: 'none', '&:hover': { textDecoration: 'underline' } }}>Privacy</Link>.
          </Typography>
        </Box>

        {/* ── Input Area ─────────────────────────────────────────────────── */}
        <Box sx={{ p: '10px 14px 14px', bgcolor: '#ffffff', borderTop: '1px solid #f0f0f0' }}>
          <Box sx={{
            display: 'flex',
            alignItems: 'flex-end',
            gap: 0,
            bgcolor: '#f8f9fa',
            borderRadius: '24px',
            border: '1.5px solid',
            borderColor: input ? agentColor : '#e8eaed',
            px: 1.5,
            py: 0.5,
            transition: 'border-color 0.2s ease',
            '&:focus-within': { borderColor: agentColor }
          }}>
            <TextField
              inputRef={inputRef}
              fullWidth
              multiline
              maxRows={4}
              placeholder="Ask anything about your assets…"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              disabled={loading}
              variant="standard"
              sx={{
                '& .MuiInputBase-root': { pb: 0.5, pt: 0.75 },
                '& .MuiInputBase-input': {
                  fontSize: '14px',
                  fontFamily: FONT_FAMILY,
                  color: '#202124',
                  lineHeight: 1.5,
                  '&::placeholder': { color: '#9aa0a6', opacity: 1 }
                },
                '& .MuiInput-underline:before': { borderBottom: 'none' },
                '& .MuiInput-underline:after': { borderBottom: 'none' },
                '& .MuiInput-underline:hover:before': { borderBottom: 'none !important' }
              }}
            />
            <Tooltip title={loading ? 'Responding…' : 'Send (Enter)'}>
              <span>
                <IconButton
                  onClick={() => handleSend()}
                  disabled={!input.trim() || loading}
                  size="small"
                  sx={{
                    mb: 0.5,
                    width: 34,
                    height: 34,
                    borderRadius: '50%',
                    bgcolor: input.trim() && !loading ? agentColor : 'transparent',
                    color: input.trim() && !loading ? '#ffffff' : '#dadce0',
                    flexShrink: 0,
                    transition: 'all 0.15s ease',
                    '&:hover': {
                      bgcolor: input.trim() && !loading ? agentColor : 'transparent',
                      opacity: 0.85
                    },
                    '&.Mui-disabled': { bgcolor: 'transparent', color: '#dadce0' }
                  }}
                >
                  <SendIcon sx={{ fontSize: 16 }} />
                </IconButton>
              </span>
            </Tooltip>
          </Box>
          <Typography sx={{ fontFamily: FONT_FAMILY, fontSize: '10.5px', color: '#c0c4c8', mt: 0.75, textAlign: 'center' }}>
            Press Enter to send · Shift+Enter for new line
          </Typography>
        </Box>
      </Box>
    </Drawer>
  );
}

export default ChatInterface;
