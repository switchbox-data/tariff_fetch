# RateAcuity

## Credentials

Set the following environment variables (via exports or a `.env` file) to allow the CLI to authenticate with the Web Portal:

```bash
RATEACUITY_USERNAME=...
RATEACUITY_PASSWORD=...
```

## Obtaining Access

1. There is no self-serve signup. [Contact RateAcuity](https://rateacuity.com/contact-us/) to request Web Portal access.
2. Use the provided username and password for both electric and gas workflows, saving them in your `.env` file if desired.

## Runtime Notes

- The CLI uses Selenium under the hood. Ensure Chrome or Chromium is installed so the automation can launch a browser session.
- If an error occurs during scraping, a `selenium_error.png` screenshot is saved in the working directory to help diagnose the failure.
