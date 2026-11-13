# ID Card Studio

Local-first ID card production for one Windows owner/operator, using a Next.js browser interface, FastAPI/SQLite, and a separate interactive-session Windows hardware agent.

**Status: implementation awaiting dependency-based and Windows hardware validation. This is not yet a certified production release.** Source files, business rules, capture workflow, Windows adapters, installer, tests and operating instructions are included. Development took place in Linux with dependency downloads blocked by DNS. See [verification results](docs/VERIFICATION.md) for precisely what ran and what did not.

## Repository

```text
id-card-studio/
  frontend/                  Next.js, React, TypeScript, Tailwind, shadcn button
    app/                     Dashboard and application shell
    components/              Projects, registration, photo crop, records, templates,
                             production, settings
    lib/                     API client, types, style utilities
  backend/
    app/                     FastAPI API, SQLAlchemy models, rules, PDF imposition,
                             backup/restore/cleanup
    migrations/versions/     Alembic version 0001
    requirements.txt
  windows-agent/
    camera/                  PnP detection, stable-file watcher, capability interfaces
    coreldraw/               Registered v21 COM adapter
    diagnostics/             Device and optional real COM diagnostic
    jobs/                    Serialized card worker with result checkpoints
    agent.py                 Authenticated polling, heartbeat, supervised worker
  shared/                    Capture-state contract
  scripts/                   Installer, launcher, shutdown, diagnostics, maintenance
  tests/                     Domain, API, storage, jobs, printing, opt-in hardware tests
  docs/                      Windows hardware procedure and verification status
  examples/                  Institution fields, mappings, import CSV
  install.ps1, start.ps1, stop.ps1, diagnose.ps1, backup.ps1
  Start ID Card Studio.bat
  Stop ID Card Studio.bat
```

## Windows installation

Copy this entire repository to a writable folder on the Windows PC, for example `C:\IDCardStudio`. Do not copy the development `.venv`; the installer creates a Windows environment.

Prerequisites: 64-bit Python **3.12** with the `py` launcher, Node.js **22 or newer**, and internet for initial open-source dependency installation. Install/activate CorelDRAW 2019 and any compatible Nikon tethering software yourself. No Docker, WSL, Redis, server or account system is needed.

In PowerShell:

```powershell
Set-Location 'C:\IDCardStudio'
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1
```

The installer checks Windows/Python/Node, creates private local storage, installs dependencies, applies Alembic migrations, type-checks/builds the frontend, runs software tests, performs noninteractive hardware discovery and creates a desktop shortcut. It stops on errors; inspect the error instead of bypassing failed tests. `npm install` creates the frontend lockfile on first successful installation; subsequent installations use `npm ci`. This repository does not contain a fabricated dependency lockfile from an unperformed install.

Optional custom storage location (set before installation and retain for future launches):

```powershell
[Environment]::SetEnvironmentVariable('IDCS_DATA_DIR', 'D:\Private\IDCardStudio', 'User')
$env:IDCS_DATA_DIR = 'D:\Private\IDCardStudio'
```

`.env.example` is documentation; scripts read environment variables, not a dotenv file.

## Start and stop

Double-click **Start ID Card Studio.bat** or the desktop shortcut. Alternatively:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\start.ps1
```

The hidden supervisor starts FastAPI and the hardware agent in your interactive Windows session, waits for API readiness and opens the default browser. Next.js is compiled to static assets and served by FastAPI at `http://127.0.0.1:8765`; Node is not required as a daily background server. There are no remote scripts/fonts or CDN dependencies in the interface.

Use **Stop ID Card Studio.bat** for shutdown, or:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\stop.ps1
```

Closing a browser tab does not stop the application. Shutdown lets the active card worker finish or time out before stopping processes. CorelDRAW itself is not quit. Do not launch a second backend manually against the same database.

## Daily workflow

1. **Schools & colleges:** create an institution, set academic year, and configure required/optional/dropdown fields. Field order is editable. Enable “Keep for next” only for repeated selections such as class/division.
2. **Templates:** register your existing CDR, dimensions and mappings. Inspect it. Follow the [CorelDRAW preparation procedure](docs/HARDWARE.md#prepare-an-existing-design).
3. **Registration:** enter details. Capture Photo arms a session; use compatible Nikon software/body shutter, then choose the received image. Alternatively Import Photo. Accept, retake or adjust crop/rotation/zoom. Save Student or Save & Next.
4. **Imported classes:** import CSV/XLSX in Student Records. Headers must match field keys shown in the UI. Import validates the entire file before inserting any records. Click Photograph next student to move through pending photographs.
5. **Production:** select saved students and a template in Student Records, then Generate Cards. Inspect CDR/PDF links and any per-student errors. Generation uses immutable job snapshots and approved photos, with checksum validation.
6. **Print sheets:** on a completed or partial job, choose Arrange print sheets. Use 210 × 297 mm for A4 or enter custom dimensions, margins, gap and bleed. Front/back requires two-page card PDFs and a duplex flip choice. Click Create print PDF. Layout preserves source PDF content without browser screenshots or automatic rescaling.
7. Print a measured test at Actual size / 100%, then the batch. Mark each generated student Printed to track the count. Download ZIP contains successful outputs and generated sheets.

See [exact Nikon/CorelDRAW hardware tests](docs/HARDWARE.md). PDF previews use the browser's PDF viewer. Dedicated high-resolution raster card previews are not currently generated.

## Storage and security

Default: `%LOCALAPPDATA%\IDCardStudio\` with `database`, `projects`, `originals`, `approved`, `templates`, `generated`, `tmp`, `logs`, `backups`, and `inbox` folders. The installer removes inherited permissions and grants the current Windows user and SYSTEM access. Database mode is SQLite WAL with foreign-key enforcement and serialized transactions.

The application binds only to loopback, checks Host/Origin and Fetch Metadata, uses an HTTP-only SameSite owner cookie plus a custom-header CSRF check, and uses a separate agent bearer token. Launch tokens are passed in a browser URL fragment and cleared from browser history. Optional owner password is scrypt-hashed in the database. This is local authentication, not a multi-user identity system. TLS is not configured for loopback. Protect the Windows account and storage; files are not application-level encrypted.

## Backup, restore and retention

Stop the application before maintenance. Backups include a SQLite backup-API snapshot plus projects, originals, approved photos, templates and generated artifacts, with a SHA-256 manifest. Authentication tokens are intentionally not exported.

```powershell
.\stop.ps1
.\backup.ps1
# A private backup ZIP path is printed.
.\scripts\restore.ps1 -Archive 'C:\Users\YOU\AppData\Local\IDCardStudio\backups\backup-YYYYMMDD-HHMMSS.zip'
.\scripts\cleanup.ps1
.\start.ps1
```

Restore checks archive paths, checksums and database integrity before replacement, retains the previous folders in a sibling rollback directory, and marks running jobs interrupted. Keep that rollback directory protected. Restore is rejected while `runtime.lock` exists. After an abnormal PC/process crash, confirm no supervisor/backend/agent/worker is running before removing a stale runtime lock; never remove a live lock to force maintenance.

Retention currently removes **unreferenced** originals/approved assets and old inbox/temp files after the configured interval. It does not automatically delete student records, approved photographs referenced by records/jobs, or production history. Rejected capture rows and their referenced originals are retained for audit; deleting a student makes those capture files eligible for cleanup unless a production snapshot still references them.

## Development checks

After installing dependencies:

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
Push-Location frontend
npm run typecheck
npm run build
Pop-Location
```

Optional real CorelDRAW test, with application stopped:

```powershell
.\diagnose.ps1 -CorelTest
$env:IDCS_HARDWARE_TEST = '1'
.\.venv\Scripts\python.exe -m pytest tests\test_hardware_optional.py -v
Remove-Item Env:IDCS_HARDWARE_TEST
```

Pure standard-library tests can also run without third-party dependencies:

```text
python -m unittest discover -s tests -p test_domain.py -v
python -m unittest discover -s tests -p "test_*stdlib.py" -v
```

## Known unfinished/validation-dependent areas

- Direct Nikon SDK shutter/live view: intentionally unavailable until a supported model/SDK is supplied and integrated.
- Full dependency installation, FastAPI integration suite, Next production build, browser UX test and PowerShell execution: not run in the restricted development environment.
- CorelDRAW hardware operation: real code, not physically verified. Additional type-library members, formatting fidelity, empty PowerClip frames, installed fonts/effects and PDF presets require the documented acceptance run.
- Separate front/back template uploads, raster card previews, automated comprehensive font/effect preflight and a system-tray UI are not implemented. A hidden supervised process and two-page CDR templates are used.
- Backups/restores are offline PowerShell operations. The Settings screen explains them; it does not perform live restores.
- No physical printer, bleed/color-standard certification or duplex registration test has been performed.

Do not use unvalidated output for a client production batch. Complete the documented first-card test and measured print proof on the target Windows workstation.
