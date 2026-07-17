# MedVault — Security

## Security model (Mode 1 - personal use)

MedVault operates in a zero-friction personal use mode. No login is required to use the app. All security is enforced at the sharing layer.

### Shareable URLs

- Tokens are UUID v4 — 122 bits of randomness. Statistically unguessable.
- Passwords are hashed with PBKDF2+SHA256 via Werkzeug's `generate_password_hash`. Plaintext passwords are never stored.
- Link expiry is enforced server-side — clients cannot bypass it by modifying the URL.
- The public share endpoint (`GET /api/share/:token`) is rate-limited to prevent brute force.

### Audit trail

Every access attempt on a shared link — success or failure — is logged to `TokenAccessLog`:
- Timestamp
- IP address
- User-Agent (browser, OS, device)
- Whether the password was correct

This creates a legally defensible audit trail for any unauthorized data sharing.

### Viewer watermarking

The Cornerstone.js DICOM viewer applies a canvas overlay with a timestamp on every rendered image. Screenshots taken of the viewer carry this watermark — making unauthorized sharing traceable.

### Why not screenshot prevention?

Screenshot prevention is not technically possible in a web browser. Native mobile apps can use OS-level flags (`FLAG_SECURE` on Android) to black the screen during captures — websites have no access to this mechanism. Watermarking is the approach used by real medical imaging platforms for the same reason.

---

## Scope and limitations

MedVault is **not** designed for production use with real patient data:

- Not HIPAA compliant
- No encryption at rest
- Single-user — no authentication for the main application

It is designed for research use with public or de-identified DICOM datasets (e.g. TCIA collections).

---

## Reporting a vulnerability

If you find a security issue, please email [thakkaraastha06@gmail.com](mailto:thakkaraastha06@gmail.com) directly rather than opening a public GitHub issue.

---

## Enterprise security roadmap (Mode 2)

For institutional deployment, the following are designed and documented:

- Institute email domain restriction
- Role-based access control (Researcher / Viewer)
- Admin dashboard with token revocation
- Domain-restricted sharing (links tied to verified emails, no public links)
- Email verification on registration

See `docs/ARCHITECTURE.md` for the full enterprise architecture.