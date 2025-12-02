# Arcadia — Signal Tariffs API

Arcadia's Signal Tariffs API (formerly Genability) provides comprehensive US utility tariff data with detailed rate structures, variable rate lookups, and bill calculation capabilities.

## Overview

- **Provider**: Arcadia
- **Product**: Signal Tariffs API
- **Energy Types**: Electricity
- **Coverage**: ~3,000+ US utilities, 100,000+ tariffs
- **Features**: Variable rate lookups, bill calculations, historical versions
- **Authentication**: API key required

## Data Format

The Signal API uses a custom JSON objects to represent tariffs, with a complex hierarchical structure.

- **[Short guide to the Tariff JSON](tariff-json-structure.md)**
- [Official API docs on Tariff JSON](https://docs.arcadia.com/v2022-12-21-Signal/reference/tariff) 

## Key Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /tariffs` | Search and retrieve tariffs |
| `GET /tariffs/{tariffId}` | Get a specific tariff with rates |
| `GET /tariffs/{masterTariffId}/history` | Historical versions |
| `GET /properties/{key}/lookups` | Variable rate values |
| `POST /calculate` | Bill calculations |


## Pricing

Arcadia charges based on API usage. See their [pricing page](https://www.arcadia.com/signal) for current rates.

