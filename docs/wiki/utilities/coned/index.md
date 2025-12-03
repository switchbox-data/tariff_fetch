# Consolidated Edison (ConEd)

**LSE ID**: 2252
**Region**: New York City, Westchester County, NY
**Service Types**: Electricity, Gas

## Overview

Consolidated Edison Company of New York, Inc. (ConEd) is one of the largest investor-owned utilities in the United States, serving approximately 3.4 million electric customers in New York City and Westchester County.

## Service Territory

ConEd's electric service territory is divided into three NYISO pricing zones:

| Zone | Territory ID | Area |
|------|--------------|------|
| H | 3632 | Upper Westchester |
| I | 3633 | Lower Westchester (including Yonkers) |
| J | 3634 | New York City (all five boroughs) |

## Residential Tariffs

| Tariff | Name | Type | Key Feature | Guide |
|--------|------|------|-------------|-------|
| SC1 (EL1) | Residential and Religious | Default | Tiered rates, no TOU | [View Guide](residential-el1/index.md) |
| SC3 (EL1-TOD) | Voluntary Time of Day | Opt-in | TOU rates (8am–midnight peak) | [View Guide](residential-el1-tou/index.md) |
| SC4 (EL1 Rate IV) | Optional Demand-Based | Opt-in | Demand charges ($/kW) | [View Guide](residential-el1-demand/index.md) |

### Tariff Comparison

| Aspect | SC1 | SC3 | SC4 |
|--------|-----|-----|-----|
| TOU | No | Yes | Yes |
| Tiering | Yes (250 kWh) | No | Partial |
| Demand Charges | No | No | **Yes** |
| Applicability | Everyone | Opt-in | Opt-in |
| Customer Charge | $20/mo | $20/mo | $29/mo |

## Shared Explainers

These guides apply to all ConEd residential tariffs:

| Guide | Description |
|-------|-------------|
| [Delivery Adjustments](delivery-adjustments.md) | MAC, RDM, CES, and other delivery surcharges explained |
| [Supply Charges](supply-charges.md) | MSC, MSC I/II adjustments, and wholesale price pass-through |
| [Riders](riders.md) | GRT, DLM, CBC, VDER, and other modular charges |
| [Variable Rates API](variable-rates-api.md) | How to retrieve time-varying rates from Arcadia APIs |

## Key Characteristics

- **Deregulated market**: Customers can choose ConEd supply or an ESCO (Energy Service Company)
- **Seasonal rates**: Summer (Jun-Sep) and Winter (Oct-May) delivery rates
- **Tiered delivery**: Consumption tiers at 250 kWh for residential (SC1 only)
- **Variable supply charges**: MSC (Market Supply Charge) changes monthly based on wholesale prices
- **Multiple riders**: GRT, DLM, VDER, CBC, and others

## Regulatory Context

ConEd is regulated by the New York Public Service Commission (NY PSC). Key regulatory frameworks affecting tariffs:

- **Revenue Decoupling**: ConEd's revenue is decoupled from sales volume
- **REV (Reforming the Energy Vision)**: Grid modernization initiative
- **VDER (Value of Distributed Energy Resources)**: Solar compensation framework
- **Clean Energy Standard**: Renewable energy mandates

## Data Sources

- [ConEd Tariff Books](https://www.coned.com/en/accounts-billing/your-bill/about-your-bill)
- [NY PSC Filings](https://www.dps.ny.gov/)
- Arcadia Signal API (LSE ID: 2252)
