# Places App — Integration Guide

A Python client for the **Google Places API (New)** that finds businesses at a given address or by name. This guide covers architecture, usage, and how to integrate `places_client.py` into other agents or applications.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Setup & Prerequisites](#setup--prerequisites)
3. [CLI Usage](#cli-usage)
4. [Python API Reference](#python-api-reference)
5. [Search Strategies](#search-strategies)
6. [Client-Side Filtering](#client-side-filtering)
7. [Integrating Into Another Agent](#integrating-into-another-agent)
8. [Data Model — Business Dataclass](#data-model--business-dataclass)
9. [Error Handling](#error-handling)
10. [Cost & Billing Considerations](#cost--billing-considerations)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│  places_app.py (CLI)                                                │
│  - argparse input (--address, --city, --zipcode, --business-name)   │
│  - Client-side post-filtering (address, city, zipcode)              │
│  - Summary table + interactive detail viewer                        │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ calls
┌──────────────────────────────▼──────────────────────────────────────┐
│  places_client.py (API Client Library)                              │
│  - search_businesses(address, api_key) → List[Business]             │
│  - search_by_name(query, api_key) → List[Business]                  │
│  - Business dataclass (40+ fields)                                  │
│  - PlacesAPIError exception class                                   │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ HTTP POST (requests)
┌──────────────────────────────▼──────────────────────────────────────┐
│  Google Places API (New)                                            │
│  - /v1/places:searchText    (Text Search)                           │
│  - /v1/places:searchNearby  (Nearby Search)                         │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Setup & Prerequisites

### 1. Google Cloud Project

1. Create a project at [console.cloud.google.com](https://console.cloud.google.com)
2. Enable **Places API (New)** (not the legacy Places API)
3. Enable **billing** on the project
4. Create an API key under Credentials

### 2. Environment Configuration

```bash
# Copy the example and add your key
cp .env.example .env
```

`.env` file:
```
GOOGLE_PLACES_API_KEY=AIzaSy...your-key-here
```

### 3. Install Dependencies

```bash
pip install requests python-dotenv pytest
```

Or using pyproject.toml:
```bash
pip install -e .
```

---

## CLI Usage

### Search by address (finds all businesses at a location)

```bash
# Named parameters (recommended)
python places_app.py --address "15435 Jeffrey Rd" --city "Irvine" --zipcode "92618"

# Positional (legacy)
python places_app.py "40 Pacifica, Irvine, CA 92618"
```

### Search by business name

```bash
python places_app.py --business-name "Cotality" --city "Irvine"
python places_app.py --business-name "HERITAGE ESCROW" --zipcode "92618"
```

### Parameters

| Flag | Short | Type | Description |
|------|-------|------|-------------|
| `--address` | `-a` | str | Street address line |
| `--city` | `-c` | str | City name (used as location filter) |
| `--zipcode` | `-z` | str | ZIP/postal code (used as location filter) |
| `--business-name` | `-b` | str | Business name to search (switches to name mode) |

All parameters are parsed as strings. When `--business-name` is provided, the app uses Text Search by name mode. Otherwise, it uses address-based search.

---

## Python API Reference

### `search_businesses(address: str, api_key: str) -> List[Business]`

Finds businesses at a physical address using a combined strategy:
1. Geocodes the address → lat/lng
2. Nearby Search (50m radius, max 20 results)
3. Text Search with pagination (up to 3 pages × 20 = 60 results)
4. Deduplicates by `place_id`

```python
from places_client import search_businesses

businesses = search_businesses("15435 Jeffrey Rd, Irvine, CA 92618", api_key)
for biz in businesses:
    print(f"{biz.name} | {biz.phone} | {biz.rating}")
```

### `search_by_name(query: str, api_key: str) -> List[Business]`

Searches for businesses by name (with optional location context). Paginates automatically (up to 60 results).

```python
from places_client import search_by_name

businesses = search_by_name("Cotality Irvine", api_key)
```

### `PlacesAPIError`

Raised when the Google API returns a non-200 response.

```python
from places_client import PlacesAPIError

try:
    results = search_businesses(address, api_key)
except PlacesAPIError as e:
    print(f"HTTP {e.status_code}: {e.message}")
```

---

## Search Strategies

### Address-Based Search (Combined Approach)

The app uses **two complementary APIs** to maximize coverage:

| API | Strength | Limit | Pagination |
|-----|----------|-------|------------|
| Nearby Search | Geographic precision (radius-based) | 20 results max | ❌ Not supported |
| Text Search | Text relevance + location bias | 20 per page | ✅ Up to 3 pages (60 total) |

**Why both?** Nearby Search catches businesses that Text Search might rank low by text relevance. Text Search catches businesses that fall slightly outside the 50m radius. Together they provide the most complete picture.

**Deduplication:** Results from both APIs are merged by `place_id` — no duplicates.

### Name-Based Search

Uses Text Search exclusively with the business name as `textQuery`. Location parameters (city, zipcode) are appended to improve relevance but are **not strict filters** at the API level.

---

## Client-Side Filtering

Google's APIs treat location parameters as **hints/bias**, not strict geographic filters. The CLI applies client-side post-filtering to enforce exact matches:

```python
# Post-filter logic (in places_app.py)
if args.address:
    businesses = [b for b in businesses if args.address.lower() in b.address.lower()]
if args.zipcode:
    businesses = [b for b in businesses if args.zipcode in b.address]
if args.city:
    businesses = [b for b in businesses if args.city.lower() in b.address.lower()]
```

This ensures that `--zipcode "92618"` only shows businesses whose Google-formatted address actually contains "92618".

---

## Integrating Into Another Agent

### Option 1: Import as a Python module

The simplest integration — import `places_client.py` directly into your agent code.

```python
import sys
sys.path.append("/path/to/samples/places-app")

from places_client import search_businesses, search_by_name, Business, PlacesAPIError

# Your agent's function
def find_businesses_at_location(address: str, zipcode: str = None) -> list[dict]:
    """Agent tool: find businesses at an address."""
    api_key = os.getenv("GOOGLE_PLACES_API_KEY")

    businesses = search_businesses(address, api_key)

    # Apply zipcode filter if specified
    if zipcode:
        businesses = [b for b in businesses if zipcode in b.address]

    # Convert to dict for agent consumption
    return [
        {
            "name": b.name,
            "place_id": b.place_id,
            "address": b.address,
            "phone": b.phone,
            "rating": b.rating,
            "type": b.primary_type_display or b.primary_type,
            "website": b.website,
            "business_status": b.business_status,
        }
        for b in businesses
    ]
```

### Option 2: Call as a subprocess

If your agent runs in a different environment or language, shell out to the CLI:

```python
import subprocess
import json

def search_places_cli(address: str, city: str = None, zipcode: str = None) -> str:
    """Run places_app.py and capture output."""
    cmd = ["python", "places_app.py", "--address", address]
    if city:
        cmd.extend(["--city", city])
    if zipcode:
        cmd.extend(["--zipcode", zipcode])

    result = subprocess.run(cmd, capture_output=True, text=True, cwd="/path/to/places-app")
    return result.stdout
```

### Option 3: Wrap as an MCP tool

For Copilot CLI or other MCP-compatible agents, expose the search as a tool:

```python
# mcp_places_tool.py — example MCP tool wrapper
from places_client import search_businesses, search_by_name, PlacesAPIError
import os
import json

def places_search(address: str = None, business_name: str = None,
                  city: str = None, zipcode: str = None) -> str:
    """
    MCP Tool: Search Google Places for businesses.

    Args:
        address: Street address to search at
        business_name: Business name to search for
        city: City filter (post-filter)
        zipcode: ZIP code filter (post-filter)

    Returns:
        JSON array of business results
    """
    api_key = os.getenv("GOOGLE_PLACES_API_KEY")

    if business_name:
        query_parts = [business_name]
        if city:
            query_parts.append(city)
        if zipcode:
            query_parts.append(zipcode)
        businesses = search_by_name(" ".join(query_parts), api_key)
    elif address:
        query_parts = [address]
        if city:
            query_parts.append(city)
        if zipcode:
            query_parts.append(zipcode)
        businesses = search_businesses(", ".join(query_parts), api_key)
    else:
        return json.dumps({"error": "Provide --address or --business-name"})

    # Post-filter
    if address:
        businesses = [b for b in businesses if address.lower() in b.address.lower()]
    if zipcode:
        businesses = [b for b in businesses if zipcode in b.address]
    if city:
        businesses = [b for b in businesses if city.lower() in b.address.lower()]

    # Serialize
    results = []
    for b in businesses:
        results.append({
            "place_id": b.place_id,
            "name": b.name,
            "type": b.primary_type_display or b.primary_type,
            "address": b.address,
            "phone": b.phone,
            "website": b.website,
            "rating": b.rating,
            "total_reviews": b.total_ratings,
            "business_status": b.business_status,
            "open_now": b.open_now,
        })

    return json.dumps(results, indent=2)
```

### Option 4: Use in a Copilot CLI Skill

Create a skill that wraps the places search:

```yaml
# .github/skills/places-lookup/SKILL.md
---
name: places-lookup
description: Look up businesses at an address using Google Places API
---

# Places Lookup Skill

Search for businesses at a given address or by name.

## Instructions

1. Import `places_client` from `samples/places-app/`
2. Call `search_businesses(address, api_key)` or `search_by_name(query, api_key)`
3. Filter results by zipcode/city if specified
4. Return formatted results to the user
```

---

## Data Model — Business Dataclass

The `Business` dataclass contains ~40 fields grouped by category:

| Category | Fields |
|----------|--------|
| **Core Identity** | `place_id`, `name`, `primary_type`, `primary_type_display`, `types` |
| **Location** | `address`, `short_address`, `google_maps_url` |
| **Contact** | `phone`, `international_phone`, `website` |
| **Status & Ratings** | `business_status`, `rating`, `total_ratings`, `price_level` |
| **Hours** | `open_now`, `weekday_hours` (list of strings) |
| **Editorial** | `editorial_summary` |
| **Services** | `delivery`, `dine_in`, `takeout`, `reservable`, `outdoor_seating`, `live_music`, `good_for_children`, `good_for_groups`, `allows_dogs`, `restroom` |
| **Food & Drinks** | `serves_breakfast`, `serves_lunch`, `serves_dinner`, `serves_beer`, `serves_wine`, `serves_cocktails`, `serves_coffee` |
| **Payment** | `accepts_credit_cards`, `accepts_debit_cards`, `accepts_cash`, `accepts_nfc` |
| **Accessibility** | `wheelchair_accessible_entrance`, `wheelchair_accessible_parking`, `wheelchair_accessible_restroom`, `wheelchair_accessible_seating` |
| **Media** | `photo_count`, `review_count` |

All optional fields default to `None` (not all businesses have all data).

---

## Error Handling

| Scenario | Behavior |
|----------|----------|
| Invalid/missing API key | `PlacesAPIError(403, "PERMISSION_DENIED")` |
| Address cannot be geocoded | `PlacesAPIError(404, "Could not find location...")` |
| Nearby Search fails | Silently skipped; Text Search still runs |
| Text Search page fails | Stops pagination; returns results collected so far |
| No results after filtering | Returns empty list; CLI prints "No businesses found" |

---

## Cost & Billing Considerations

Google Places API (New) charges per request based on the **field mask**:

| Tier | Example Fields | Cost (approx.) |
|------|---------------|----------------|
| **Essentials** | displayName, formattedAddress, types | $0 (included) |
| **Pro** | rating, reviews, openingHours, phone | ~$0.02/request |
| **Enterprise** | photos, editorialSummary, paymentOptions | ~$0.05/request |

Our `FIELD_MASK` requests Enterprise-tier fields. For a typical address search:
- 1 geocode request (Text Search)
- 1 Nearby Search request
- 1–3 Text Search requests (pagination)
- **Total: 3–5 API calls per search** (~$0.15–$0.25)

To reduce cost, trim `FIELD_MASK` in `places_client.py` to only the fields you need.

---

## File Structure

```
samples/places-app/
├── places_client.py          # API client library (import this)
├── places_app.py             # CLI entry point
├── .env.example              # API key template
├── .env                      # Your API key (gitignored)
├── pyproject.toml            # Python project config
├── README.md                 # Quick-start guide
├── places_api_integration.md # This document
└── tests/
    └── test_places_client.py # Unit tests (mocked HTTP)
```
