# Codebase Concerns & Unnecessary Files

During the codebase scan, several unnecessary files, caches, and misplaced artifacts were identified that should be removed or moved before final submission.

## Unnecessary Files & Directories to Delete
1. `code/.venv/` - Virtual environment directory. Must be removed to keep the repository lightweight.
2. `code/__pycache__/` - Python compilation artifacts. Should be deleted.
3. `code/image.png` - A 1.7MB image file in the `code/` directory. Appears to be an unnecessary stray artifact.
4. `.env` (in root) - Contains actual secrets. Must absolutely be deleted or excluded from the final ZIP file to prevent leaking credentials.
5. `support_tickets/output.csv` - Generated output from previous runs. Usually, results should not be packaged in the initial source ZIP.

## Misplaced Files
1. `code/.env.example` - According to the `AGENTS.md` project contract and standard conventions, this file should reside in the root directory, not inside `code/`.
