# Arcadia Access & Credentials

## Obtaining Access

To gain access to Arcadia (Genability), you need to create an account and generate application credentials:

1. [Create an Arcadia account](https://dash.genability.com/signup) if you don't already have one.
2. Log in and navigate to the [Applications dashboard](https://dash.genability.com/org/applications).
3. Create a new application.
4. Copy the Application ID and Application Key for the next step.

## Setting Credentials

`tariff_fetch` will read the credentials from the `ARCADIA_APP_ID` and `ARCADIA_APP_KEY` environment variables.

Either export them, or place them in your `.env` file:

```bash
ARCADIA_APP_ID=<your app id goes here>
ARCADIA_APP_KEY=<your app key goes here>
```

!!! warning "Important"
Make sure to add `.env` to your `.gitignore` file to avoid accidentally committing your credentials to version control.
