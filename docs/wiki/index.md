# Tariff Wiki

This section contains domain knowledge for understanding and working with electricity tariffs downloaded using `tariff_fetch`.

## What's Here

When you download tariff data from sources like Arcadia (Genability), you get detailed JSON structures with rates, riders, adjustments, and more. This wiki provides:

- **Utility-specific guides** explaining rate structures, charges, and regulatory context
- **Rate plan breakdowns** with charge-by-charge explanations
- **API guides** for retrieving variable rate values
- **Domain knowledge** about how utility billing actually works

## Why This Exists

Tariff data is complex. A single residential tariff might have:

- 20+ line items with different charge types
- Variable rates that require API lookups
- Riders that reference other tariff documents
- Zone-specific and seasonal variations
- Regulatory adjustment mechanisms with multi-month time lags

This wiki explains what all of that means so you can actually use the data.

## Utilities Covered

| Utility                                                       | Region       | Guides Available              |
| ------------------------------------------------------------- | ------------ | ----------------------------- |
| [Consolidated Edison (ConEd)](utilities/coned/index.md)       | New York     | EL1 Residential               |
| [PSEG Long Island](utilities/psegli/index.md)                  | New York     | Rate 194 (default)           |
| [RG&E](utilities/rge/index.md)                                | New York     | 1-RSS (default)              |
| [NYSEG](utilities/nyseg/index.md)                             | New York     | SC1 (default)                |
| [National Grid – NY](utilities/nimo/index.md)                  | New York     | SC1 (default)                 |
| [Orange & Rockland](utilities/or/index.md)                     | New York     | Rate 1 (default)              |
| [Central Hudson](utilities/cenhud/index.md)                   | New York     | Rate 1 (default)              |
| [Rhode Island Energy](utilities/rie/index.md)                  | Rhode Island | A-16 (default)                |

See also [NY default rate comparison](utilities/ny-comparison/index.md) for a cross-utility charge comparison.

## Structure

```
wiki/
├── utilities/
│   ├── coned/                    # Consolidated Edison
│   │   ├── index.md
│   │   ├── residential-el1/
│   │   │   └── index.md
│   │   ├── delivery-adjustments.md
│   │   ├── riders.md
│   │   ├── supply-charges.md
│   │   └── variable-rates-api.md
│   ├── ny-comparison/            # NY default rate comparison
│   │   └── index.md
│   ├── psegli/                   # PSEG Long Island
│   │   ├── index.md
│   │   └── residential-194/
│   │       └── index.md
│   ├── rge/                      # RG&E
│   │   ├── index.md
│   │   └── residential-1-rss/
│   │       └── index.md
│   ├── nyseg/                    # NYSEG
│   │   ├── index.md
│   │   └── residential-sc1/
│   │       └── index.md
│   ├── nimo/                     # National Grid NY
│   │   ├── index.md
│   │   └── residential-sc1/
│   │       └── index.md
│   ├── or/                       # Orange & Rockland
│   │   ├── index.md
│   │   └── residential-1/
│   │       └── index.md
│   ├── cenhud/                   # Central Hudson
│   │   ├── index.md
│   │   └── residential-1/
│   │       └── index.md
│   └── rie/                      # Rhode Island Energy
│       ├── index.md
│       └── residential-a16/
│           └── index.md
```

## Contributing

To add or update wiki content:

1. **Follow the structure** — New utilities go in `docs/wiki/utilities/{utility-code}/`. Each rate plan gets its own subdirectory.

2. **Use the existing format** — Look at the ConEd EL1 guides for the expected structure:
   - `index.md` — Tariff overview with metadata, properties, and charge reference table
   - Separate files for deep dives (supply charges, delivery adjustments, riders, etc.)

3. **Submit a PR** — Open a pull request with your changes. Include the tariff JSON you're documenting if it's not already in the repo.

## Disclaimer

> ⚠️ The guides in this wiki are for educational purposes. They were initially generated with AI assistance and have not been verified by utility rate experts. Verify any claims against official utility tariff books before using for business or regulatory purposes.
