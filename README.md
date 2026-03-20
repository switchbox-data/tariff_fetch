# Tariff Fetch

[![PyPI version](https://img.shields.io/pypi/v/tariff_fetch)](https://pypi.org/project/tariff_fetch/)
[![Build status](https://img.shields.io/github/actions/workflow/status/switchbox-data/tariff_fetch/python-package-main.yml?branch=main)](https://github.com/switchbox-data/tariff_fetch/actions/workflows/python-package-main.yml?query=branch%3Amain)
[![Commit activity](https://img.shields.io/github/commit-activity/m/switchbox-data/tariff_fetch)](https://img.shields.io/github/commit-activity/m/switchbox-data/tariff_fetch)
[![License](https://img.shields.io/github/license/switchbox-data/tariff_fetch)](https://img.shields.io/github/license/switchbox-data/tariff_fetch)

A CLI tool, and python library, to simplify downloading electric and gas utility tariff data from multiple providers in a consistent data format.

- **Github repository**: <https://github.com/switchbox-data/tariff_fetch/>
- **Documentation**: <https://switchbox-data.github.io/tariff_fetch/>
- **PyPI page**: <https://pypi.org/project/tariff_fetch/>

## Requirements

- Python 3.11+
- Credentials for the providers you intend to call:

  - **Genability / Arcadia Data Platform**: `ARCADIA_APP_ID`, `ARCADIA_APP_KEY`

    [Create an account](https://dash.genability.com/signup), navigate to [Applications dashboard](https://dash.genability.com/org/applications), create an application, then copy the Application ID and Key.

  - **OpenEI**: `OPENEI_API_KEY`

    Request a key at the [OpenEI API signup](https://openei.org/services/api/signup/). The key arrives by email.

  - **RateAcuity Web Portal**: `RATEACUITY_USERNAME`, `RATEACUITY_PASSWORD`

    There is no self-serve signup. [Contact RateAcuity](https://rateacuity.com/contact-us/) to request Web Portal access. No API key is required for `tariff_fetch`.

- Google Chrome or Chromium installed locally (for RateAcuity)

## Configuration

Populate a `.env` file (or export the variables manually). Only set the values you need.

```
ARCADIA_APP_ID=...
ARCADIA_APP_KEY=...
OPENEI_API_KEY=...
RATEACUITY_USERNAME=...
RATEACUITY_PASSWORD=...
```

## Running CLI with uvx

If you have [uv](https://github.com/astral-sh/uv/releases) installed, you can run the cli simply with

```bash
uvx --env-file=.env --from git+https://github.com/switchbox-data/tariff_fetch tariff-fetch
```

Or, for gas tariffs:

```bash
uvx --env-file=.env --from git+https://github.com/switchbox-data/tariff_fetch tariff-fetch gas
```

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

## Running the CLI

```bash
python -m tariff_fetch.cli [OPTIONS]
```

With uv:

```bash
uv run tariff-fetch [OPTIONS]
uv run tariff-fetch ni arcadia MASTER_TARIFF_ID [EFFECTIVE_DATE] [OPTIONS]
uv run tariff-fetch gas [OPTIONS]
uv run tariff-fetch gas urdb [OPTIONS]
uv run tariff-fetch urdb ni MASTER_TARIFF_ID YEAR [OPTIONS]
```

With Just:

```bash
just cli
```

Options:

- `--state` / `-s`: two-letter state abbreviation (default: prompt)
- `--provider` / `-p`: provider to fetch (`genability`, `openei`, `rateacuity`)
- `--output-folder` / `-o`: directory for exports (default: `./outputs`)
- `--effective-date`: provider query date in `YYYY-MM-DD` format
- `--log-dir`: directory for log files
- `--log-file`: exact log file path

Omitted options will trigger interactive prompts.

When the CLI reaches the utility selection step, it caches the EIA utility parquet for 1 hour in the platform-specific
user cache directory so repeated runs do not re-download it every time. You can clear that cache with:

```bash
uv run tariff-fetch cache clear
```

### Examples

```bash
# Fully interactive run
uv run tariff-fetch

# Scripted run for Genability
uv run tariff-fetch \
  --state ca \
  --provider genability \
  --effective-date 2025-06-01 \
  --output-folder data/exports
```

The CLI suggests filenames like `outputs/openei_Utility_sector_detail-0_2024-03-18.json` before writing each file so you
can accept or override them.

## Direct Arcadia to URDB Conversion

For direct conversion of a single Arcadia master tariff to URDB JSON:

```bash
uv run tariff-fetch urdb ni 522 2025
```

Useful options:

- `--output` / `-o`: output file path
- `--apply-percentages` / `--no-apply-percentages`
- `--charge-class`: repeat to include multiple charge classes
- `--property`: repeat `key=value` to pre-fill Arcadia tariff properties
- `--force` / `-f`: overwrite an existing output file

Arcadia property overrides accept either the machine-readable property key or the user-facing property name. For
CHOICE properties, the value can be either the Arcadia option value or the user-facing choice label.

Example:

```bash
uv run tariff-fetch urdb ni 522 2025 \
  --property territoryId=123 \
  --property "Territory=Primary Territory"
```

## Direct Arcadia Raw Fetch

Fetch a single Arcadia master tariff as raw JSON without going through the interactive utility picker:

```bash
uv run tariff-fetch ni arcadia 522
uv run tariff-fetch ni arcadia 522 2025-06-01
```

If `EFFECTIVE_DATE` is omitted, the command uses today.

Useful options:

- `--output` / `-o`: output file path
- `--force` / `-f`: overwrite an existing output file
- `--log-dir`: directory for log files
- `--log-file`: exact log file path

## Show Arcadia Properties

Inspect the Arcadia property keys, user-facing names, descriptions, and CHOICE aliases for a master tariff before
running conversion:

```bash
uv run tariff-fetch show-properties 522
uv run tariff-fetch show-properties 522 2025-06-01
```

## Cache Management

Clear the cached utility parquet used by the interactive utility picker:

```bash
uv run tariff-fetch cache clear
```
