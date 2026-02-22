# Central Hudson Gas & Electric (Central Hudson)

**LSE ID**: 2033
**Region**: Mid-Hudson Valley, NY (Ulster, Dutchess, and surrounding counties)
**Service Types**: Electricity, Gas

## Overview

Central Hudson Gas & Electric Corporation serves the Mid-Hudson Valley, including Ulster, Dutchess, and surrounding counties. The default residential electric rate is Rate 1: flat, non-TOU, with customer charge, energy (delivery), MFC components (lost revenue, base supply, administration), market price and purchased power adjustments, and standard NY policy riders.

## Service Territory

Single primary territory (territoryId 2285) for default residential.

## Residential Tariffs

| Tariff | Name       | Type    | Key Feature        | Guide                              |
| ------ | ---------- | ------- | ------------------ | ---------------------------------- |
| 1      | Residential | Default | Flat; MFC split into 3 components | [View Guide](residential-1/index.md) |

## Key Characteristics

- **Flat rate**: No TOU; single energy charge for delivery.
- **MFC**: Allocated into lost revenue, base supply, and administration charges.
- **Supply**: Market Price Charge, Market Price Adjustment, Purchased Power Adjustment, Electric Bill Credit (lookups or variable).
- **NY riders**: RDM, Transition, SBC, EAM, RAM, CBC (solar), low-income discount (tiered).

## Regulatory Context

- NY PSC. Revenue decoupling, Clean Energy Standard, system benefits, and low-income programs apply.

## Data Sources

- [Central Hudson Rates](https://www.cenhud.com/)
- [NY PSC](https://www.dps.ny.gov/)
- Arcadia Signal API (LSE ID: 2033)
