# 🏢 Places App — Find Businesses at an Address

A simple Python CLI that uses the **Google Places API (New)** Text Search endpoint to find all businesses/companies at a given address.

## Prerequisites

1. A Google Cloud project with **billing enabled**
2. The **Places API (New)** enabled in your project
3. An **API key** with access to the Places API

> 📖 See the [research report](../../.copilot/session-state/) or [Google's setup guide](https://developers.google.com/maps/get-started) for detailed instructions on enabling the API.

## Setup

```bash
# Navigate to this directory
cd samples/places-app

# Install dependencies
pip install requests python-dotenv pytest

# Create your .env file from the example
cp .env.example .env

# Edit .env and add your API key
# GOOGLE_PLACES_API_KEY=AIzaSy...your-actual-key
```

## Usage

**With command-line argument:**
```bash
python places_app.py "1600 Amphitheatre Parkway, Mountain View, CA"
```

**With interactive prompt:**
```bash
python places_app.py
# Enter an address to search: 1600 Amphitheatre Parkway, Mountain View, CA
```

**Example output:**
```
Searching for businesses at: 1600 Amphitheatre Parkway, Mountain View, CA

Found 3 business(es):

#    Business Name                       Address
———  —————————————————————————————————   ————————————————————————————————————————
1    Google                              1600 Amphitheatre Pkwy, Mountain View, CA 94043
2    Google Store                        1600 Amphitheatre Pkwy, Mountain View, CA 94043
3    Google Visitor Experience           1600 Amphitheatre Pkwy, Mountain View, CA 94043
```

## Running Tests

```bash
python -m pytest tests/ -v
```

## How It Works

1. Loads your API key from `.env`
2. Sends a `POST` request to `https://places.googleapis.com/v1/places:searchText`
3. Uses `X-Goog-FieldMask` to request only the fields we need (saves cost!)
4. Filters by `includedTypes: ["establishment"]` to focus on businesses
5. Displays results in a formatted table

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `Places API (New) has not been used...` | API not enabled | Enable "Places API (New)" in Cloud Console |
| `The provided API key is invalid` | Wrong key | Check `.env` — key should start with `AIzaSy` |
| `REQUEST_DENIED` | Billing not active | Link a billing account to your project |
| No results | Address too specific | Try a broader address (street + city) |

## Pricing

Text Search uses the **Pro tier**: 5,000 free requests/month, then $32 per 1,000 requests. Using `X-Goog-FieldMask` ensures you only pay for the fields you request.
