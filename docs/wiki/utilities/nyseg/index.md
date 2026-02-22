# New York State Electric & Gas (NYSEG)

**LSE ID**: 562
**Region**: Upstate New York (East, West, Lower Hudson Valley)
**Service Types**: Electricity, Gas

## Overview

New York State Electric & Gas Corporation (NYSEG) serves Upstate New York across three delivery zones: East, West, and Lower Hudson Valley. Residential default rate is Service Classification 1 (SC1); default supply is NYSEG Supply Service (NSS), a managed mix at variable price. Customers may choose an ESCO for supply.

## Service Territory

| Territory         | Territory ID | Area               |
| ----------------- | ------------ | ------------------ |
| East              | 3690         | Eastern NY         |
| Lower Hudson Valley | 5337       | Lower Hudson       |
| West              | 3689         | Western NY         |

## Residential Tariffs

| Tariff | Name       | Type    | Key Feature                 | Guide                                |
| ------ | ---------- | ------- | --------------------------- | ------------------------------------ |
| SC1    | Residential | Default | Flat delivery; supply by zone | [View Guide](residential-sc1/index.md) |

## Key Characteristics

- **Flat delivery**: Single energy rate $0.09507/kWh; no TOU. Supply varies by territory.
- **Fixed components**: Customer $19, bill issuance $0.89; make-whole, EAM, EV Make Ready, recovery charge, CBC (solar) have fixed or lookup rates.
- **RAD**: Residential Agricultural Discount for qualifying customers (lookup).
- **Riders**: RAM, EAM, DLM, arrears relief, late payment/waived fees, EV Make Ready.

## Regulatory Context

- NY PSC regulation. Revenue decoupling, Clean Energy Standard, system benefits, and NY-mandated riders (CBC, EV, arrears) apply.

## Data Sources

- [NYSEG Electricity Pricing](https://www.nyseg.com/w/electricity-pricing-and-tariffs)
- [NY PSC](https://www.dps.ny.gov/)
- Arcadia Signal API (LSE ID: 562)
