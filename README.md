# MedVault

> A smart DICOM medical image research assistant — ML-powered auto-albuming, anomaly detection, and in-browser image viewing.

[![CI](https://github.com/aasthathakkar/MedVault/actions/workflows/ci.yml/badge.svg)](https://github.com/aasthathakkar/MedVault/actions)
[![Python](https://img.shields.io/badge/python-3.14-blue)](https://python.org)
[![Flask](https://img.shields.io/badge/flask-3.0.3-green)](https://flask.palletsprojects.com)
[![License](https://img.shields.io/badge/license-MIT-orange)](LICENSE)

**[API Docs →](docs/API.md)** | **[Architecture →](docs/ARCHITECTURE.md)**

---

## What is MedVault?

Medical researchers work with thousands of DICOM files (.dcm) stored in unorganized local folders. Finding specific scans, grouping them into research collections, checking for corrupt images, and sharing them with colleagues is entirely manual — and it's slow.

MedVault automates the entire workflow:

1. **Index** — point it at any local folder, it scans every DICOM file and extracts metadata into a queryable database
2. **Auto-album** — DBSCAN clustering automatically suggests meaningful groupings ("CT · Chest · 2023-24") with confidence scores
3. **Quality check** — IsolationForest flags corrupt or low-quality images before they pollute your research dataset
4. **View** — click any file to view it in the browser via Cornerstone.js (no downloads needed)
5. **Share** — generate password-protected links with optional expiry; every access is logged with IP, device, and timestamp

---

## Features

### Core pipeline
- Recursive DICOM folder indexer — handles corrupt files gracefully (logged, never crashes)
- Filter-based album creation — by modality, PatientID, date range, body part
- Optional Niffler CSV import for hospital PACS workflow compatibility
- Zip export with auto-generated `summary.json`

### ML features
- **Auto-albuming** — DBSCAN on metadata feature vectors; no cluster count needed; noise handled natively
- **Quality detection** — IsolationForest on pixel statistics (mean intensity, std dev, zero-pixel ratio, Shannon entropy); model persisted with joblib

### Security
- UUID v4 shareable tokens (122 bits — unguessable)
- Optional password protection (PBKDF2+SHA256 via Werkzeug — never plaintext)
- Optional link expiry enforced server-side
- Full audit trail — every link access logs IP, device, timestamp, and password success/fail
- Canvas watermark on Cornerstone.js viewer — every screenshot is traceable

### Developer quality
- 60+ pytest cases
- GitHub Actions CI — tests run on every push
- Consistent API response envelope: `{"success": true/false, "data": ..., "error": ...}`
- Docker support
- SQLite for dev, PostgreSQL-ready for production (change `DATABASE_URL` only)

---

## Tech stack

| Layer | Technologies |
|---|---|
| Backend | Python 3.14, Flask 3.0.3, SQLAlchemy 2.0.30, SQLite / PostgreSQL |
| DICOM | pydicom |
| ML | scikit-learn (DBSCAN, IsolationForest), numpy, scipy, pandas, joblib |
| Frontend | React 18, Tailwind CSS, Cornerstone.js, React Router, Axios |
| Infra | Docker, GitHub Actions, Render / Railway |

---

## Quick start

### Prerequisites
- Python 3.11+
- Node.js 18+
- pip

### 1. Clone and set up backend

```bash
git clone https://github.com/aasthathakkar/MedVault.git
cd MedVault
python3 -m venv med_vault
source med_vault/bin/activate
pip install -r backend/requirements.txt
```

### 2. Configure environment

```bash
cp backend/.env.example backend/.env
# Edit backend/.env and set SECRET_KEY
```

### 3. Run the demo seed (loads sample DICOM data)

```bash
python backend/scripts/seed_demo.py
```

### 4. Start the backend

```bash
cd backend
flask run
# API running at http://localhost:5000
```

### 5. Start the frontend

```bash
cd frontend
npm install
npm run dev
# UI running at http://localhost:5173
```
---

## Running tests

```bash
cd backend
pytest tests/ -v
```

---

## Project structure

```
MedVault/
├── backend/
│   ├── app/
│   │   ├── api/            ← Flask route blueprints
│   │   ├── models/         ← SQLAlchemy models (7 tables)
│   │   ├── services/       ← business logic
│   │   ├── ml/             ← DBSCAN + IsolationForest
│   │   └── utils/          ← helpers
│   ├── tests/
│   ├── scripts/
│   │   └── seed_demo.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   └── src/
│       ├── pages/          ← Dashboard, Albums, Viewer, Suggestions
│       └── components/
├── docs/
│   ├── API.md
│   └── ARCHITECTURE.md
└── sample_data/            ← gitignored
```

---

## Enterprise roadmap

MedVault currently operates in personal/local mode — no login required. For institutional adoption, the following enterprise features are designed and documented:

- Institute email domain restriction (`@hospital.org` only)
- Role-based access control (Researcher vs Viewer)
- Admin dashboard — manage users, revoke tokens, export audit logs
- Domain-restricted sharing — links tied to verified user emails

---

## Honest limitations

- **Not HIPAA compliant** — built for research use with public DICOM datasets
- **Single user** — no authentication for the main app; security is at the sharing layer
- **IsolationForest tuning** — contamination parameter may need adjustment per dataset/modality

---
