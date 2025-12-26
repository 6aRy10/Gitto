# Gitto — Cash Collections Forecast Command Center

This is a B2B finance product for FP&A and CFOs that turns invoice/payment history into a behavior-based cash collections forecast.

## Quick Start (PowerShell)

To start both the backend and frontend simultaneously:

1. Open PowerShell in the root directory.
2. Run:
   ```powershell
   ./run.ps1
   ```

## Manual Setup

### Backend (FastAPI)
1. `cd backend`
2. `pip install -r requirements.txt`
3. `uvicorn main:app --reload --port 8000`

### Frontend (Next.js)
1. `cd frontend`
2. `npm install`
3. `npm run dev` (Runs on `http://localhost:3000`)

## Core Features
- **13-Week Forecast**: Behavioral modeling with P25/P50/P75 confidence bands.
- **Weekly Meeting Mode**: Waterfall comparison between forecast snapshots.
- **Scenario Modeling**: Global and customer-specific delay shocks.
- **AR Prioritization**: Ranked list of invoices to chase for immediate cash impact.
- **Snowflake Connector**: Enterprise-grade data ingestion mapping.

