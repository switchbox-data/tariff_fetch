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

| Utility | Region | Guides Available |
|---------|--------|------------------|
| [Consolidated Edison (ConEd)](utilities/coned/index.md) | New York | EL1 Residential |

## Structure

```
wiki/
├── utilities/
│   └── coned/                    # Consolidated Edison
│       ├── index.md              # ConEd overview
│       └── residential-el1/      # EL1 Residential tariff
│           ├── index.md          # Tariff field guide
│           ├── supply-charges.md # How supply charges work
│           ├── delivery-adjustments.md
│           ├── riders.md
│           └── variable-rates-api.md
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

