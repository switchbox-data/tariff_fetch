# Rochester Gas and Electric (RG&E)

**LSE ID**: 1007
**Region**: Rochester and surrounding counties, NY
**Service Types**: Electricity, Gas

## Overview

Rochester Gas and Electric Corporation (RG&E) serves the Greater Rochester area and surrounding counties in Upstate New York. Residential default supply is RG&E Supply Service (RSS), tariff 1-RSS. Customers may choose an ESCO for supply while retaining RG&E delivery.

## Service Territory

Single primary territory (territoryId 1114) for default residential rates; no zone split in the base tariff.

## Residential Tariffs

| Tariff  | Name       | Type    | Key Feature              | Guide                                        |
| ------- | ---------- | ------- | ------------------------ | -------------------------------------------- |
| 1-RSS   | Residential | Default | Flat rate, no TOU        | [View Guide](residential-1-rss/index.md)     |

## Key Characteristics

- **Flat rate**: No time-of-use; single delivery and supply rate (with adjustments).
- **Fixed delivery**: Customer charge $23, bill issuance $0.99, energy delivery $0.08316/kWh, make-whole $0.00221/kWh.
- **Supply and many adjustments**: MFC, transition, SBC, RDM, RAM, EAM, DLM, CES, CBC (solar), low-income and RAD credits via lookups or applicability.
- **Minimum**: $23.99/month.

## Regulatory Context

- Regulated by the NY PSC. Revenue decoupling, Clean Energy Standard, system benefits, and low-income programs apply.
- RAD (Residential Agricultural Discount) and HEAP-based low-income tiers are eligibility-based.

## Data Sources

- [RG&E Electric Pricing](https://www.rge.com/understand-your-bill/electric-pricing-and-rates)
- [NY PSC](https://www.dps.ny.gov/)
- Arcadia Signal API (LSE ID: 1007)
