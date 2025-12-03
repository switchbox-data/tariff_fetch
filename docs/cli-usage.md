# CLI Usage Guide

## Running via `uvx`

If you prefer not to clone the repository or manage a local virtual environment, `uvx` can execute the CLI directly from GitHub:

```bash
# electricity
uvx --env-file=.env --from git+https://github.com/switchbox-data/tariff_fetch tariff-fetch

# gas
uvx --env-file=.env --from git+https://github.com/switchbox-data/tariff_fetch tariff-fetch-gas
```

All environment variables (API keys, credentials, etc.) still need to be exported or added to your `.env` file beforehand.

## Electricity CLI (`tariff-fetch`)

Run `uv run tariff-fetch` (or `python -m tariff_fetch.cli` / `just cli`) to launch the interactive workflow.

### Options

- `--state` / `-s`: two-letter state abbreviation (case-insensitive). If omitted, the CLI prompts you.
- `--providers` / `-p`: repeatable flag for each provider (`genability`, `openei`, `rateacuity`). Leaving it out opens a checkbox prompt so you can select multiple providers at once.
- `--output-folder` / `-o`: directory for exported JSON files. Defaults to `./outputs`.

### Workflow Overview

1. Pick a state (option or prompt).
2. Choose which providers to fetch (option or interactive checkbox).
3. Select a utility from the structured EIA list. The CLI fetches the latest CORE_EIA861 data to help you pick based on name, entity type, sales, revenue, and customer counts.
4. For each provider selected, `tariff_fetch` runs the corresponding workflow (`process_genability`, `process_openei`, or `process_rateacuity`) and writes exports to the chosen output folder. Authentication failures print guidance about the relevant environment variables.

## Gas CLI (`tariff-fetch-gas`)

Run `uv run tariff-fetch-gas` (or `python -m tariff_fetch.cli_gas` / `just cligas`).

### Options

- `--state` / `-s`: gas benchmark state (prompts if omitted).
- `--output-folder` / `-o`: output directory (defaults to `./outputs`).

### Workflow Overview

This command only targets RateAcuity’s gas workflow. After you confirm the state, the CLI launches the Selenium flow via `process_rateacuity_gas`, exporting the selected schedules. Failures typically mean the `RATEACUITY_USERNAME`/`RATEACUITY_PASSWORD` credentials or local Chrome/Chromium installation need attention.
