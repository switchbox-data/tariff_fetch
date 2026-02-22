# Utilities

Guides organized by utility company.

## Available Utilities

| Utility                                           | LSE ID | Region                     | Service Type |
| ------------------------------------------------- | ------ | -------------------------- | ------------ |
| [Consolidated Edison (ConEd)](coned/index.md)     | 2252   | New York City, Westchester | Electricity  |
| [PSEG Long Island (PSEG-LI)](psegli/index.md)     | 200    | Long Island, NY            | Electricity  |
| [Rochester Gas and Electric (RG&E)](rge/index.md) | 1007   | Rochester area, NY         | Electricity  |
| [NYSEG](nyseg/index.md)                           | 562    | Upstate NY                 | Electricity  |
| [National Grid – NY (NIMO)](nimo/index.md)        | 579    | Upstate NY                 | Electricity  |
| [Orange & Rockland (O&R)](or/index.md)            | 691    | Rockland/Orange, NY; NJ    | Electricity  |
| [Central Hudson](cenhud/index.md)                 | 2033   | Mid-Hudson Valley, NY      | Electricity  |
| [Rhode Island Energy (RIE)](rie/index.md)         | 507    | Rhode Island               | Electricity  |

## Cross-Utility Comparison

| Page                                                 | Description                                                           |
| ---------------------------------------------------- | --------------------------------------------------------------------- |
| [NY default rate comparison](ny-comparison/index.md) | Charge-by-charge comparison of all seven NY default residential rates |

## Adding New Utilities

To add documentation for a new utility:

1. Create a folder under `wiki/utilities/` with the utility's short name
2. Add an `index.md` with utility overview
3. Add subfolders for each tariff with detailed guides
4. Update the table above

## Utility Identifiers

When working with Arcadia/Genability data, utilities are identified by:

- **`lseId`**: Unique numeric ID (e.g., 2252 for ConEd)
- **`lseName`**: Full name (e.g., "Consolidated Edison Co-NY Inc")
- **`lseCode`**: Short code (e.g., "ConEd")

You can search for utilities using the `tariff_fetch` CLI or the Arcadia LSE API.
