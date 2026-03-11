import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import { CssBaseline, ThemeProvider, createTheme } from '@mui/material'

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
  },
  typography: {
    fontFamily: '"Tw Cen MT", "Tw Cen MT Condensed", Arial, sans-serif',
    fontSize: 14, // 14px base font size
    htmlFontSize: 14, // Set base HTML font size to 14px
    h1: {
      fontSize: 14, // 14px
      fontFamily: '"Tw Cen MT", "Tw Cen MT Condensed", Arial, sans-serif',
    },
    h2: {
      fontSize: 14, // 14px
      fontFamily: '"Tw Cen MT", "Tw Cen MT Condensed", Arial, sans-serif',
    },
    h3: {
      fontSize: 14, // 14px
      fontFamily: '"Tw Cen MT", "Tw Cen MT Condensed", Arial, sans-serif',
    },
    h4: {
      fontSize: 14, // 14px
      fontFamily: '"Tw Cen MT", "Tw Cen MT Condensed", Arial, sans-serif',
    },
    h5: {
      fontSize: 14, // 14px
      fontFamily: '"Tw Cen MT", "Tw Cen MT Condensed", Arial, sans-serif',
    },
    h6: {
      fontSize: 14, // 14px
      fontFamily: '"Tw Cen MT", "Tw Cen MT Condensed", Arial, sans-serif',
    },
    body1: {
      fontSize: 14, // 14px
      fontFamily: '"Tw Cen MT", "Tw Cen MT Condensed", Arial, sans-serif',
    },
    body2: {
      fontSize: 14, // 14px
      fontFamily: '"Tw Cen MT", "Tw Cen MT Condensed", Arial, sans-serif',
    },
    button: {
      fontSize: 14, // 14px
      fontFamily: '"Tw Cen MT", "Tw Cen MT Condensed", Arial, sans-serif',
    },
    caption: {
      fontSize: 14, // 14px
      fontFamily: '"Tw Cen MT", "Tw Cen MT Condensed", Arial, sans-serif',
    },
  },
  components: {
    MuiTypography: {
      defaultProps: {
        fontFamily: '"Tw Cen MT", "Tw Cen MT Condensed", Arial, sans-serif',
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          fontSize: 14,
          fontFamily: '"Tw Cen MT", "Tw Cen MT Condensed", Arial, sans-serif',
        },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        root: {
          fontSize: 14,
          fontFamily: '"Tw Cen MT", "Tw Cen MT Condensed", Arial, sans-serif',
        },
      },
    },
    MuiTab: {
      styleOverrides: {
        root: {
          fontSize: 14,
          fontFamily: '"Tw Cen MT", "Tw Cen MT Condensed", Arial, sans-serif',
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        label: {
          fontSize: 14,
          fontFamily: '"Tw Cen MT", "Tw Cen MT Condensed", Arial, sans-serif',
        },
      },
    },
    MuiMenuItem: {
      styleOverrides: {
        root: {
          fontSize: 14,
          fontFamily: '"Tw Cen MT", "Tw Cen MT Condensed", Arial, sans-serif',
        },
      },
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          '& .MuiInputBase-input': {
            fontSize: 14,
            fontFamily: '"Tw Cen MT", "Tw Cen MT Condensed", Arial, sans-serif',
          },
        },
      },
    },
    MuiSelect: {
      styleOverrides: {
        root: {
          fontSize: 14,
          fontFamily: '"Tw Cen MT", "Tw Cen MT Condensed", Arial, sans-serif',
        },
      },
    },
  },
});

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <style>
        {`
          body, html {
            font-family: "Tw Cen MT", "Tw Cen MT Condensed", Arial, sans-serif;
            font-size: 14px;
          }
          .MuiTypography-root {
            font-family: "Tw Cen MT", "Tw Cen MT Condensed", Arial, sans-serif;
          }
          .MuiButton-root {
            font-family: "Tw Cen MT", "Tw Cen MT Condensed", Arial, sans-serif;
            font-size: 14px;
          }
          .MuiTableCell-root {
            font-family: "Tw Cen MT", "Tw Cen MT Condensed", Arial, sans-serif;
            font-size: 14px;
          }
          .MuiTab-root {
            font-family: "Tw Cen MT", "Tw Cen MT Condensed", Arial, sans-serif;
            font-size: 14px;
          }
          .MuiChip-label {
            font-family: "Tw Cen MT", "Tw Cen MT Condensed", Arial, sans-serif;
            font-size: 14px;
          }
          .MuiMenuItem-root {
            font-family: "Tw Cen MT", "Tw Cen MT Condensed", Arial, sans-serif;
            font-size: 14px;
          }
          .MuiInputBase-input {
            font-family: "Tw Cen MT", "Tw Cen MT Condensed", Arial, sans-serif;
            font-size: 14px;
          }
        `}
      </style>
      <App />
    </ThemeProvider>
  </React.StrictMode>,
)
