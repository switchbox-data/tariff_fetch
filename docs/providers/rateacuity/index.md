# Rate Acuity

Rate Acuity provides US utility rate data for both electricity and gas through their web portal.

## Overview

- **Product**: Web Portal
- **Energy Types**: Electricity, Gas
- **Coverage**: US utilities
- **Data Format**: CSV
- **Authentication**: Account required

## Data Format

COMING SOON.

## CLI Modes

`tariff_fetch` supports both interactive and non-interactive RateAcuity workflows.

Non-interactive commands:

```bash
uv run tariff-fetch ni rateacuity fuzzy ny "con ed" --tariff "residential service"
uv run tariff-fetch ni rateacuity eia-id 123 --tariff "small commercial"
uv run tariff-fetch gas ni ny "con ed gas" --tariff "firm gas service"
uv run tariff-fetch gas urdb ni ny "con ed gas" --year 2025 --tariff "firm gas service"
```

The electric raw workflow has two modes:

- `ni rateacuity fuzzy`: you provide the state and a utility query string
- `ni rateacuity eia-id`: the CLI resolves the utility name from the cached parquet using an EIA ID, then proceeds

Gas currently supports fuzzy matching only:

- `gas ni`: raw gas fetch
- `gas urdb ni`: gas history to URDB conversion

## Fuzzy Matching

RateAcuity choices are only known at runtime because they come from the live web portal dropdowns. For that reason,
the non-interactive commands do not accept a stable tariff id. Instead, they fuzzy-match your input against the live
utility and schedule labels.

Behavior:

- both your query and the available RateAcuity choices are lowercased before comparison
- the best fuzzy match is selected automatically
- repeated `--tariff` queries that resolve to the same schedule are deduplicated

Examples:

```bash
# likely matches "Consolidated Edison Company of New York"
uv run tariff-fetch ni rateacuity fuzzy ny "con ed" --tariff "residential service"

# uppercase/lowercase differences do not matter
uv run tariff-fetch ni rateacuity fuzzy ny "CON ED" --tariff "RESIDENTIAL"
```

Be careful with broad tariff fragments such as `"service"` or `"residential"`. The non-interactive commands do not ask
for confirmation; they select the best match and continue.

## Features

Rate Acuity offers:

- Electricity and gas tariff data (unlike Arcadia/NREL which are electricity-only)
- Web-based interface for browsing rates
- Export functionality for rate data

## Use Cases

Rate Acuity is useful when:

- You need gas tariff data (not available in Arcadia or NREL)
- You want a second source to validate electricity rates
- You want a web portal interface for manual lookups

## Resources

- [Rate Acuity Website](https://www.rateacuity.com/)

## Contributing

If you'd like to help implement Rate Acuity support, see the [contributing guide](../../wiki/index.md#contributing).
