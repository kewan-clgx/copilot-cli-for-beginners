"""CLI app to find businesses at a given address using Google Places API."""

import argparse
import os
import sys

from dotenv import load_dotenv

from places_client import PlacesAPIError, search_businesses, search_by_name


def format_bool(value):
    """Format a boolean for display."""
    if value is None:
        return "—"
    return "Yes" if value else "No"


def print_business_details(index: int, biz) -> None:
    """Print full details for a single business."""
    print(f"\n{'='*60}")
    print(f"  #{index} — {biz.name}")
    print(f"{'='*60}")

    # Core info
    print(f"  Place ID:       {biz.place_id}")
    if biz.primary_type_display:
        print(f"  Type:           {biz.primary_type_display}")
    elif biz.primary_type:
        print(f"  Type:           {biz.primary_type}")
    if biz.types:
        print(f"  All Types:      {', '.join(biz.types)}")

    # Location
    print(f"\n  📍 Location")
    print(f"  Address:        {biz.address}")
    if biz.short_address:
        print(f"  Short Address:  {biz.short_address}")
    if biz.google_maps_url:
        print(f"  Google Maps:    {biz.google_maps_url}")

    # Contact
    if biz.phone or biz.website:
        print(f"\n  📞 Contact")
        if biz.phone:
            print(f"  Phone:          {biz.phone}")
        if biz.international_phone:
            print(f"  Intl Phone:     {biz.international_phone}")
        if biz.website:
            print(f"  Website:        {biz.website}")

    # Status & ratings
    print(f"\n  ⭐ Status & Ratings")
    if biz.business_status:
        print(f"  Status:         {biz.business_status}")
    if biz.rating is not None:
        rating_str = f"{biz.rating}/5"
        if biz.total_ratings:
            rating_str += f" ({biz.total_ratings} reviews)"
        print(f"  Rating:         {rating_str}")
    if biz.price_level:
        print(f"  Price Level:    {biz.price_level}")
    if biz.open_now is not None:
        print(f"  Open Now:       {format_bool(biz.open_now)}")

    # Hours
    if biz.weekday_hours:
        print(f"\n  🕐 Hours")
        for day in biz.weekday_hours:
            print(f"     {day}")

    # Editorial summary
    if biz.editorial_summary:
        print(f"\n  📝 Summary")
        print(f"     {biz.editorial_summary}")

    # Services
    services = {
        "Delivery": biz.delivery,
        "Dine-in": biz.dine_in,
        "Takeout": biz.takeout,
        "Reservable": biz.reservable,
        "Outdoor Seating": biz.outdoor_seating,
        "Live Music": biz.live_music,
        "Good for Children": biz.good_for_children,
        "Good for Groups": biz.good_for_groups,
        "Allows Dogs": biz.allows_dogs,
        "Restroom": biz.restroom,
    }
    active_services = {k: v for k, v in services.items() if v is not None}
    if active_services:
        print(f"\n  🏪 Services & Amenities")
        for name, val in active_services.items():
            print(f"  {name + ':':<20} {format_bool(val)}")

    # Food service
    food = {
        "Breakfast": biz.serves_breakfast,
        "Lunch": biz.serves_lunch,
        "Dinner": biz.serves_dinner,
        "Beer": biz.serves_beer,
        "Wine": biz.serves_wine,
        "Cocktails": biz.serves_cocktails,
        "Coffee": biz.serves_coffee,
    }
    active_food = {k: v for k, v in food.items() if v is not None}
    if active_food:
        print(f"\n  🍽️  Food & Drinks")
        for name, val in active_food.items():
            print(f"  {name + ':':<20} {format_bool(val)}")

    # Payment
    payment = {
        "Credit Cards": biz.accepts_credit_cards,
        "Debit Cards": biz.accepts_debit_cards,
        "Cash": biz.accepts_cash,
        "NFC/Contactless": biz.accepts_nfc,
    }
    active_payment = {k: v for k, v in payment.items() if v is not None}
    if active_payment:
        print(f"\n  💳 Payment Options")
        for name, val in active_payment.items():
            print(f"  {name + ':':<20} {format_bool(val)}")

    # Accessibility
    access = {
        "Wheelchair Entrance": biz.wheelchair_accessible_entrance,
        "Wheelchair Parking": biz.wheelchair_accessible_parking,
        "Wheelchair Restroom": biz.wheelchair_accessible_restroom,
        "Wheelchair Seating": biz.wheelchair_accessible_seating,
    }
    active_access = {k: v for k, v in access.items() if v is not None}
    if active_access:
        print(f"\n  ♿ Accessibility")
        for name, val in active_access.items():
            print(f"  {name + ':':<20} {format_bool(val)}")

    # Photos & reviews
    if biz.photo_count or biz.review_count:
        print(f"\n  📸 Media")
        print(f"  Photos:         {biz.photo_count}")
        print(f"  Reviews:        {biz.review_count}")


def print_summary_table(businesses) -> None:
    """Print a summary table of all businesses found."""
    print(f"{'#':<4} {'Place ID':<30} {'Name':<30} {'Type':<20} {'Address':<45} {'Phone':<16} {'Status':<12} {'Rating':<7} {'Reviews'}")
    print(f"{'—'*3:<4} {'—'*28:<30} {'—'*28:<30} {'—'*18:<20} {'—'*43:<45} {'—'*14:<16} {'—'*10:<12} {'—'*5:<7} {'—'*7}")

    for i, biz in enumerate(businesses, start=1):
        rating_str = f"{biz.rating}" if biz.rating else "—"
        reviews_str = str(biz.total_ratings) if biz.total_ratings else "—"
        type_str = (biz.primary_type_display or biz.primary_type or "—")[:18]
        name_str = biz.name[:28]
        addr_str = biz.address[:43]
        phone_str = (biz.phone or "—")[:14]
        status_str = (biz.business_status or "—")[:10]
        place_id_str = biz.place_id[:28]

        print(f"{i:<4} {place_id_str:<30} {name_str:<30} {type_str:<20} {addr_str:<45} {phone_str:<16} {status_str:<12} {rating_str:<7} {reviews_str}")


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Find businesses at an address or search by name using Google Places API.",
        epilog="""
Examples:
  python places_app.py --address "40 Pacifica" --city "Irvine" --zipcode "92618"
  python places_app.py --business-name "Cotality" --city "Irvine"
  python places_app.py "40 Pacifica, Irvine, CA 92618"
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--address", "-a", type=str, help="Street address line (e.g., '40 Pacifica')")
    parser.add_argument("--city", "-c", type=str, help="City name (e.g., 'Irvine')")
    parser.add_argument("--zipcode", "-z", type=str, help="ZIP/postal code (e.g., '92618')")
    parser.add_argument("--business-name", "-b", type=str, help="Business name to search for (e.g., 'Cotality')")
    parser.add_argument("query", nargs="*", type=str, help="Free-form search query (positional)")
    return parser.parse_args()


def build_query(args) -> tuple:
    """Build search query and mode from parsed arguments.

    Returns:
        (query_string, mode, description) where mode is 'address' or 'name',
        and description is a human-readable summary of the search filters.
    """
    # If --business-name is provided, search by name
    if args.business_name:
        parts = [args.business_name]
        filters = []
        if args.address:
            parts.append(args.address)
            filters.append(f"address: {args.address}")
        if args.city:
            parts.append(args.city)
            filters.append(f"city: {args.city}")
        if args.zipcode:
            parts.append(args.zipcode)
            filters.append(f"zipcode: {args.zipcode}")

        desc = f"business name '{args.business_name}' (case-insensitive)"
        if filters:
            desc += f" in {', '.join(filters)}"
        return " ".join(parts), "name", desc

    # Otherwise, build an address query
    parts = []
    if args.address:
        parts.append(args.address)
    if args.city:
        parts.append(args.city)
    if args.zipcode:
        parts.append(args.zipcode)

    # Fall back to positional args (legacy usage: places_app.py "40 Pacifica, Irvine")
    if not parts and args.query:
        query = " ".join(args.query)
        return query, "address", query

    if parts:
        query = ", ".join(parts)
        return query, "address", query

    return "", "address", ""


def main() -> None:
    load_dotenv()

    api_key = os.getenv("GOOGLE_PLACES_API_KEY")
    if not api_key or api_key == "your-api-key-here":
        print("\nError: GOOGLE_PLACES_API_KEY not set.")
        print("Copy .env.example to .env and add your API key.")
        print("See README.md for setup instructions.\n")
        sys.exit(1)

    args = parse_args()
    query, mode, description = build_query(args)

    # If no arguments at all, prompt interactively
    if not query:
        query = input("\nEnter an address or business name to search: ").strip()
        if not query:
            print("\nError: A search query is required.\n")
            sys.exit(1)
        mode = "address"
        description = query

    if mode == "name":
        print(f"\nSearching for: {description}\n")
    else:
        print(f"\nSearching for businesses at: {description}\n")

    try:
        if mode == "name":
            businesses = search_by_name(query, api_key)
        else:
            businesses = search_businesses(query, api_key)
    except PlacesAPIError as e:
        print(f"Error: {e.message}\n")
        if e.status_code == 403:
            print("Troubleshooting tips:")
            print("  - Is the Places API (New) enabled in your GCP project?")
            print("  - Is billing enabled on your project?")
            print("  - Does your API key have the correct restrictions?\n")
        sys.exit(1)

    # Post-filter: Google Text Search uses parameters as hints, not strict filters.
    # We filter client-side to ensure results match the location constraints.
    total_before_filter = len(businesses)
    if businesses:
        if args.address:
            businesses = [b for b in businesses if args.address.lower() in b.address.lower()]
        if args.zipcode:
            businesses = [b for b in businesses if args.zipcode in b.address]
        if args.city:
            businesses = [b for b in businesses if args.city.lower() in b.address.lower()]
        if total_before_filter != len(businesses):
            print(f"  (Filtered from {total_before_filter} to {len(businesses)} results matching location)\n")

    if not businesses:
        print("No businesses found.\n")
        return

    print(f"Found {len(businesses)} business(es):\n")
    print_summary_table(businesses)

    # Interactive detail selection loop
    while True:
        print()
        choice = input("Choose a business to print details (1-{}, or 'q' to quit): ".format(len(businesses))).strip()

        if choice.lower() in ("q", "quit", "exit", ""):
            break

        try:
            index = int(choice)
            if 1 <= index <= len(businesses):
                print_business_details(index, businesses[index - 1])
            else:
                print(f"  Please enter a number between 1 and {len(businesses)}.")
        except ValueError:
            print("  Invalid input. Enter a number or 'q' to quit.")

    print("\nDone.\n")


if __name__ == "__main__":
    main()
