# MedVault — Architecture

## System overview

MedVault is a full-stack local research assistant for DICOM medical image datasets. It runs locally or on a private server — no external hospital infrastructure required.

```
┌─────────────────────────────────────────────────────────────────┐
│                        React Frontend                           │
│   Dashboard | Albums | ML Suggestions | Viewer | Access Logs    │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP (Axios)
┌────────────────────────────▼────────────────────────────────────┐
│                      Flask REST API                             │
│                  17 endpoints, blueprints                       │
│        consistent: {"success", "data", "error"}                │
└──┬──────────────┬───────────────┬──────────────┬───────────────┘
   │              │               │              │
   ▼              ▼               ▼              ▼
Indexer      Album mgr        ML layer       Sharing
(pydicom)   (SQLAlchemy)   (sklearn)       (UUID+hash)
   │              │               │              │
   └──────────────┴───────────────┴──────────────┘
                             │
                    ┌────────▼────────┐
                    │  SQLite (dev)   │
                    │  PostgreSQL     │
                    │  (prod via URL) │
                    └─────────────────┘
```

---

## Layer breakdown

### 1. DICOM indexer (`backend/app/services/indexer.py`)

Recursively walks a folder tree and processes every `.dcm` file.

**Key decisions:**
- Uses `pydicom`'s `dcmread(..., stop_before_pixels=True)` to read metadata only — pixel arrays are NOT loaded during indexing. This keeps memory constant even for 100GB+ datasets.
- `SOPInstanceUID` is stored as a UNIQUE constraint — re-indexing the same folder is safe, no duplicates.
- Any exception per file (corrupt binary, wrong format, missing required tags) is caught, written to `ScanError`, and the scan continues. The indexer never crashes on bad data.

**Metadata extracted per file:**

| Field | DICOM tag | Example |
|---|---|---|
| patient_id | (0010,0020) | PAT_001 |
| modality | (0008,0060) | CT |
| study_date | (0008,0020) | 2023-09-15 |
| body_part | (0018,0015) | CHEST |
| sop_instance_uid | (0008,0018) | 1.2.840.10008.5... |

---

### 2. Album manager (`backend/app/services/album_manager.py`)

Creates named collections of DICOM files based on filter criteria.

**Many-to-many design:** Files are never copied or moved on disk. The `AlbumFile` association table stores only `(album_id, file_id)` pairs. A 50GB dataset with 20 albums adds essentially zero disk overhead.

**Cascade rule:** Deleting an Album cascades to its `AlbumFile` rows but never touches `DICOMFile` rows — source files are always preserved.

---

### 3. ML layer (`backend/app/ml/`)

#### 3a. Auto-albuming — DBSCAN (`clustering.py`)

**Input:** Metadata from all indexed `DICOMFile` rows
**Output:** Suggested album groupings with confidence scores and labels

```
raw metadata
     │
     ▼
pandas DataFrame
     │
     ▼
Label encode (Modality, BodyPart) + timestamp (StudyDate) + hash (PatientID)
     │
     ▼
StandardScaler → normalized feature matrix
     │
     ▼
DBSCAN(eps=0.5, min_samples=3)
     │
     ▼
cluster labels  (-1 = noise, 0,1,2,... = clusters)
     │
     ▼
human-readable label per cluster (dominant Modality · BodyPart · date range)
     │
     ▼
POST /api/albums/suggest → [{label, file_ids, confidence_score}]
```

**Why DBSCAN over KMeans:**
- KMeans requires number of clusters upfront → unknown for arbitrary DICOM datasets
- DBSCAN discovers density-based clusters of any shape and size
- Noise points (files that don't fit any cluster) are marked `-1` and excluded from suggestions

#### 3b. Quality detection — IsolationForest (`quality.py`)

**Input:** Pixel arrays from `DICOMFile` rows
**Output:** `quality_score` (float) and `is_anomaly` (bool) stored per file

```
pixel array (ds.pixel_array via pydicom)
     │
     ▼
pixel statistics (numpy + scipy)
  - mean intensity
  - standard deviation
  - zero-pixel ratio (black pixel %)
  - Shannon entropy (information content)
     │
     ▼
StandardScaler → normalized stats matrix
     │
     ▼
IsolationForest(contamination=0.05)
     │
     ▼
decision_function() → anomaly score per file
     │
     ▼
stored: DICOMFile.quality_score, DICOMFile.is_anomaly
model persisted: app/ml/models/quality_model.pkl (joblib)
```

**Why IsolationForest:**
- No labeled "bad image" dataset exists — supervised learning not possible
- Isolates anomalies by fitting random decision trees — outliers are isolated in fewer splits
- `contamination` parameter = expected proportion of anomalies (default 0.05 = 5%)
- Model saved with joblib — loaded on startup, not retrained on every request

---

### 4. Flask REST API (`backend/app/api/`)

**App factory pattern:** `create_app(config)` in `backend/app/__init__.py` — allows multiple instances for testing without state pollution.

**Blueprints:**
- `index_bp` — indexing and import
- `albums_bp` — album CRUD and ML endpoints
- `files_bp` — file serving
- `sharing_bp` — token generation and public access
- `health_bp` — health check

**Response envelope (every endpoint):**
```json
{
  "success": true,
  "data": { ... },
  "error": null
}
```
or on error:
```json
{
  "success": false,
  "data": null,
  "error": "Descriptive error message"
}
```

**Global error handlers:** 400, 404, 405, 500 — all return the envelope format. No unformatted errors ever reach the client.

---

### 5. Sharing + security (`backend/app/services/sharing.py`)

**Token generation:**
```python
import uuid
token = str(uuid.uuid4())  # 32 hex chars, 122 bits of randomness
```

**Password hashing:**
```python
from werkzeug.security import generate_password_hash, check_password_hash
hash = generate_password_hash(password)  # PBKDF2+SHA256, salted
check_password_hash(hash, candidate)     # constant-time comparison
```

**Expiry check (server-side):**
```python
from datetime import datetime, timezone
if token.expires_at and datetime.now(timezone.utc) > token.expires_at:
    return {"success": False, "error": "Link has expired"}, 410
```

**Access logging:**
Every request to `GET /api/share/:token` (success or fail) creates a `TokenAccessLog` row:
```
ip_address      from request.remote_addr
user_agent      from request.user_agent.string
accessed_at     datetime.now(timezone.utc)
password_correct true/false
```

**Canvas watermark:** When Cornerstone.js renders a DICOM image in the browser, a React hook draws a canvas overlay with the current timestamp. Every screenshot taken of the viewer carries this watermark — making unauthorized sharing traceable.

---

### 6. Database (`backend/app/models/`)

**7 tables:**

| Table | Purpose |
|---|---|
| `DICOMFile` | One row per indexed .dcm file |
| `Album` | Named collection |
| `AlbumFile` | Many-to-many: files ↔ albums |
| `ShareToken` | UUID token for a shared album |
| `TokenAccessLog` | Every access attempt on a shared link |
| `ScanError` | Files that failed during indexing |
| `AppSettings` | Key-value config for future enterprise mode |

**SQLite → PostgreSQL migration:** Change `DATABASE_URL` in `.env` from `sqlite:///medvault.db` to `postgresql://user:pass@host/db`. SQLAlchemy handles the rest — no code changes.

---

### 7. Frontend (`frontend/src/`)

**Pages:**
- `Dashboard` — paste folder path, index, see stats
- `Albums` — list, search, create
- `AlbumDetail` — files with quality flags, export, share, viewer
- `MLSuggestions` — DBSCAN results, accept/reject/rename
- `ShareView` — public page for shared links (password prompt if set)

**Cornerstone.js viewer:**
- Loaded as a React component in `AlbumDetail`
- Fetches raw DICOM bytes from `GET /api/files/:id/raw`
- Renders with windowing, zoom, pan controls built in
- Canvas watermark hook draws timestamp overlay on every render

**Axios base config:**
```js
// src/utils/api.js
import axios from 'axios';
const api = axios.create({ baseURL: import.meta.env.VITE_API_URL || 'http://localhost:5000' });
export default api;
```

---

## Deployment architecture

```
GitHub push
     │
     ▼
GitHub Actions CI (pytest)
     │ pass
     ▼
Render / Railway
  ├── Backend service (Docker → Flask)
  │     DATABASE_URL=postgresql://...
  │     SECRET_KEY=...
  └── Frontend service (Vite build → static)
        VITE_API_URL=https://api.medvault.app
```

---

## Security model (Mode 1 — personal use)

MedVault uses a zero-friction security model. No login required for the main app. All security is enforced at the sharing layer.

**Threat model:**
- Unauthorized link access → blocked by password + expiry
- Brute force on tokens → statistically impossible (122-bit UUID)
- Brute force on passwords → rate-limited endpoint
- Unauthorized screenshot sharing → canvas watermark makes it traceable
- Compromised DB → passwords are hashed (PBKDF2), tokens are random UUIDs

**Not in scope (Mode 1):**
- HIPAA compliance
- Multi-user authentication
- Encryption at rest

See `docs/ENTERPRISE.md` for Mode 2 enterprise architecture roadmap.

---

## Tech choices rationale

| Choice | Alternatives considered | Reason chosen |
|---|---|---|
| DBSCAN | KMeans, Agglomerative | No cluster count needed; handles noise |
| IsolationForest | LOF, One-class SVM | Fast, no labels needed, joblib-persistable |
| SQLite (dev) | PostgreSQL from start | Zero setup; swap via env var for prod |
| Cornerstone.js | OHIF Viewer | OHIF needs a DICOMweb proxy (weeks of work); Cornerstone.js is the same engine, embedded directly |
| Flask | FastAPI, Django | Lightweight, matches Aastha's existing experience, clean blueprints |
| UUID v4 tokens | JWT, HMAC tokens | Simpler, no secret key dependency, 122-bit randomness is sufficient |