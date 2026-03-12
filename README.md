# 🔍 Backlog Inspector Dashboard

**AI-Powered Offshore Topside Inspection Management System**

A modern web application that processes Excel-based inspection backlog data and provides an intelligent dashboard with risk assessment, prioritization, and actionable insights for offshore oil & gas operations.

---

## ✨ Features

- **📊 Excel Processing**: Automatically parses complex inspection database spreadsheets
- **🤖 AI-Powered Analysis**: Uses CrewAI and LangChain for intelligent data enrichment
- **🎯 Risk Assessment**: Automatically categorizes items by risk level (High/Medium/Low)
- **📈 Real-time Dashboard**: Beautiful Material-UI interface with statistics and color-coded rows
- **🔄 SECE Prioritization**: Special handling for Safety & Environmental Critical Equipment
- **📤 Export Functionality**: Download processed data as CSV
- **⚡ Fast & Responsive**: Modern tech stack with React + FastAPI

---

## 🏗️ Architecture

```
┌─────────────────┐
│  React Frontend │  (Vite + Material-UI)
│   Port: 5173    │
└────────┬────────┘
         │ HTTP/REST
         ▼
┌─────────────────┐
│  FastAPI Backend│  (Python 3.11)
│   Port: 8000    │
└────────┬────────┘
         │
    ┌────┴────┬──────────┬─────────────┐
    ▼         ▼          ▼             ▼
 openpyxl  CrewAI  LangChain    OpenRouter
 (Excel)   (Agents)  (LLM)       (API)
```

---

## 🚀 Quick Start (MacBook Pro)

### Prerequisites

- **Python 3.11+**: `brew install python@3.11`
- **Node.js 20+**: `brew install node`
- **Git**: `brew install git`
- **OpenRouter API Key**: Get from [openrouter.ai/keys](https://openrouter.ai/keys)

### Option 1: Docker Setup (Recommended)

```bash
# Clone or navigate to project directory
cd backlog-dashboard

# Copy environment file and add your API key
cp backend/.env.example backend/.env
# Edit backend/.env and set: OPENROUTER_API_KEY=your_key_here

# Start all services
docker-compose up --build

# Access the application
open http://localhost:5173
```

### Option 2: Manual Setup

#### 1️⃣ Backend Setup

```bash
cd backend

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On macOS/Linux

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Setup environment variables
cp .env.example .env
nano .env  # Add your OPENROUTER_API_KEY

# Start backend server
python main.py
# Or: uvicorn main:app --reload --port 8000
```

Backend will be available at: http://localhost:8000

#### 2️⃣ Frontend Setup

```bash
# Open new terminal
cd frontend

# Install dependencies
npm install

# Setup environment (optional)
cp .env.example .env

# Start development server
npm run dev
```

Frontend will be available at: http://localhost:5173

---

## 📖 Usage Guide

### 1. Prepare Your Excel File

Your Excel file should have a sheet named "Data Base" (or "DataBase", case-insensitive) with these columns:

**Required Columns:**
- `Tag` - Equipment tag ID
- `Backlog?` - "Yes" for backlog items
- `Days in Backlog` - Number of days overdue

**Recommended Columns:**
- `Item Class` - Type of inspection
- `Description` - Inspection description
- `Functional Location` - Format: `GIR/LOCATION/SYSTEM/...`
- `Due Date` - Inspection due date
- `SECE STATUS` - "SCE" for safety-critical equipment
- `M. Item`, `M. Plan` - Maintenance codes

### 2. Upload and Process

1. Click **"Select Excel File"** button
2. Choose your `.xls`, `.xlsx`, or `.xlsm` file
3. Click **"Process Backlog"**
4. Wait for AI analysis (10-30 seconds)
5. View the dashboard with color-coded risk levels

### 3. Interpret Results

**Risk Levels:**
- 🔴 **High Risk** (Red): >90 days overdue OR SECE >60 days
- 🟡 **Medium Risk** (Yellow): 30-90 days overdue
- 🟢 **Low Risk** (Green): <30 days overdue

**Actions:**
- **Escalate**: Immediate action required
- **Schedule**: Plan inspection soon

**Statistics Cards:**
- View distribution of risk levels
- Track total backlog items
- Monitor SECE equipment

### 4. Export Data

Click the **Download** icon to export processed data as CSV for reporting or further analysis.

---

## 🛠️ Configuration

### Backend Configuration (backend/.env)

```env
# Required
OPENROUTER_API_KEY=sk-or-v1-xxxxx

# Optional
OPENROUTER_MODEL=minimax/mm-m2
LLM_TEMPERATURE=0.2
LLM_MAX_TOKENS=3000
LOG_LEVEL=INFO
BACKEND_PORT=8000
```

### Frontend Configuration (frontend/.env)

```env
VITE_API_URL=http://localhost:8000
```

---

## 🧪 Testing

### Test Backend API

```bash
# Check health
curl http://localhost:8000/

# Test with sample file
curl -X POST http://localhost:8000/process-backlog \
  -F "database=@sample_database.xlsx"
```

### Run Python Tests

```bash
cd backend
pytest tests/ -v
```

---

## 📁 Project Structure

```
backlog-dashboard/
├── backend/
│   ├── main.py              # FastAPI application
│   ├── utils.py             # Excel parsing & AI processing
│   ├── models.py            # Pydantic data models
│   ├── requirements.txt     # Python dependencies
│   ├── .env.example         # Environment template
│   └── Dockerfile           # Backend container
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # Main React component
│   │   └── main.jsx         # React entry point
│   ├── index.html           # HTML template
│   ├── vite.config.js       # Vite configuration
│   ├── package.json         # Node dependencies
│   ├── .env.example         # Frontend env template
│   └── Dockerfile           # Frontend container
├── docker-compose.yml       # Multi-container orchestration
└── README.md               # This file
```

---

## 🐛 Troubleshooting

### Issue: "OPENROUTER_API_KEY not set"

**Solution**: 
```bash
cd backend
cp .env.example .env
nano .env  # Add your API key
```

### Issue: "Port 8000 already in use"

**Solution**:
```bash
# Find and kill process
lsof -ti:8000 | xargs kill -9

# Or use different port
uvicorn main:app --port 8001
```

### Issue: "No sheet matching 'Data Base' found"

**Solution**: 
- Ensure your Excel file has a sheet named "Data Base" or "DataBase"
- Check for typos in sheet name
- Sheet names are case-insensitive

### Issue: Frontend can't connect to backend

**Solution**:
```bash
# Check backend is running
curl http://localhost:8000/

# Check CORS configuration in backend/main.py
# Ensure frontend URL is in allowed_origins
```

### Issue: "Module not found" errors

**Solution**:
```bash
# Backend
cd backend
pip install -r requirements.txt

# Frontend  
cd frontend
rm -rf node_modules package-lock.json
npm install
```

### Issue: AI processing fails

**Solution**: System automatically falls back to rule-based processing. Check:
- API key validity
- Network connection
- OpenRouter service status

---

## 🔒 Security Notes

- **API Keys**: Never commit `.env` files to version control
- **File Uploads**: Only processes Excel files, validates extensions
- **Data Privacy**: Files are processed in `/tmp` and deleted after processing
- **CORS**: Configured for local development only

---

## 🚢 Deployment (Production)

### Using Docker

```bash
# Build production images
docker-compose -f docker-compose.prod.yml build

# Deploy
docker-compose -f docker-compose.prod.yml up -d
```

### Manual Deployment

**Backend:**
```bash
cd backend
pip install -r requirements.txt
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker
```

**Frontend:**
```bash
cd frontend
npm run build
# Serve dist/ folder with nginx or similar
```

---

## 📊 API Documentation

Once the backend is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Endpoints

#### `GET /`
Health check endpoint

**Response:**
```json
{
  "status": "healthy",
  "service": "Backlog Inspector API",
  "version": "2.0.0",
  "ai_enabled": true
}
```

#### `POST /process-backlog`
Process Excel backlog file

**Request:**
- Content-Type: `multipart/form-data`
- Body: `database` (file)

**Response:**
```json
{
  "success": true,
  "message": "Successfully processed 45 items",
  "items_processed": 45,
  "dashboard": {
    "table": [...]
  },
  "timestamp": "2025-11-01T10:30:00"
}
```

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open Pull Request

---

## 📝 License

This project is proprietary software for offshore inspection management.

---

## 🙋 Support

For issues or questions:
- Check the troubleshooting section
- Review API documentation
- Check logs: `docker-compose logs` or individual service logs

---

## 🎯 Roadmap

- [ ] Multi-user authentication
- [ ] Historical trend analysis
- [ ] Email notifications for high-risk items
- [ ] Integration with SAP maintenance systems
- [ ] Mobile app (React Native)
- [ ] PDF report generation
- [ ] Advanced filtering and search
- [ ] Bulk actions on dashboard items

---

**Built with care for Offshore Operations Teams**

---

**Powered by FO/STP/INS/MET | Contact: Ataliba Miguel**
