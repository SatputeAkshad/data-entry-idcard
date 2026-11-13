# Verification ledger

Development environment: Linux, Python 3.12 virtual environment (system Python 3.14 also available), no standalone Node/npm. The editor bundles Electron's Node runtime and a TypeScript compiler, which were used only for syntax parsing.

## Executed and passing

- 8 pure business-rule tests: dynamic-field validation, required/dropdown checks, 100 retakes, rejected/waiting approval rejection, object mapping, A4 geometry, bleed/invalid dimensions.
- 3 test-only simulated job-worker tests: per-student data/photo identity, continuing after one failure, retry skipping successes, approved-photo checksum failure. Simulated outputs are explicitly named `.simulation.json`; they are not CDR/PDF artifacts.
- 4 real standard-library backup/restore tests: SQLite snapshot and asset round trip, interrupted-job recovery, tamper rejection without replacing current data, archive traversal rejection, and live-lock refusal.
- Python source compilation for backend, Windows agent, scripts and tests.
- TypeScript/TSX syntax parsing with the editor-bundled TypeScript compiler. This does not resolve React/Next types or prove a successful production build.

## Written but not executed here

`tests/test_api.py`: real FastAPI/SQLAlchemy CRUD, optimistic revision checks, institution schema changes, import transaction validation, CSV/XLSX export, photo approval/retake, late capture rejection, next-student photo clearing, crop validation, job snapshots, idempotency/retry, cross-institution rejection, origin/host/auth boundaries.

`tests/test_storage_printing.py`: application database backup/restore, PDF dimensions/front-back contents, watched-folder transfer stability and duplicate handling.

`tests/test_hardware_optional.py`: opt-in real CorelDRAW diagnostic.

The Windows installer runs the available full software suite after installing requirements; the hardware test stays skipped unless explicitly enabled.

## Blocked environment checks

Attempted package installation using `uv pip install` failed resolving pypi.org. Offline retry confirmed FastAPI was not cached. A request to nodejs.org also failed DNS resolution. No sandbox approval bypass or external installation was attempted. Consequently, no dependency-resolved backend startup, npm install, Next build, browser screenshot, Windows script execution or real hardware acceptance result is claimed.

## Acceptance still required

Run the full numbered procedure in HARDWARE.md, record actual Nikon model/firmware and CorelDRAW build/type library, compare generated names/faces against source records, verify original CDR preservation and font/effect fidelity, then measure a physical front/back print at 100% scale. Passing tests cannot substitute for these observations.
