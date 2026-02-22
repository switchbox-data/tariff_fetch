# New York Default Residential Rate Comparison

This page compares **default residential electric rates** across the seven major New York utilities that appear in the platform's Genability/Arcadia tariff set: Consolidated Edison (ConEd), PSEG Long Island (PSEG-LI), Rochester Gas and Electric (RG&E), New York State Electric & Gas (NYSEG), National Grid – New York (Niagara Mohawk), Orange & Rockland (O&R), and Central Hudson. Each utility’s default rate is documented in its own wiki guide; this page summarizes how charge types align across utilities and highlights structural differences.

---

## Cross-Utility Charge Comparison

Rows are **charge categories** (merged so that equivalent charges under different names count as one). Columns are the seven NY utilities. Cell content: a fixed value when the tariff shows one, “Lookup” when the rate is variable (Arcadia Lookups API), “—” when that charge does not appear on that tariff, or a short note. “(+)” indicates multiple sub-rates (e.g. by zone or season) for that category.

| Charge type                           | ConEd                       | PSEG-LI                       | RGE             | NYSEG           | National Grid   | O&R           | Central Hudson            |
| ------------------------------------- | --------------------------- | ----------------------------- | --------------- | --------------- | --------------- | ------------- | ------------------------- |
| Customer charge (fixed)               | $20/mo                      | $0.56/day                     | $23/mo          | $19/mo          | Yes (zone)      | Yes           | $22.50/mo                 |
| Bill issuance / billing               | $1.28/mo                    | —                             | $0.99/mo        | $0.89/mo        | —               | Yes           | —                         |
| Delivery volumetric (energy)          | Tiered; summer/winter; zone | TOU + season                  | $0.08316/kWh    | $0.09507/kWh    | Zone-specific   | Summer/winter | $0.1386/kWh               |
| Revenue decoupling                    | Lookup                      | Lookup                        | Lookup          | Lookup          | Lookup          | Lookup        | Lookup                    |
| Transition / restructuring            | Lookup                      | —                             | Lookup          | Lookup          | Lookup          | Lookup        | Lookup                    |
| Merchant function charge              | Lookup                      | $0.001764/kWh                 | Lookup          | Lookup          | Yes (zone)      | Lookup        | Multiple components       |
| Supply (commodity)                    | MSC by zone; Lookup         | TOU + season; fixed in tariff | Lookup          | By zone; Lookup | By zone; Lookup | Lookup        | Market price; Lookup      |
| System benefits charge                | Lookup                      | —                             | Lookup          | Lookup          | Lookup          | Lookup        | Lookup                    |
| Clean Energy Standard                 | Lookup (delivery + supply)  | —                             | REC + ZEC fixed | Lookup          | Yes             | —             | —                         |
| Minimum charge                        | $20/mo                      | $0.56/day                     | $23.99/mo       | —               | Yes             | Yes           | Yes                       |
| Customer benefit contribution (solar) | $1.84/kW                    | $0.0372/kW                    | $1.3056/kW      | $1.1917/kW      | Yes             | Yes           | Yes                       |
| EV Make Ready / EV infrastructure     | $0.0008/kWh                 | —                             | —               | $0.000127/kWh   | Yes             | Yes           | —                         |
| Dynamic load management               | Lookup                      | —                             | $0.000084/kWh   | Lookup          | Lookup          | Lookup        | —                         |
| Rate adjustment mechanism             | —                           | —                             | $0.00029/kWh    | Lookup          | Yes             | —             | Lookup                    |
| Earnings adjustment mechanism         | —                           | —                             | $0.000047/kWh   | $0.00032/kWh    | Lookup          | —             | Lookup                    |
| Arrears recovery                      | $0.0012/kWh                 | —                             | —               | Yes (phases)    | Yes             | —             | —                         |
| Gross receipts tax                    | By zone (H/I/J)             | —                             | —               | —               | —               | —             | —                         |
| VDER cost recovery                    | $0.0011/kWh                 | —                             | —               | —               | —               | —             | —                         |
| Tax surcredit                         | Lookup                      | —                             | —               | —               | —               | —             | —                         |
| Delivery adjustment / surcharge       | Lookup (MAC, etc.)          | Lookup                        | —               | —               | Yes             | Lookup        | —                         |
| Make-whole energy                     | —                           | —                             | $0.00221/kWh    | $0.00276/kWh    | —               | —             | —                         |
| Securitization                        | —                           | Lookup (offset + charge)      | —               | —               | —               | —             | —                         |
| NY State assessment / surcharge       | Lookup                      | Lookup                        | —               | —               | —               | —             | —                         |
| Low-income program                    | —                           | —                             | HEAP tiers      | —               | Yes             | Yes (tiers)   | Yes (tiers)               |
| Residential agricultural discount     | —                           | —                             | Lookup          | Lookup          | —               | —             | —                         |
| Shoreham / SPT (PSEG-LI)              | —                           | Lookup; by territory          | —               | —               | —               | —             | —                         |
| DER cost recovery                     | —                           | Lookup                        | —               | —               | —               | —             | —                         |
| Pilot / municipal (PSEG-LI)           | —                           | Yes (commodity + trans.)      | —               | —               | —               | —             | —                         |
| Energy storage surcharge              | —                           | —                             | —               | —               | —               | Yes           | —                         |
| GreenUp (National Grid)               | —                           | —                             | —               | —               | Optional        | —             | —                         |
| Market price / purchased power        | —                           | —                             | —               | —               | —               | Lookup        | Lookup                    |
| MFC components (Central Hudson)       | —                           | —                             | —               | —               | —               | —             | Lost revenue; base; admin |

---

## Qualitative Discussion

### What Collects the Rate-Case Revenue Requirement

The **revenue requirement** set in a rate case is recovered mainly through:

- **Customer charge** (fixed monthly or daily) and **delivery volumetric (energy) charge** — These are the core delivery rates. Amounts are set in the rate case and stay in effect until the next case (subject to adjustment mechanisms).
- **Supply (commodity)** — For default service, supply is usually a **pass-through**: the utility buys power and passes through cost (often with a small margin or MFC). It is not part of the traditional “rate base” revenue requirement; over- or under-collection is typically reconciled via **market supply** or **purchased power** adjustment clauses, so the utility does not keep surplus or absorb shortfalls beyond the designed mechanism.
- **Merchant function charge (MFC)** — Recovers the utility’s cost to run default supply (procurement, billing, risk). Often a small per-kWh or fixed component; may be in rate case or adjusted separately.

So: **customer charge + delivery energy charge (+ delivery adjustments that true up to allowed delivery revenue)** collect the **delivery** revenue requirement. **Supply** is a pass-through; **MFC** is the piece tied to the utility’s own supply-related costs.

### Adjustments and True-Ups

- **Revenue decoupling mechanism (RDM)** — Adjusts delivery revenue so the utility is indifferent to sales volume (true-up to allowed revenue). Over/under collection is reconciled periodically; it does not create a permanent surplus.
- **Rate adjustment mechanism (RAM)** / **Earnings adjustment mechanism (EAM)** — Typically true-ups to allowed delivery revenue or earnings. They correct for differences between actual and forecast (e.g. expenses, capital), not standalone revenue pots.
- **Transition charge** — Legacy restructuring costs; usually a fixed or formula-based recovery that runs off over time. Not part of ongoing “core” rate-case revenue.
- **Delivery adjustment / surcharge** (e.g. ConEd MAC, PSEG-LI delivery service adjustment) — Umbrella or specific true-ups for delivery costs (taxes, storm, pensions, etc.). Designed to bring actual recovery in line with allowed amounts.

These mechanisms are **reconciliation** tools: they move charges up or down so that, over time, collected amounts align with what the commission has authorized. They are not open-ended “extra” revenue; overcollection in one period is typically returned or offset in later periods.

### Policy and Program Charges (Separate Pots)

- **System benefits charge (SBC)** — Funds NYSERDA and related programs (efficiency, renewables, low-income). Set by the commission; collected from customers and transferred to program administrators. Not the utility’s revenue requirement; overcollection would be handled per program rules (e.g. rate adjustment or refund).
- **Clean Energy Standard (CES)** — RECs, ZECs, and related compliance. Often a pass-through or fixed surcharge; flows to compliance markets/contracts, not the utility’s general revenue.
- **Gross receipts tax (GRT)** — Tax on the utility levied by municipalities; passed through to customers. Not revenue to the utility; overcollection would be a tax refund or credit issue.
- **VDER cost recovery** — Recovers costs the utility pays for distributed energy (e.g. solar) under VDER; collected from ratepayers. Tied to a specific cost stream, not general rate-case revenue.
- **Arrears recovery** — Spreads cost of arrears forgiveness (e.g. COVID programs) across customers. Dedicated to that program; not core delivery revenue.
- **EV Make Ready, Energy storage surcharge** — Recover specific infrastructure or program costs; typically set to match authorized spending.
- **Shoreham / SPT (PSEG-LI)** — Long Island–specific property tax and settlement recovery; separate from core delivery revenue.
- **Securitization (PSEG-LI)** — Recovers securitized costs (e.g. bonds); flows to debt service. Not general revenue requirement.
- **Pilot / municipal (PSEG-LI)** — Payment-in-lieu-of-taxes and similar; flows to municipalities. Pass-through.
- **NY State assessment / surcharge** — State-level assessment or surcharge; remitted to the state. Pass-through.

For these, “overcollection” is possible only to the extent the mechanism is not perfectly tuned; commissions and tariffs usually provide for refunds or rate adjustments.

### Structural Differences Across NY Utilities

- **TOU vs flat**: Only **PSEG-LI** default (Rate 194) is time-of-use (peak 3–7 PM weekdays). **ConEd** has seasonal and tiered delivery but not TOU on the default EL1. **O&R** has seasonal (summer/winter) delivery. The rest are flat delivery (and usually flat supply) in the default rate.
- **Zones**: **ConEd** (H/I/J), **PSEG-LI** (Suffolk / outside Suffolk), **NYSEG** (East, West, Lower Hudson), and **National Grid** (six zones) have zone-specific delivery and/or supply. **RG&E**, **O&R**, and **Central Hudson** default rates are not zone-split in the same way.
- **Customer charge**: ConEd and RG&E are at the high end (~~$20–23/mo); NYSEG and Central Hudson in the middle (~~$19–22.50); PSEG-LI uses a daily charge (~$0.56/day ≈ $17/mo).
- **Minimum charge**: Most set a floor at or near the customer (and bill) charge; NYSEG’s SC1 has no separate minimum in the table.
- **Low-income and RAD**: RG&E (HEAP tiers), O&R (Enhanced Energy Affordability), Central Hudson (low-income tiers), NYSEG and RG&E (RAD) have eligibility-based credits or discounts; ConEd and PSEG-LI do not show a comparable default-tariff line item in this set.
- **Utility-specific**: **Shoreham/SPT**, **securitization**, **pilot/municipal**, and **DER cost recovery** are PSEG-LI-specific. **GreenUp** is National Grid optional. **Energy storage surcharge** is O&R. **MFC components** (lost revenue, base, admin) are broken out only for Central Hudson. **GRT** and **VDER** appear on ConEd’s default rate; **tax surcredit** is ConEd.

### Summary

- **Rate-case revenue** is collected mainly by **fixed customer charge** and **volumetric delivery (energy) charge**, with **RDM/RAM/EAM/delivery adjustments** trueing to allowed delivery revenue.
- **Supply** is a **pass-through**; **MFC** recovers utility supply-related costs.
- **SBC, CES, GRT, VDER, arrears, EV, Shoreham, securitization, pilot, state assessment** are **policy or pass-through** charges with their own rules; they are not part of the core delivery revenue requirement.
- Structural differences (TOU, zones, customer/minimum charges, low-income and RAD, and utility-specific riders) are what to watch when comparing bills or building models across the seven NY default rates.
