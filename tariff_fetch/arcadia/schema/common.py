from typing import Literal

TariffPrivacy = Literal["PUBLIC", "UNLISTED", "PRIVATE"]

LoadServingServiceType = Literal["ELECTRICITY", "SOLAR_PV"]
TariffServiceType = Literal[LoadServingServiceType, "GAS"]
TariffType = Literal["DEFAULT", "ALTERNATIVE", "OPTIONAL_EXTRA", "RIDER"]
CustomerClass = Literal["RESIDENTIAL", "GENERAL", "SPECIAL_USE"]
TariffEffectiveOnRule = Literal["TARIFF_EFFECTIVE_DATE", "BILLING_PERIOD_START"]
TariffChargeType = Literal[
    "FIXED_PRICE",
    "CONSUMPTION_BASED",
    "DEMAND_BASED",
    "QUANTITY",
    "FORMULA",
    "MINIMUM",
    "MAXIMUM",
    "TAX",
]
TariffChargePeriod = Literal["MONTHLY", "DAILY", "QUARTERLY", "ANNUALLY", "HOURLY"]

RateChargeClass = Literal[
    "SUPPLY",
    "TRANSMISSION",
    "DISTRIBUTION",
    "TAX",
    "CONTRACTED",
    "USER_ADJUSTED",
    "AFTER_TAX",
    "OTHER",
    "NON_BYPASSABLE",
]
RateTransactionType = Literal["BUY", "SELL", "NET", "BUY_IMPORT", "SELL_IMPORT"]
RateUnit = Literal["COST_PER_UNIT", "PERCENTAGE"]

TerritoryUsageType = Literal["SERVICE", "TARIFF", "CLIMATE_ZONE", "UTILITY_CLIMATE_ZONE"]
TerritoryItemType = Literal["STATE", "COUNTY", "CITY", "ZIPCODE"]

SeasonPredominance = Literal["PREDOMINANT", "SUBSERVIENT"]

TimeOfUseType = Literal["SUPER_OFF_PEAK", "OFF_PEAK", "PARTIAL_PEAK", "ON_PEAK", "SUPER_ON_PEAK", "CRITICAL_PEAK"]
TimeOfUsePrivacy = Literal["PUBLIC", "PRIVATE"]
