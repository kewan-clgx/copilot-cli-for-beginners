"""Client for querying Google Places API (New) to find businesses at an address."""

from dataclasses import dataclass, field
from typing import List, Optional

import requests

TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
NEARBY_SEARCH_URL = "https://places.googleapis.com/v1/places:searchNearby"

# Request all available fields from the Nearby Search API
FIELD_MASK = ",".join([
    "places.id",
    "places.displayName",
    "places.formattedAddress",
    "places.shortFormattedAddress",
    "places.types",
    "places.primaryType",
    "places.primaryTypeDisplayName",
    "places.nationalPhoneNumber",
    "places.internationalPhoneNumber",
    "places.websiteUri",
    "places.googleMapsUri",
    "places.businessStatus",
    "places.rating",
    "places.userRatingCount",
    "places.priceLevel",
    "places.regularOpeningHours",
    "places.currentOpeningHours",
    "places.editorialSummary",
    "places.reviews",
    "places.photos",
    "places.paymentOptions",
    "places.parkingOptions",
    "places.accessibilityOptions",
    "places.outdoorSeating",
    "places.liveMusic",
    "places.delivery",
    "places.dineIn",
    "places.takeout",
    "places.reservable",
    "places.servesBreakfast",
    "places.servesLunch",
    "places.servesDinner",
    "places.servesBeer",
    "places.servesWine",
    "places.servesCocktails",
    "places.servesCoffee",
    "places.goodForChildren",
    "places.goodForGroups",
    "places.goodForWatchingSports",
    "places.allowsDogs",
    "places.restroom",
    "places.menuForChildren",
])


@dataclass
class Business:
    """Full details for a business found via Google Places API."""

    # Core identity
    place_id: str
    name: str
    primary_type: Optional[str]
    primary_type_display: Optional[str]
    types: List[str]

    # Location
    address: str
    short_address: Optional[str]
    google_maps_url: Optional[str]

    # Contact
    phone: Optional[str]
    international_phone: Optional[str]
    website: Optional[str]

    # Status & ratings
    business_status: Optional[str]
    rating: Optional[float]
    total_ratings: Optional[int]
    price_level: Optional[str]

    # Hours
    open_now: Optional[bool]
    weekday_hours: List[str] = field(default_factory=list)

    # Editorial
    editorial_summary: Optional[str] = None

    # Services & amenities
    delivery: Optional[bool] = None
    dine_in: Optional[bool] = None
    takeout: Optional[bool] = None
    reservable: Optional[bool] = None
    outdoor_seating: Optional[bool] = None
    live_music: Optional[bool] = None
    good_for_children: Optional[bool] = None
    good_for_groups: Optional[bool] = None
    allows_dogs: Optional[bool] = None
    restroom: Optional[bool] = None

    # Food service
    serves_breakfast: Optional[bool] = None
    serves_lunch: Optional[bool] = None
    serves_dinner: Optional[bool] = None
    serves_beer: Optional[bool] = None
    serves_wine: Optional[bool] = None
    serves_cocktails: Optional[bool] = None
    serves_coffee: Optional[bool] = None

    # Payment
    accepts_credit_cards: Optional[bool] = None
    accepts_debit_cards: Optional[bool] = None
    accepts_cash: Optional[bool] = None
    accepts_nfc: Optional[bool] = None

    # Accessibility
    wheelchair_accessible_entrance: Optional[bool] = None
    wheelchair_accessible_parking: Optional[bool] = None
    wheelchair_accessible_restroom: Optional[bool] = None
    wheelchair_accessible_seating: Optional[bool] = None

    # Photos & reviews count
    photo_count: int = 0
    review_count: int = 0


def search_businesses(address: str, api_key: str) -> List[Business]:
    """Search for businesses/companies at a given address.

    Uses a combined approach for maximum coverage:
    1. Geocode the address to get lat/lng coordinates
    2. Nearby Search (up to 20 results by geographic proximity)
    3. Text Search with pagination (up to 60 results by text relevance)
    4. Merge and deduplicate by place_id

    Args:
        address: The street address to search (e.g., "123 Main St, City, State").
        api_key: A valid Google Places API key.

    Returns:
        A list of Business objects found at the address.

    Raises:
        PlacesAPIError: If the API returns an error response.
    """
    # Step 1: Geocode the address to get coordinates
    lat, lng = _geocode_address(address, api_key)

    seen_place_ids = set()
    all_businesses = []

    def _add_unique(business):
        if business.place_id not in seen_place_ids:
            seen_place_ids.add(business.place_id)
            all_businesses.append(business)

    # Step 2: Nearby Search — finds businesses by geographic proximity (max 20)
    nearby_headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": FIELD_MASK,
    }

    nearby_body = {
        "locationRestriction": {
            "circle": {
                "center": {"latitude": lat, "longitude": lng},
                "radius": 50.0,
            }
        },
        "maxResultCount": 20,
    }

    response = requests.post(NEARBY_SEARCH_URL, json=nearby_body, headers=nearby_headers)
    if response.status_code == 200:
        data = response.json()
        for place in data.get("places", []):
            display_name = place.get("displayName", {})
            name = display_name.get("text", "Unknown")
            if name.lower().strip() == address.lower().strip():
                continue
            _add_unique(_parse_place(place))

    # Step 3: Text Search with pagination — finds additional results by relevance
    text_headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": FIELD_MASK + ",nextPageToken",
    }

    text_body = {
        "textQuery": f"businesses at {address}",
        "locationBias": {
            "circle": {
                "center": {"latitude": lat, "longitude": lng},
                "radius": 200.0,
            }
        },
        "pageSize": 20,
    }

    max_pages = 3
    for _ in range(max_pages):
        response = requests.post(TEXT_SEARCH_URL, json=text_body, headers=text_headers)

        if response.status_code != 200:
            break

        data = response.json()
        for place in data.get("places", []):
            display_name = place.get("displayName", {})
            name = display_name.get("text", "Unknown")
            if name.lower().strip() == address.lower().strip():
                continue
            _add_unique(_parse_place(place))

        next_page_token = data.get("nextPageToken")
        if not next_page_token:
            break
        text_body["pageToken"] = next_page_token

    return all_businesses


def search_by_name(query: str, api_key: str) -> List[Business]:
    """Search for businesses by name using Text Search.

    Automatically paginates to retrieve all available results (up to 60).

    Args:
        query: Business name query, optionally with location context
               (e.g., "Cotality Irvine" or "Starbucks 92618").
        api_key: A valid Google Places API key.

    Returns:
        A list of Business objects matching the query.

    Raises:
        PlacesAPIError: If the API returns an error response.
    """
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": FIELD_MASK + ",nextPageToken",
    }

    body = {
        "textQuery": query,
        "pageSize": 20,
    }

    all_businesses = []
    max_pages = 3  # Google allows up to 3 pages (60 results total)

    for _ in range(max_pages):
        response = requests.post(TEXT_SEARCH_URL, json=body, headers=headers)

        if response.status_code != 200:
            error_msg = _parse_error(response)
            raise PlacesAPIError(response.status_code, error_msg)

        data = response.json()
        places = data.get("places", [])
        all_businesses.extend(_parse_place(place) for place in places)

        # Check for next page
        next_page_token = data.get("nextPageToken")
        if not next_page_token:
            break
        body["pageToken"] = next_page_token

    return all_businesses


def _parse_place(place: dict) -> Business:
    """Parse a Places API response object into a Business dataclass."""
    display_name = place.get("displayName", {})
    primary_type_display = place.get("primaryTypeDisplayName", {})
    opening_hours = place.get("regularOpeningHours", {})
    current_hours = place.get("currentOpeningHours", {})
    payment = place.get("paymentOptions", {})
    accessibility = place.get("accessibilityOptions", {})
    editorial = place.get("editorialSummary", {})

    return Business(
        place_id=place.get("id", ""),
        name=display_name.get("text", "Unknown"),
        primary_type=place.get("primaryType"),
        primary_type_display=primary_type_display.get("text") if primary_type_display else None,
        types=place.get("types", []),
        address=place.get("formattedAddress", "N/A"),
        short_address=place.get("shortFormattedAddress"),
        google_maps_url=place.get("googleMapsUri"),
        phone=place.get("nationalPhoneNumber"),
        international_phone=place.get("internationalPhoneNumber"),
        website=place.get("websiteUri"),
        business_status=place.get("businessStatus"),
        rating=place.get("rating"),
        total_ratings=place.get("userRatingCount"),
        price_level=place.get("priceLevel"),
        open_now=current_hours.get("openNow"),
        weekday_hours=opening_hours.get("weekdayDescriptions", []),
        editorial_summary=editorial.get("text") if editorial else None,
        delivery=place.get("delivery"),
        dine_in=place.get("dineIn"),
        takeout=place.get("takeout"),
        reservable=place.get("reservable"),
        outdoor_seating=place.get("outdoorSeating"),
        live_music=place.get("liveMusic"),
        good_for_children=place.get("goodForChildren"),
        good_for_groups=place.get("goodForGroups"),
        allows_dogs=place.get("allowsDogs"),
        restroom=place.get("restroom"),
        serves_breakfast=place.get("servesBreakfast"),
        serves_lunch=place.get("servesLunch"),
        serves_dinner=place.get("servesDinner"),
        serves_beer=place.get("servesBeer"),
        serves_wine=place.get("servesWine"),
        serves_cocktails=place.get("servesCocktails"),
        serves_coffee=place.get("servesCoffee"),
        accepts_credit_cards=payment.get("acceptsCreditCards"),
        accepts_debit_cards=payment.get("acceptsDebitCards"),
        accepts_cash=payment.get("acceptsCashOnly"),
        accepts_nfc=payment.get("acceptsNfc"),
        wheelchair_accessible_entrance=accessibility.get("wheelchairAccessibleEntrance"),
        wheelchair_accessible_parking=accessibility.get("wheelchairAccessibleParking"),
        wheelchair_accessible_restroom=accessibility.get("wheelchairAccessibleRestroom"),
        wheelchair_accessible_seating=accessibility.get("wheelchairAccessibleSeating"),
        photo_count=len(place.get("photos", [])),
        review_count=len(place.get("reviews", [])),
    )


def _geocode_address(address: str, api_key: str) -> tuple:
    """Convert an address to lat/lng using Text Search (no separate Geocoding API needed)."""
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.location",
    }
    body = {"textQuery": address, "maxResultCount": 1}

    response = requests.post(TEXT_SEARCH_URL, json=body, headers=headers)

    if response.status_code != 200:
        error_msg = _parse_error(response)
        raise PlacesAPIError(response.status_code, error_msg)

    data = response.json()
    places = data.get("places", [])
    if not places:
        raise PlacesAPIError(400, f"Could not find location for: {address}")

    location = places[0].get("location", {})
    lat = location.get("latitude")
    lng = location.get("longitude")
    if lat is None or lng is None:
        raise PlacesAPIError(400, f"No coordinates returned for: {address}")

    return lat, lng


def _parse_error(response: requests.Response) -> str:
    """Extract a readable error message from an API error response."""
    try:
        error_data = response.json()
        error = error_data.get("error", {})
        return error.get("message", f"HTTP {response.status_code}")
    except (ValueError, KeyError):
        return f"HTTP {response.status_code}: {response.text[:200]}"


class PlacesAPIError(Exception):
    """Raised when the Google Places API returns an error."""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"Places API Error ({status_code}): {message}")
