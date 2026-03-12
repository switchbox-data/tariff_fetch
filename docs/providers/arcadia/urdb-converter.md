# Arcadia to URDB Converter

This page explains what the Arcadia-to-URDB converter does, what it asks for, and which Arcadia tariffs it can convert reliably today.

The goal of the converter is to turn Arcadia electricity tariffs into a URDB-style rate record that is useful for downstream analysis. It is intentionally conservative: if the tariff uses features that are not yet handled safely, the converter should stop instead of silently producing a misleading result.

## What it converts

The converter is designed for Arcadia electricity tariffs with:

- energy charges based on kWh
- optional time-of-use structure
- optional tiered consumption bands
- a customer fixed charge
- optional percentage-based adjustments that can be applied on top of matching charges

The result is a URDB-style record with:

- tariff name
- utility name
- weekday schedule
- weekend schedule
- energy rate structure
- fixed monthly charge

## What the converter asks for

When converting a tariff, you may be asked for:

- the tariff to convert
- the year to convert it for
- which charge classes to include
- whether percentage-based rates should be applied
- any Arcadia tariff property values needed to resolve the tariff

Some Arcadia tariffs depend on user inputs such as territory or service configuration. If those values are required and not already known, the converter prompts for them interactively.

## How the output should be understood

The converter produces a URDB-style approximation of the Arcadia tariff for a chosen year.

That matters because Arcadia tariffs can contain more detail than the URDB schedule model can represent directly. To bridge that gap, the converter samples the tariff across the year and collapses the result into:

- one weekday schedule for each month
- one weekend schedule for each month
- one fixed monthly charge

For many residential and other relatively simple tariffs, this is a reasonable representation. For more complex tariffs, not every Arcadia detail can be preserved exactly.

## Supported tariff behavior

The converter currently works best for tariffs with:

- standard kWh-based energy charges
- monthly billing periods
- seasonal rates
- weekday/weekend time-of-use patterns
- tiered energy rates based on consumption thresholds
- monthly customer charges
- daily customer charges that can be converted to a monthly equivalent
- simple percentage adders applied to supported charge classes

## Current limitations

Some Arcadia tariff features are not supported yet. The converter is expected to stop when they appear instead of guessing.

Examples include:

- rates whose tier limits come from a variable lookup
- rates whose value must be multiplied by an additional variable factor
- rates that depend on a quantity such as number of meters
- calendar-driven time-of-use overrides such as holiday or event calendars
- demand-based rate bands
- property-limited bands and formula-driven band logic

In practice, this means the converter currently targets simpler electricity tariffs first and does not claim full Arcadia schema coverage.

## Fixed charges

The converter outputs one fixed charge in monthly units.

- monthly fixed charges are used directly
- daily fixed charges are converted to a monthly equivalent before being averaged into the final output

If a tariff includes fixed-charge structures that do not fit this model, the converter should stop rather than emit an ambiguous result.

## Percentage-based charges

Some Arcadia tariffs include percentage-based adjustments. These can be included or excluded during conversion.

- if percentage application is enabled, supported percentage adjustments are applied to matching charge classes
- if percentage application is disabled, those adjustments are left out

This makes it easier to compare a cleaner base energy schedule against a schedule that includes percentage adders.

## Debug output

For troubleshooting, the converter saves fetched Arcadia data under `outputs/arcadia_library/` by default.

This includes:

- tariff data
- variable lookup data
- prompted property values

This folder is useful when checking why a tariff converted a certain way or why the converter stopped on a particular feature.

## Partial conversions

The current interactive flow may allow you to continue after one part of the conversion fails.

That is useful while developing or investigating difficult tariffs, but it also means you can end up with a partial URDB record if you explicitly choose to continue. For normal usage, treat a clean conversion with no skipped sections as the reliable result.

## When to trust the output

You should have the most confidence in the output when the tariff:

- is an electricity tariff
- uses standard consumption-based charges
- has ordinary seasonal or time-of-use structure
- has a simple fixed customer charge
- does not rely on advanced Arcadia-only features

If the tariff uses more advanced logic, the safer expectation is that the converter may stop and require additional support to be implemented first.
