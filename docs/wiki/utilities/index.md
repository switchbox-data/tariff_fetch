# Utilities

Guides organized by utility company.

## Available Utilities

| Utility | LSE ID | Region | Service Type |
|---------|--------|--------|--------------|
| [Consolidated Edison (ConEd)](coned/index.md) | 2252 | New York City, Westchester | Electricity |

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
