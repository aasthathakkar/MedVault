# MedVault — API Reference

Base URL: `http://localhost:5000` (dev) | `https://api.medvault.app` (prod)

All responses follow this envelope:
```json
{ "success": true, "data": { ... }, "error": null }
{ "success": false, "data": null, "error": "message" }
```

---

## Health

### GET /api/health
Returns API status. Used by deployment platform for uptime monitoring.

**Response:**
```json
{ "success": true, "data": { "status": "ok", "version": "1.0.0" }, "error": null }
```

---

## Indexing

### POST /api/index
Recursively scans a local folder and indexes all DICOM files into the database.

**Request body:**
```json
{ "path": "/Users/researcher/datasets/lung-study" }
```

**Response:**
```json
{
  "success": true,
  "data": {
    "indexed": 1842,
    "skipped_duplicates": 12,
    "errors": 3,
    "scan_id": "uuid-of-this-scan"
  },
  "error": null
}
```

**Notes:**
- Corrupt or unreadable files are logged to `ScanError` — scan never stops
- Duplicate files (same `SOPInstanceUID`) are skipped, not re-indexed
- `errors` count reflects files logged to `ScanError`

---

### POST /api/import-niffler
Imports DICOM metadata from a Niffler CSV export file (secondary workflow for hospital PACS users).

**Request body:**
```json
{ "csv_path": "/Users/researcher/niffler_export.csv" }
```

**Response:** same shape as `POST /api/index`

---

## Albums

### POST /api/albums
Create a new album with optional filter criteria. Files matching ALL provided filters are added.

**Request body:**
```json
{
  "name": "Lung Study Phase 1",
  "description": "CT scans, chest, 2023",
  "filters": {
    "modality": "CT",
    "body_part": "CHEST",
    "date_from": "2023-01-01",
    "date_to": "2023-12-31",
    "patient_id": "PAT_001"
  }
}
```
All filter fields are optional. Omitting `filters` creates an empty album.

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 3,
    "name": "Lung Study Phase 1",
    "description": "CT scans, chest, 2023",
    "file_count": 847,
    "created_at": "2026-07-18T10:32:00Z"
  },
  "error": null
}
```

---

### GET /api/albums
List all albums.

**Response:**
```json
{
  "success": true,
  "data": [
    { "id": 1, "name": "...", "file_count": 200, "created_at": "..." },
    { "id": 2, "name": "...", "file_count": 45, "created_at": "..." }
  ],
  "error": null
}
```

---

### GET /api/albums/:id
Get details of one album.

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 3,
    "name": "Lung Study Phase 1",
    "description": "CT scans, chest, 2023",
    "file_count": 847,
    "anomaly_count": 12,
    "created_at": "2026-07-18T10:32:00Z",
    "updated_at": "2026-07-18T10:32:00Z"
  },
  "error": null
}
```

---

### PATCH /api/albums/:id
Update album name or description.

**Request body:**
```json
{ "name": "Lung Study Phase 1 — Revised", "description": "Updated" }
```

---

### DELETE /api/albums/:id
Delete an album. Does NOT delete the underlying DICOM files.

---

## Files

### GET /api/albums/:id/files
List all files in an album with quality flags.

**Query params:** `?page=1&per_page=50&anomaly_only=true`

**Response:**
```json
{
  "success": true,
  "data": {
    "files": [
      {
        "id": 12,
        "filepath": "/data/scan_001.dcm",
        "modality": "CT",
        "study_date": "2023-09-15",
        "body_part": "CHEST",
        "quality_score": -0.23,
        "is_anomaly": false
      },
      {
        "id": 47,
        "filepath": "/data/scan_047.dcm",
        "modality": "CT",
        "study_date": "2023-09-20",
        "body_part": "CHEST",
        "quality_score": 0.81,
        "is_anomaly": true
      }
    ],
    "total": 847,
    "page": 1,
    "per_page": 50
  },
  "error": null
}
```

---

### GET /api/files/:id/raw
Serves raw DICOM file bytes. Used internally by Cornerstone.js viewer in the React frontend.

**Response:** Binary DICOM data with `Content-Type: application/dicom`

---

## ML endpoints

### POST /api/albums/suggest
Runs DBSCAN clustering on all indexed metadata and returns suggested album groupings.

**Request body:** `{}` (no input needed — runs on all indexed files)

**Response:**
```json
{
  "success": true,
  "data": {
    "suggestions": [
      {
        "label": "CT · Chest · 2023–24",
        "file_count": 412,
        "confidence_score": 0.87,
        "dominant_modality": "CT",
        "dominant_body_part": "CHEST",
        "date_range": "2023-01-01 to 2024-06-30",
        "file_ids": [1, 2, 3, ...]
      },
      {
        "label": "MRI · Brain · 2022",
        "file_count": 189,
        "confidence_score": 0.91,
        "dominant_modality": "MRI",
        "dominant_body_part": "BRAIN",
        "date_range": "2022-03-10 to 2022-11-05",
        "file_ids": [201, 202, ...]
      }
    ],
    "noise_file_count": 23
  },
  "error": null
}
```

**Notes:**
- `noise_file_count` = files that didn't cluster into any group (DBSCAN label `-1`)
- `confidence_score` = intra-cluster cohesion metric (0–1, higher = tighter cluster)

---

### GET /api/albums/:id/quality-report
Returns quality scores for all files in an album.

**Response:**
```json
{
  "success": true,
  "data": {
    "album_id": 3,
    "total_files": 847,
    "anomaly_count": 12,
    "anomaly_rate": 0.014,
    "files": [
      {
        "id": 47,
        "filepath": "/data/scan_047.dcm",
        "quality_score": 0.81,
        "is_anomaly": true,
        "reason": "high zero-pixel ratio (0.73), low entropy (0.12)"
      }
    ]
  },
  "error": null
}
```

---

## Export

### GET /api/albums/:id/export
Downloads the album as a zip archive.

**Response:**
- `Content-Type: application/zip`
- `Content-Disposition: attachment; filename="album-3-lung-study.zip"`

**Zip contents:**
```
album-3-lung-study.zip
├── summary.json          ← album metadata, file list, quality stats
├── scan_001.dcm
├── scan_002.dcm
└── ...
```

**summary.json structure:**
```json
{
  "album_name": "Lung Study Phase 1",
  "exported_at": "2026-07-18T14:30:00Z",
  "file_count": 847,
  "anomaly_count": 12,
  "modalities": ["CT"],
  "body_parts": ["CHEST"],
  "date_range": "2023-01-01 to 2023-12-31",
  "files": [
    { "filename": "scan_001.dcm", "modality": "CT", "is_anomaly": false }
  ]
}
```

---

## Sharing

### POST /api/albums/:id/share
Generates a shareable URL for an album.

**Request body:**
```json
{
  "password": "research2026",
  "expires_in_days": 7
}
```
Both fields are optional. Omit `password` for a public link. Omit `expires_in_days` for a permanent link.

**Response:**
```json
{
  "success": true,
  "data": {
    "token": "a3f8c2d1-9b4e-4f2a-8c3d-1e5f9a2b7c4d",
    "url": "https://medvault.app/share/a3f8c2d1-9b4e-4f2a-8c3d-1e5f9a2b7c4d",
    "expires_at": "2026-07-25T14:30:00Z",
    "password_protected": true
  },
  "error": null
}
```

---

### GET /api/share/:token
Public endpoint. Returns the album for a valid token.

**Request body (if password-protected):**
```json
{ "password": "research2026" }
```

**Response (success):**
```json
{
  "success": true,
  "data": {
    "album_name": "Lung Study Phase 1",
    "file_count": 847,
    "shared_by": "anonymous",
    "files": [ ... ]
  },
  "error": null
}
```

**Error responses:**
- `401` — wrong password
- `404` — token not found
- `410` — link has expired

**Side effects:** Every request (success or fail) creates a `TokenAccessLog` row.

---

### GET /api/albums/:id/access-log
Returns the access history for all share tokens belonging to an album.

**Response:**
```json
{
  "success": true,
  "data": {
    "accesses": [
      {
        "accessed_at": "2026-07-20T09:14:22Z",
        "ip_address": "103.21.58.12",
        "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)...",
        "password_correct": true
      },
      {
        "accessed_at": "2026-07-20T11:02:01Z",
        "ip_address": "45.33.32.156",
        "user_agent": "python-requests/2.31.0",
        "password_correct": false
      }
    ],
    "total_accesses": 2,
    "unique_ips": 2
  },
  "error": null
}
```

---

## Errors

### GET /api/scan-errors
Lists files that failed during the last indexing scan.

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "filepath": "/data/corrupt_001.dcm",
      "error_message": "InvalidDicomError: File is not DICOM",
      "scanned_at": "2026-07-18T10:30:01Z"
    }
  ],
  "error": null
}
```

---

## HTTP status codes

| Code | Meaning |
|---|---|
| 200 | Success |
| 201 | Created |
| 400 | Bad request — missing or invalid fields |
| 404 | Resource not found |
| 405 | Method not allowed |
| 410 | Gone — link has expired |
| 429 | Too many requests — rate limited |
| 500 | Internal server error |