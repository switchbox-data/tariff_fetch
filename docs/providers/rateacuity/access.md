# RateAcuity Access & Credentials

## Obtaining Access

There is no self-serve signup for RateAcuity. To gain access:

1. [Contact RateAcuity](https://rateacuity.com/contact-us/) to request access to the web portal.
2. They will provide you with a username and password. Copy them for the next step.
3. They will start you off with a free trial, after which the username and password will become invalid unless you subscribe to the web portal product.

## Setting Credentials

`tariff_fetch` will read the credentials from the `RATEACUITY_USERNAME` and `RATEACUITY_PASSWORD` environment variables.

Either export them, or place them in your `.env` file:

```bash
RATEACUITY_USERNAME=<your username goes here>
RATEACUITY_PASSWORD=<your password goes here>
```

!!! warning "Important"
Make sure to add `.env` to your `.gitignore` file to avoid accidentally committing your credentials to version control.

## Runtime Notes

- The CLI uses Selenium under the hood. Ensure Chrome or Chromium is installed so the automation can launch a browser session.
- If an error occurs during scraping, a `selenium_error.png` screenshot is written to the working directory to help diagnose the failure.
