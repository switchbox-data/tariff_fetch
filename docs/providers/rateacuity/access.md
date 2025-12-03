# Rate Acuity Access & Runtime Notes

## Credentials

Set the following environment variables (via exports or a `.env` file) so the CLI can authenticate with the web portal:

```bash
RATEACUITY_USERNAME=...
RATEACUITY_PASSWORD=...
```

## Obtaining Access

1. There is no self-serve signup. [Contact Rate Acuity](https://rateacuity.com/contact-us/) to request portal access.
2. Use the provided username and password for both electric and gas workflows, storing them in your `.env` file if desired.

## Runtime Notes

- The CLI uses Selenium under the hood. Ensure Chrome or Chromium is installed so the automation can launch a browser session.
- If an error occurs during scraping, a `selenium_error.png` screenshot is written to the working directory to help diagnose the failure.

## Helpful Links

- Access requests: <https://rateacuity.com/contact-us/>
- Portal login: <https://portal.rateacuity.com/>
