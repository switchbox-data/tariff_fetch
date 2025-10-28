# Tariff Fetch

The project provides a CLI tool that retrieves electric and gas utility tariff data from multiple providers.

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
python -m tariff-fetch.cli [OPTIONS]
python -m tariff-fetch.cli_gas [OPTIONS]
```

With uv:

```bash
uv run tariff-fetch [OPTIONS]
uv run tariff-fetch-gas [OPTIONS]
```

With Just:

```bash
just cli
just cligas
```

Options:
- `--state` / `-s`: two-letter state abbreviation (default: prompt)
- `--providers` / `-p`: repeat per provider (`genability`, `openei`, `rateacuity`)
- `--output-folder` / `-o`: directory for exports (default: `./outputs`)

Omitted options will trigger interactive prompts.

### Gas benchmark CLI

RateAcuity natural gas benchmarks use a separate entry point:

```bash
uv run python -m tariff_fetch.cli_gas [OPTIONS]
```

`just cligas` runs the same command.

Options:
- `--state` / `-s`: two-letter state abbreviation (default: prompt)
- `--output-folder` / `-o`: directory for exports (default: `./outputs`)

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
- **RateAcuity (electric)**: Selenium session that logs in, picks a state, utility, and schedules. Stores the scraped sections as
  JSON. A failure produces `selenium_error.png` for inspection.
- **RateAcuity (gas)**: Uses the gas benchmark workflow and exports the selected schedules in the same JSON format. Credentials are identical to the electric flow.
