import json
from integrations.google_places import get_vendor_details

# format API response to dict
def format_vendor_data(vendor):
    return {
        "place_id": vendor.get("place_id"),
        "name": vendor.get("name"),
        "vicinity": vendor.get("vicinity"),
        "rating": vendor.get("rating"),
        "user_ratings_total": vendor.get("user_ratings_total"),
        "price_level": vendor.get("price_level"),
        "types": vendor.get("types", []),
    }

# add additional details for 8 vendors
def attach_place_details(vendors, limit=8) :
    vendor_data: list[dict] = []

    for v in vendors[:limit]:
        details = get_vendor_details(v.get("place_id"))

        # use basic details only if no extra details
        if not details:
            vendor_data.append(format_vendor_data(v))
            continue

        # append additional details
        vendor_data.append({
            **format_vendor_data(v),
            "description": details.get("description"),
            "reviews": [
                {
                    "rating": r.get("rating"),
                    "time": r.get("relative_time_description"),
                    "text": (r.get("text") or "")[:280],
                }
                for r in (details.get("reviews") or [])[:4]
            ],
        })

    # basic details for remaining
    for v in vendors[limit:12]:
        vendor_data.append(format_vendor_data(v))

    return vendor_data

# OPEN AI API CALL
def ai_rank_vendors(client, event_type: str, vendor_type: str, vendors: list[dict], detail_limit: int = 8):
    vendor_data = attach_place_details(vendors, limit=detail_limit)

    # ai prompt
    response = client.responses.create(
        model="gpt-4o-mini",
        input=[
            {
                "role": "developer",
                "content": (
                    "You are an event vendor recommender.\n"
                    "Return ONLY valid JSON. No markdown, no code fences, no extra text.\n"
                    "Use ONLY the provided vendor data. Do NOT invent reviews, prices, or details.\n\n"

                    "IMPORTANT:\n"
                    "- When explaining why a vendor ranks highly, reference specific points from the provided reviews text.\n"
                    "- Summarise common themes from reviews (e.g. staff friendliness, food quality, organisation, atmosphere).\n"
                    "- If quoting or paraphrasing reviews, use only what appears in the provided review text.\n"
                    "- If reviews are limited or vague, explicitly mention that as a risk.\n"
                    "- Avoid generic statements like 'well reviewed' or 'highly rated' without explaining what people liked.\n\n"

                    "Required JSON schema:\n"
                    "{\n"
                    '  \"best_place_id\": \"string\",\n'
                    '  \"ranking\": [\n'
                    '    {\"place_id\": \"string\", \"google_rating\": 0, \"why\": \"string\", \"risks\": \"string\"}\n'
                    "  ],\n"
                    '  \"notes\": \"string\"\n'
                    "}\n\n"

                    "Scoring guidance:\n"
                    "- Prefer higher rating WITH higher user_ratings_total.\n"
                    "- If user_ratings_total is missing, treat rating as less reliable.\n"
                    "- Consider relevance to vendor_type using the `types` field.\n"
                    "- Keep explanations concise but evidence-based.\n"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Event type: {event_type}\n"
                    f"Vendor type needed: {vendor_type}\n"
                    f"Vendors JSON:\n{json.dumps(vendor_data)}"
                ),
            },
        ],
    )

    # get output response
    text = getattr(response, "output_text", None)
    text = (text or "").strip()
    # convert JSON string output to dict
    return json.loads(text)
