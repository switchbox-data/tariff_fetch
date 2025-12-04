# URDB Access & Credentials 

## Obtaining Access

To gain access to URDB, you need to obtain a simple API key from NREL. The process is simple:

1. Request the API key through the [OpenEI API signup form](https://openei.org/services/api/signup/).
2. The key arrives via email, copy it for the next step.

## Setting Credentials

`tariff_fetch` will read the API key from the `OPENEI_API_KEY` environment variable.

Either export it, or place it in your `.env` file:

```bash
OPENEI_API_KEY=<your key goes here>
```

!!! warning "Important"
    Make sure to add `.env` to your `.gitignore` file to avoid accidentally committing your credentials to version control.