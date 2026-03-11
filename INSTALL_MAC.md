# 🍎 MacBook Pro Installation Instructions

## Step-by-Step Guide to Run Backlog Inspector Dashboard

---

## ⚡ FASTEST METHOD (5 minutes)

### 1️⃣ Install Prerequisites (if not already installed)

```bash
# Install Homebrew (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python 3.11
brew install python@3.11

# Install Node.js
brew install node

# Install Docker Desktop (optional, for Docker method)
# Download from: https://www.docker.com/products/docker-desktop/
```

### 2️⃣ Get OpenRouter API Key

1. Go to https://openrouter.ai/keys
2. Sign up or log in
3. Create a new API key
4. Copy the key (starts with `sk-or-v1-`)

### 3️⃣ Setup Project

```bash
# Navigate to the project folder
cd /path/to/backlog-dashboard

# Make setup script executable
chmod +x setup.sh

# Run automated setup
./setup.sh
```

Choose option **1** (Quick Setup - Docker) or **2** (Manual Setup)

### 4️⃣ Configure API Key

```bash
# Edit the .env file
nano backend/.env

# Add your API key:
OPENROUTER_API_KEY=sk-or-v1-YOUR_KEY_HERE

# Save: Ctrl+O, Enter, Ctrl+X
```

### 5️⃣ Start Services

**Option A: Using Docker**
```bash
docker-compose up --build
```

**Option B: Manual**
```bash
# Terminal 1 - Backend
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py

# Terminal 2 - Frontend
cd frontend
npm install
npm run dev
```

### 6️⃣ Access Application

Open browser: http://localhost:5173

---

## 📊 Generate Test Data

```bash
# In project root
python3 generate_test_data.py
```

This creates `sample_backlog_data.xlsx` with 50 test items.

---

## 🧪 Test the Application

1. Click "Select Excel File"
2. Choose `sample_backlog_data.xlsx`
3. Click "Process Backlog"
4. Wait 10-30 seconds
5. View the dashboard!

---

## 🛑 Stop Services

**Docker:**
```bash
docker-compose down
```

**Manual:**
```bash
# Press Ctrl+C in both terminal windows
```

---

## 🔍 Verify Installation

Run these commands to verify everything is installed:

```bash
# Check Python
python3 --version
# Should show: Python 3.11.x or higher

# Check Node.js
node --version
# Should show: v20.x.x or higher

# Check npm
npm --version
# Should show: 10.x.x or higher

# Check Docker (if using Docker method)
docker --version
docker-compose --version
```

---

## 🐛 Common Issues on MacBook

### Issue: "Permission denied" when running setup.sh

**Solution:**
```bash
chmod +x setup.sh
./setup.sh
```

### Issue: "python3: command not found"

**Solution:**
```bash
# Install Python via Homebrew
brew install python@3.11

# Add to PATH (if needed)
echo 'export PATH="/usr/local/opt/python@3.11/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### Issue: "node: command not found"

**Solution:**
```bash
brew install node
```

### Issue: Port 8000 already in use

**Solution:**
```bash
# Find and kill process using port 8000
lsof -ti:8000 | xargs kill -9
```

### Issue: "Cannot connect to Docker daemon"

**Solution:**
1. Open Docker Desktop app
2. Wait for it to start (whale icon in menu bar)
3. Try again

### Issue: M1/M2 Mac compatibility

**Solution:** 
All dependencies are compatible with Apple Silicon. If you encounter issues:
```bash
# Install Rosetta 2 (if needed)
softwareupdate --install-rosetta

# Use native ARM versions
arch -arm64 brew install python@3.11
```

---

## 📁 Project Location

After extraction, your project structure should be:

```
backlog-dashboard/
├── backend/          ← Python FastAPI code
├── frontend/         ← React application
├── setup.sh          ← Automated setup script
├── README.md         ← Full documentation
└── QUICKSTART.md     ← Quick reference
```

---

## 🎯 Next Steps

1. ✅ Install prerequisites
2. ✅ Get API key
3. ✅ Run `./setup.sh`
4. ✅ Configure `.env` file
5. ✅ Start services
6. ✅ Open http://localhost:5173
7. ✅ Upload test file
8. 🎉 You're done!

---

## 📚 Additional Resources

- **Full Documentation**: See `README.md`
- **API Reference**: http://localhost:8000/docs (when running)
- **Troubleshooting**: See `README.md` troubleshooting section
- **Deployment**: See `DEPLOYMENT_CHECKLIST.md`

---

## 💡 Pro Tips for Mac Users

1. **Use iTerm2** instead of Terminal for better experience
2. **Install Oh My Zsh** for better shell experience
3. **Use VS Code** for editing code:
   ```bash
   brew install --cask visual-studio-code
   code backlog-dashboard
   ```
4. **Keep Docker Desktop updated** for best performance
5. **Use Homebrew** to manage all tools

---

## ⚡ Quick Commands Reference

```bash
# Start everything (Docker)
docker-compose up

# Start everything (Manual)
# Terminal 1:
cd backend && source venv/bin/activate && python main.py
# Terminal 2:
cd frontend && npm run dev

# Stop everything (Docker)
docker-compose down

# View logs (Docker)
docker-compose logs -f

# Generate test data
python3 generate_test_data.py

# Run tests
cd backend && pytest tests/ -v

# Clean rebuild (Docker)
docker-compose down
docker-compose up --build

# Clean reinstall (Manual)
cd backend && rm -rf venv && python3 -m venv venv
cd frontend && rm -rf node_modules && npm install
```

---

## 🎉 Success Indicators

You know it's working when:
- ✅ No errors in terminal/console
- ✅ Can access http://localhost:5173
- ✅ Can upload Excel file
- ✅ Dashboard shows with colored rows
- ✅ Statistics cards display numbers

---

**Need Help?** Check the troubleshooting section in README.md or review the logs for error messages.

**Have Fun!** 🚀
