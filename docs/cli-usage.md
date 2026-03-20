# CLI Usage Guide

## Running via `uvx`

If you prefer not to clone the repository or manage a local virtual environment, `uvx` can execute the CLI directly from GitHub:

```bash
# electricity
uvx --env-file=.env --from git+https://github.com/switchbox-data/tariff_fetch tariff-fetch

# gas
uvx --env-file=.env --from git+https://github.com/switchbox-data/tariff_fetch tariff-fetch gas

# arcadia to urdb
uvx --env-file=.env --from git+https://github.com/switchbox-data/tariff_fetch tariff-fetch urdb ni 522 2025
```

All environment variables (API keys, credentials, etc.) still need to be exported or added to your `.env` file beforehand.

## Electricity CLI (`tariff-fetch`)

Run `uv run tariff-fetch` (or `python -m tariff_fetch.cli` / `just cli`) to launch the interactive workflow.

### Options

- `--state` / `-s`: two-letter state abbreviation (case-insensitive). If omitted, the CLI prompts you.
- `--provider` / `-p`: provider to fetch (`genability`, `openei`, `rateacuity`). If omitted, the CLI prompts you.
- `--output-folder` / `-o`: directory for exported JSON files. Defaults to `./outputs`.
- `--effective-date`: provider query date in `YYYY-MM-DD` format.
- `--log-dir`: directory for log files.
- `--log-file`: exact file path for the log file.

### Workflow Overview

1. Pick a state (option or prompt).
2. Choose which provider to fetch (option or prompt).
3. Select a utility from the structured EIA list. The CLI fetches the latest CORE_EIA861 data to help you pick based on name, entity type, sales, revenue, and customer counts.
4. `tariff_fetch` runs the selected workflow (`process_genability`, `process_openei`, or `process_rateacuity`) and writes exports to the chosen output folder. Authentication failures print guidance about the relevant environment variables.

The utility picker caches the CORE_EIA861 parquet for 1 hour in the platform-specific user cache directory, so repeated runs usually reuse the local copy instead of downloading it again.

Example:

```bash
uv run tariff-fetch --state ca --provider genability --effective-date 2025-06-01
```

## URDB CLI (`tariff-fetch urdb`)

Run `uv run tariff-fetch urdb` for the interactive Genability-to-URDB flow.

### Options

- `--state` / `-s`: two-letter state abbreviation (case-insensitive). If omitted, the CLI prompts you.
- `--output-folder` / `-o`: directory for exported files. Defaults to `./outputs`.
- `--year` / `-y`: year to convert. If omitted, the CLI prompts you.
- `--log-dir`: directory for log files.
- `--log-file`: exact file path for the log file.
- `--fail-fast`: stop immediately on conversion errors instead of prompting to continue.

### Subcommands

- `ni`: convert one Arcadia master tariff directly to URDB JSON.

Example:

```bash
uv run tariff-fetch urdb ni 522 2025 --output ./outputs/arcadia_urdb_522_2025.json
```

## Cache CLI (`tariff-fetch cache`)

Use this command to clear the cached utility parquet used by the interactive utility picker.

### Subcommands

- `clear`: remove the cached CORE_EIA861 parquet file.

Example:

```bash
uv run tariff-fetch cache clear
```

## Gas CLI (`tariff-fetch gas`)

Run `uv run tariff-fetch gas` (or `python -m tariff_fetch.cli gas` / `just cli`).

### Options

- `--state` / `-s`: gas benchmark state (prompts if omitted).
- `--output-folder` / `-o`: output directory (defaults to `./outputs`).

### Subcommands

- `urdb`: convert gas tariffs to URDB format.

Examples:

```bash
uv run tariff-fetch gas --state tx --output-folder outputs
uv run tariff-fetch gas urdb --state tx --year 2025 --output-folder outputs
```

### Workflow Overview

This command only targets RateAcuity’s gas workflow. After you confirm the state, the CLI launches the Selenium flow via `process_rateacuity_gas`, exporting the selected schedules. Failures typically mean the `RATEACUITY_USERNAME`/`RATEACUITY_PASSWORD` credentials or local Chrome/Chromium installation need attention.

`tariff-fetch gas urdb` runs the RateAcuity gas-to-URDB flow and may prompt for a year if `--year` is omitted.
