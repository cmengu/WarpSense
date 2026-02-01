# Installation and Testing Commands

## Step 1: Fix Frontend Dependencies (my-app)

```bash
cd /Users/ngchenmeng/test/my-app

# Remove existing node_modules and lock file
rm -rf node_modules package-lock.json

# Install with legacy peer deps to handle React 19 compatibility
npm install --legacy-peer-deps
```

## Step 2: Install iPad App Dependencies

```bash
cd /Users/ngchenmeng/test/ipad_app

# Remove existing node_modules and lock file if needed
rm -rf node_modules package-lock.json

# Install dependencies (use --legacy-peer-deps to handle React version conflicts)
npm install --legacy-peer-deps
```

## Step 3: Install Backend Dependencies

```bash
cd /Users/ngchenmeng/test/backend

# Create virtual environment if it doesn't exist
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Step 4: Run Tests

### Backend Tests
```bash
cd /Users/ngchenmeng/test/backend
source venv/bin/activate  # If not already activated
pytest tests/ -v
```

### Frontend Tests
```bash
cd /Users/ngchenmeng/test/my-app
npm test
```

### ESP32 Firmware Check
```bash
cd /Users/ngchenmeng/test
bash scripts/check-esp32.sh
```

### Type Check (Frontend)
```bash
cd /Users/ngchenmeng/test/my-app
npx tsc --noEmit
```

## All-in-One Script

You can also run all tests at once:

```bash
cd /Users/ngchenmeng/test

# Backend tests
cd backend && source venv/bin/activate && pytest tests/ -v && cd ..

# Frontend tests  
cd my-app && npm test && cd ..

# ESP32 check
bash scripts/check-esp32.sh
```
