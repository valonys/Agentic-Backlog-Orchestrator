# ✅ Deployment & Testing Checklist

## 📋 Pre-Deployment Checklist

### Environment Setup
- [ ] Python 3.11+ installed and verified (`python3 --version`)
- [ ] Node.js 20+ installed and verified (`node --version`)
- [ ] Docker installed (if using Docker setup)
- [ ] OpenRouter API key obtained from https://openrouter.ai/keys
- [ ] Git repository initialized (optional)

### Configuration
- [ ] `backend/.env` created from `.env.example`
- [ ] `OPENROUTER_API_KEY` set in `backend/.env`
- [ ] `frontend/.env` created (optional, uses defaults)
- [ ] All sensitive files added to `.gitignore`

### Dependencies
- [ ] Backend: `pip install -r backend/requirements.txt` completed
- [ ] Frontend: `npm install` in frontend/ completed
- [ ] No dependency conflicts or errors

---

## 🧪 Testing Checklist

### Backend Tests
```bash
cd backend
source venv/bin/activate  # If using venv
pytest tests/ -v
```

- [ ] All unit tests pass
- [ ] Health check endpoint responds (`curl http://localhost:8000/`)
- [ ] API documentation accessible at http://localhost:8000/docs

### Frontend Tests
```bash
cd frontend
npm run dev
```

- [ ] Development server starts without errors
- [ ] Can access UI at http://localhost:5173
- [ ] No console errors in browser

### Integration Tests
- [ ] Generate test data: `python3 generate_test_data.py`
- [ ] Upload `sample_backlog_data.xlsx` through UI
- [ ] Processing completes successfully
- [ ] Dashboard displays with color-coded rows
- [ ] Statistics cards show correct counts
- [ ] Export to CSV works
- [ ] Can reset and upload different file

### AI Processing Tests
- [ ] With valid API key: AI enrichment works
- [ ] With invalid/no API key: Falls back to rule-based processing
- [ ] Error messages are user-friendly

---

## 🚀 Docker Deployment Checklist

### Build & Start
```bash
docker-compose up --build
```

- [ ] Backend container builds successfully
- [ ] Frontend container builds successfully
- [ ] Both services start and are healthy
- [ ] Can access frontend at http://localhost:5173
- [ ] Backend API responds at http://localhost:8000

### Health Checks
```bash
# Check running containers
docker-compose ps

# View logs
docker-compose logs backend
docker-compose logs frontend

# Check backend health
curl http://localhost:8000/
```

- [ ] All containers showing "Up" status
- [ ] No critical errors in logs
- [ ] Health check passes

---

## 📊 Manual Deployment Checklist

### Backend Deployment
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

- [ ] Virtual environment created
- [ ] All dependencies installed
- [ ] Server starts on port 8000
- [ ] No Python errors

### Frontend Deployment
```bash
cd frontend
npm install
npm run dev
```

- [ ] Node modules installed
- [ ] Vite dev server starts
- [ ] Hot reload working
- [ ] Can access at http://localhost:5173

---

## 🔍 Functionality Testing

### Core Features
- [ ] **File Upload**: Can select and upload .xls/.xlsx/.xlsm files
- [ ] **Processing**: File processes within 30 seconds
- [ ] **Dashboard**: Data displays in table with proper formatting
- [ ] **Risk Levels**: Items color-coded (red/yellow/green)
- [ ] **Statistics**: Correct counts for High/Medium/Low risk
- [ ] **SECE Marking**: SECE items properly identified
- [ ] **Sorting**: Items sorted by risk level and days overdue
- [ ] **Export**: CSV download works and contains all data
- [ ] **Reset**: Can clear and upload new file

### Error Handling
- [ ] Invalid file type shows error message
- [ ] Empty file handled gracefully
- [ ] Missing columns handled gracefully
- [ ] Network errors show user-friendly messages
- [ ] API errors don't crash the frontend

### Performance
- [ ] File upload < 5 seconds
- [ ] Processing 50 items < 30 seconds
- [ ] Dashboard renders < 2 seconds
- [ ] Export < 3 seconds
- [ ] UI remains responsive during processing

---

## 🔒 Security Checklist

### Credentials
- [ ] `.env` files not committed to git
- [ ] API keys stored securely
- [ ] No hardcoded secrets in code

### File Handling
- [ ] Only Excel files accepted
- [ ] File size limits enforced (if applicable)
- [ ] Temporary files cleaned up after processing
- [ ] No path traversal vulnerabilities

### Network
- [ ] CORS configured correctly
- [ ] HTTPS enabled (production)
- [ ] Rate limiting considered (production)

---

## 📝 Documentation Checklist

- [ ] README.md complete and accurate
- [ ] QUICKSTART.md tested and working
- [ ] API documentation accessible
- [ ] Code comments adequate
- [ ] Environment variables documented
- [ ] Troubleshooting section complete

---

## 🎯 Production Readiness

### Before Going Live
- [ ] All tests passing
- [ ] Error handling comprehensive
- [ ] Logging configured
- [ ] Monitoring setup (optional)
- [ ] Backup strategy defined
- [ ] Rollback plan in place

### Performance Optimization
- [ ] Frontend build optimized (`npm run build`)
- [ ] Static assets cached
- [ ] API response times acceptable
- [ ] Database queries optimized (if applicable)

### User Acceptance
- [ ] Demo with actual users completed
- [ ] Feedback incorporated
- [ ] Training materials prepared
- [ ] Support process defined

---

## 📱 Browser Compatibility

Test in these browsers:
- [ ] Chrome/Edge (latest)
- [ ] Firefox (latest)
- [ ] Safari (latest)

---

## 🛠️ Maintenance Checklist

### Regular Updates
- [ ] Dependencies updated monthly
- [ ] Security patches applied
- [ ] Logs reviewed weekly
- [ ] Backup verified monthly

### Monitoring
- [ ] Error rates tracked
- [ ] Performance metrics monitored
- [ ] User feedback collected
- [ ] API usage tracked

---

## ✅ Sign-Off

**Deployment Date**: _______________

**Deployed By**: _______________

**Verified By**: _______________

**Issues/Notes**: 
```
_______________________________________
_______________________________________
_______________________________________
```

---

**Status Legend:**
- ✅ Complete
- ⚠️ In Progress  
- ❌ Blocked
- ⏭️ Skipped (with reason)
