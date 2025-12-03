# Data Providers

`tariff_fetch` can retrieve tariff data from multiple sources. Each provider has different coverage, data formats, and API conventions.

## Supported Providers

| Provider | Product | Energy Types | Coverage | Data Format |
|----------|---------|--------------|----------|-------------|
| [Arcadia](arcadia/index.md) | Signal Tariffs API | Electricity | US utilities, comprehensive | Tariff JSON object |
| [NREL](nrel/index.md) | Utility Rate Database (URDB) | Electricity | US utilities | URDB JSON format |
| [Rate Acuity](rateacuity/index.md) | Web Portal | Electricity, Gas | US utilities | CSV exports |

## Choosing a Provider

**NREL Utility Rate Database (URDB)** is free and open but may have less detailed or less frequently updated data. Good for basic rate lookups and open-source projects.

**Arcadia Signal Tariffs API** is the most comprehensive option for US electricity tariff data. It is paid and includes:

- Detailed rate structures with tiers, seasons, and TOU periods
- Variable rate lookups via API
- Historical tariff versions

**Rate Acuity** provides both electricity and gas tariffs through their web portal. It is also paid Useful when you need gas rates or prefer a different data source for validation.

