# Dhaka/Chattogram Academic Job Scanner

Two small, independent scanners that watch university and research-institute
career pages in Bangladesh and email you a digest whenever a page changes
*and* still matches your keywords. Built for:

- **`ra_job_scanner/`** — Research Assistant / Research Associate postings at
  Dhaka research institutes (icddr,b, BIDS, CPD, BRAC JPGSPH, BIGD) and CSE
  departments.
- **`lecturer_scanner/`** — Lecturer / Senior Lecturer postings at 30+
  universities across Dhaka and Chattogram.

Each folder is fully self-contained and runs independently. Nothing is
emailed on a run where nothing new is found.

## How it decides what's "new"

Each run fetches every URL in `sites.json`, hashes the page's visible text,
and compares it to the hash stored in `state.json` from the last run. If the
page changed **and** still contains a keyword match, that page's matching
snippets go into the digest. This is page-level diffing, not per-posting
diffing — if a page changes for any reason, you'll see all current keyword
matches on it (up to 3 snippets), which may include postings you've already
seen bundled alongside the new one. Simple, and doesn't break every time an
institute redesigns their HTML.

Known noisy sources: IUBAT and UITS's career pages list "Lecturer" as a
permanent form/dropdown option rather than a specific posting, so those two
occasionally re-trigger without an actual new opening.

## Setup

1. **Clone this repo** and install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. **Generate a Gmail App Password** (needs 2-Step Verification enabled):
   https://myaccount.google.com/apppasswords

3. **Configure each scanner you want to use.** In `ra_job_scanner/` and/or
   `lecturer_scanner/`:
   ```bash
   cp config.example.json config.json
   ```
   Then edit `config.json`:
   ```json
   {
     "gmail_address": "you@gmail.com",
     "gmail_app_password": "16-char-app-password",
     "to_email": "where-you-want-the-digest@example.com"
   }
   ```
   `config.json` is gitignored — it holds your credentials and should never
   be committed or shared.

## Usage

Once `config.json` is set up (see Setup above), run from the repo root:

### With `make` (recommended)

```bash
make setup             # installs requirements.txt + pyinstaller
make run-ra             # run the RA/Research Associate scanner once
make run-lecturer        # run the Lecturer scanner once
make dry-run-ra          # preview what would be emailed, without sending
make dry-run-lecturer
make build                # build both standalone .exe files, so you can
                           # double-click them without a Python install
make build-ra              # or build just one
make build-lecturer
make clean                  # remove PyInstaller build artifacts
```

Built exes land back in their own scanner folder, next to `sites.json`/
`config.json`, ready to double-click.

### Alternative: without `make`

No `make` on your system (e.g. plain Windows without Git Bash/WSL)? Run
`scan.py` directly from inside either scanner's folder:

```bash
python scan.py            # normal run: check sites, email digest if anything new
python scan.py --dry-run  # check sites, print what WOULD be emailed, send nothing
python scan.py --force    # ignore stored hashes, treat every keyword match as new
```

To build the exe manually instead of `make build`:

```bash
pip install pyinstaller
python -m PyInstaller --onefile --console --name "Scanner" --clean scan.py
```

The first run against a fresh `state.json` emails you a baseline of
everything currently matching — later runs only email about genuine changes.

### Automating it

Point Windows Task Scheduler (or `cron`/`systemd` on Linux) at
`python scan.py` (or the built exe) on whatever interval you like — the
script is idempotent and safe to run as often as you want.

## Customizing

Edit `sites.json` in either folder — it's a plain list of `{name, url}`
plus a `keywords` array. Add, remove, or retarget it for other
positions/cities/institutions; the scanning logic doesn't care what you put
in it.
