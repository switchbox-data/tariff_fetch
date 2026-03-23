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
uv run tariff-fetch ni rateacuity fuzzy STATE UTILITY_QUERY --tariff TARIFF_QUERY [--tariff TARIFF_QUERY ...] [OPTIONS]
uv run tariff-fetch ni rateacuity eia-id EIA_ID --tariff TARIFF_QUERY [--tariff TARIFF_QUERY ...] [OPTIONS]
uv run tariff-fetch gas [OPTIONS]
uv run tariff-fetch gas ni STATE UTILITY_QUERY --tariff TARIFF_QUERY [OPTIONS]
uv run tariff-fetch gas urdb [OPTIONS]
uv run tariff-fetch gas urdb ni STATE UTILITY_QUERY --year YEAR --tariff TARIFF_QUERY [OPTIONS]
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
- `--no-input`: fail instead of prompting for interactive input
- `--log-dir`: directory for log files
- `--log-file`: exact log file path

Omitted options will trigger interactive prompts.

Use `--no-input` for automation or CI runs when you want missing required inputs to fail fast instead of opening an
interactive prompt.

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
- `--cc`: compact charge-class selector using `S T D t C U A O N n`
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

## Direct RateAcuity Fetch

RateAcuity does not expose a stable tariff identifier like Arcadia's `master_tariff_id`, so the non-interactive
commands work by fuzzy-matching your input against the live dropdown choices shown in the RateAcuity web portal at
runtime.

Available commands:

```bash
uv run tariff-fetch ni rateacuity fuzzy ny "con ed" --tariff "residential service"
uv run tariff-fetch ni rateacuity eia-id 123 --tariff "residential service"
uv run tariff-fetch gas ni ny "con ed gas" --tariff "firm gas service"
uv run tariff-fetch gas urdb ni ny "con ed gas" --year 2025 --tariff "firm gas service"
```

### How fuzzy matching works

- The CLI loads the current RateAcuity utility list for the requested state.
- It lowercases both your query and every available RateAcuity choice before scoring them.
- It picks the highest-scoring utility match.
- After selecting that utility, it loads the current tariff list and fuzzy-matches each `--tariff` query the same way.
- If multiple `--tariff` queries resolve to the same RateAcuity tariff, the duplicate is ignored and that tariff is only fetched once.

This means your query does not need to be an exact string from the portal. Shortened, lowercased, or partial input is
usually fine.

Examples:

```bash
# Utility query does not need to match RateAcuity text exactly
uv run tariff-fetch ni rateacuity fuzzy ny "con ed" --tariff "residential service"

# Tariff queries are also fuzzy-matched and case-insensitive
uv run tariff-fetch ni rateacuity fuzzy ny "consolidated edison" \
  --tariff "RESIDENTIAL" \
  --tariff "time of use"

# Electric raw fetch using EIA-based utility lookup from the cached parquet
uv run tariff-fetch ni rateacuity eia-id 123 --tariff "small commercial"
```

### Important fuzzy-matching behavior

- Matching is performed against the live strings that RateAcuity returns in the browser session.
- Matching is case-insensitive because both sides are compared as lowercase.
- The command does not stop to ask "did you mean X?" in non-interactive mode. It chooses the best match and proceeds.
- If your query is too broad, the "best" result may still be the wrong tariff.

In practice, use queries that are distinctive enough to narrow the target:

- Better: `"residential service"`
- Riskier: `"residential"`
- Better: `"firm gas service"`
- Riskier: `"service"`

When you are unsure what RateAcuity calls a tariff, start with the interactive flow once, note the exact names shown in
the dropdowns, and then use those strings in the non-interactive commands.

### RateAcuity command summary

- `tariff-fetch ni rateacuity fuzzy`: electric raw fetch by state plus fuzzy utility/tariff matching
- `tariff-fetch ni rateacuity eia-id`: electric raw fetch by utility EIA id, then fuzzy tariff matching
- `tariff-fetch gas ni`: gas raw fetch by state plus fuzzy utility/tariff matching
- `tariff-fetch gas urdb ni`: gas URDB conversion by state plus fuzzy utility/tariff matching

For `tariff-fetch gas urdb ni`, you must also provide the conversion year and any URDB metadata you want to override:

```bash
uv run tariff-fetch gas urdb ni ny "con ed gas" \
  --year 2025 \
  --tariff "firm gas service" \
  --label ceg \
  --sector Commercial \
  --servicetype Delivery \
  --apply-percentages
```

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
