# Tariff Fetch

The project provides a CLI tool that retrieves electric utility tariff data from multiple providers.

## Requirements
- Python 3.11+
- Credentials for the providers you intend to call:
  - `ARCADIA_APP_ID` and `ARCADIA_APP_KEY`
  - `OPENEI_API_KEY`
  - `RATEACUITY_USERNAME` and `RATEACUITY_PASSWORD`
- Google Chrome or Chromium installed locally (for RateAcuity)

## Installation

```bash
uv sync
source .venv/bin/activate
```

Alternative using plain `pip`:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Configuration

Populate a `.env` file (or export the variables manually). Only set the values you need.

```
ARCADIA_APP_ID=...
ARCADIA_APP_KEY=...
OPENEI_API_KEY=...
RATEACUITY_USERNAME=...
RATEACUITY_PASSWORD=...
```

## Running the CLI

```bash
uv run python -m tariff_fetch.cli [OPTIONS]
```

`just cli` runs the same command if you use the supplied Justfile.

Options:
- `--state` / `-s`: two-letter state abbreviation (default: prompt)
- `--providers` / `-p`: repeat per provider (`genability`, `openei`, `rateacuity`)
- `--output-folder` / `-o`: directory for exports (default: `./outputs`)

Omitted options will trigger interactive prompts.

### Examples

```bash
# Fully interactive run
uv run python -m tariff_fetch.cli

# Scripted run for Genability and OpenEI
uv run python -m tariff_fetch.cli \
  --state ca \
  --providers genability \
  --providers openei \
  --output-folder data/exports
```

The CLI suggests filenames like `outputs/openei_Utility_sector_detail-0_2024-03-18.json` before writing each file so you
can accept or override them.

## Provider notes
- **Genability**: choose customer classes and tariff types before selecting tariffs. Requires Arcadia credentials.
- **OpenEI**: pick the sector and detail level, then select the returned tariffs. Requires `OPENEI_API_KEY`.
- **RateAcuity**: Selenium session that logs in, picks a state, utility, and schedules. Stores the scraped sections as
  JSON. A failure produces `selenium_error.png` for inspection.
