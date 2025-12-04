# Tariff Fetch

Collect electric and gas utility tariffs from Genability/Arcadia, OpenEI, and RateAcuity through a single CLI.

## Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (optional, but the easiest way to run the CLI)
- Google Chrome or Chromium on the machine that will run RateAcuity scrapes
- Credentials for any provider you plan to call (see **Obtaining API Keys**)

## Installation & Usage

```bash
# clone the repo
git clone https://github.com/switchbox-data/tariff_fetch.git
cd tariff_fetch

# create an environment
uv sync                   # or: python -m venv .venv && source .venv/bin/activate && pip install -e .

# run electricity CLI
uv run tariff-fetch --state ca --providers genability --providers openei --output-folder outputs

# run gas CLI
uv run tariff-fetch-gas --state tx --output-folder outputs
```

Other entry points:
- `python -m tariff_fetch.cli` / `python -m tariff_fetch.cli_gas`
- `just cli` / `just cligas` (from the repo root)

Populate a `.env` file (or export variables) before running:

```bash
ARCADIA_APP_ID=...
ARCADIA_APP_KEY=...
OPENEI_API_KEY=...
RATEACUITY_USERNAME=...
RATEACUITY_PASSWORD=...
```

Omit variables for providers you do not intend to call; the CLI will prompt interactively for any missing arguments such as state or provider list.

## Obtaining API Keys & Credentials

See the provider notes for step-by-step credential setup:

- [Arcadia Signal API](providers/arcadia/access.md)
- [NREL URDB](providers/nrel/access.md)
- [RateAcuity](providers/rateacuity/access.md)

See the [CLI Usage Guide](cli-usage.md) for detailed command-line workflows and option reference.
