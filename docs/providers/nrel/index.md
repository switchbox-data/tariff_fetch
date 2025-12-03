# NREL / OpenEI — Utility Rate Database (URDB)

The Utility Rate Database (URDB) is a free, open dataset of US utility rates maintained by the National Renewable Energy Laboratory (NREL) and hosted on OpenEI.

## Overview

- **Provider**: NREL / OpenEI
- **Product**: Utility Rate Database (URDB)
- **Energy Types**: Electricity
- **Coverage**: US utilities (coverage varies)
- **Features**: Free access, open data
- **Authentication**: API key (free registration)

## Data Format

URDB outputs data in the an open data standard called URDB JSON. Many NREL tools already accept this standard.

- **[Short guide to URDB JSON](urdb-json-structure.md)** 
- [Official API docs on URDB JSON](https://openei.org/services/doc/rest/util_rates/?version=7) 

## Key Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /utility_rates` | Search and retrieve rates |
| `GET /utility_rates?getpage={label}` | Get a specific rate by ID |
| `GET /utility_rates?ratesforutility={name}` | Get all rates for a utility |
| `GET /utility_rates?lat={lat}&lon={lon}` | Find rates by location |

## Resources

- [Browse URDB Rates](https://openei.org/apps/USURDB/) — Interactive rate browser
- [NREL Developer Network](https://developer.nrel.gov/) — API key registration (free)

## Comparison with Arcadia

| Aspect | URDB | Arcadia |
|--------|------|---------|
| Cost | Free | Paid |
| Coverage | OK, community-maintained | Comprehensive, professionally maintained |
| Update frequency | Annual | Regular updates |
| Variable rates | Not supported | Lookups API |

