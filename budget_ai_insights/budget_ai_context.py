from integrations.google_places import get_vendor_details

# Get Google Places details for vendors with quotes
def vendor_quote_data(interactions, limit=8):
    seen_place_ids = set() # tracking set to avoid duplicates
    results = []

    # loop through interactions
    for v in interactions:

        # skip if no price
        if v.price is None:
            continue

        # check google place id
        place_id = v.vendor_place_id 
        if not place_id or place_id in seen_place_ids:
            continue

        seen_place_ids.add(place_id) # track

        # use vendor interactions as base dictionary
        vendor_data = {
            "place_id": place_id,
            "name": v.vendor_name,
            "vendor_type": v.vendor_type.vendor_type if v.vendor_type else "Unknown",
            "quote_price": float(v.price),
            "is_booked": bool(v.is_booked),
            "is_favourite": bool(v.is_favourite),
        }

        # API request for details
        details = get_vendor_details(place_id)

        # append API results to base dict
        if details:
            results.append({
                **vendor_data,
                "vicinity": details.get("vicinity"),
                "rating": details.get("rating"),
                "user_ratings_total": details.get("user_ratings_total"),
                "price_level": details.get("price_level"),
                "types": details.get("types", []),
                "reviews": [
                    {
                        "rating": r.get("rating"),
                        "time": r.get("relative_time_description"),
                        "text": (r.get("text") or "")[:200],
                    }
                    for r in (details.get("reviews") or [])[:3] # first 3 only
                ],
            })
        else:
            results.append(vendor_data)

        if len(results) >= limit:
            break

    return results