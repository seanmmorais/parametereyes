# Parametereyes (Automi-style folder layout)

This version matches the folder layout you showed:

```
Parametereyes/
  backend/
    server.py
    workflow_runner.py
    requirements.txt
    _logs/
  frontend/
    main.js
    preload.js
    package.json
    renderer/
      index.html
      renderer.js
      styles.css
```

## What runs where?
- `frontend/main.js` = Electron **main process** (desktop shell)
- `frontend/preload.js` = safe bridge to the renderer
- `frontend/renderer/*` = the UI (dashboard with Home, Edit GXB, Tab 3..6)
- `backend/server.py` = Python FastAPI backend (`/health`, `/gxb/inspect`)

## Prereqs
- Node.js 18+
- Python 3.10+

## Setup

### 1) Frontend deps
```bash
cd frontend
npm install
```

### 2) Backend venv + deps
From the repo root:

**Windows (PowerShell)**
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
```

**macOS/Linux**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

## Run (dev)
From `frontend/`:
```bash
npm run dev
```

This starts:
- backend: `http://127.0.0.1:5123`
- electron window

## Notes
- In production, Electron will spawn the backend automatically unless `PARAMEYES_NO_BACKEND=1`.
- If your python executable isn’t `python`, set `PARAMEYES_PYTHON` (e.g. `py` on Windows):
  - Windows (PowerShell): `$env:PARAMEYES_PYTHON="py"`
  - macOS/Linux: `export PARAMEYES_PYTHON=python3`
