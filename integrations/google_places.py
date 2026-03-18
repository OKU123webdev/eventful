import googlemaps
from os import environ as env
from vendors.vendor_keywords import EVENT_KEYWORDS
from urllib.parse import quote

# initalise client
gmaps = googlemaps.Client(key=env.get("GOOGLE_MAPS_API_KEY"))

# get location data from saved place id
def get_location_data(place_id):
    try:
        place_details = gmaps.place(place_id=place_id, fields=["geometry"])
        if place_details.get("status") == "OK":
            location = place_details["result"]["geometry"]["location"]
            return location["lat"], location["lng"]
        else:
            print("Error fetching place details:", place_details.get("status"))
            return None
    except Exception as e:
        print("Exception occurred:", e)
        return None
    
# search nearby vendors based on  vendor type
def search_nearby_vendors(lat, lng, vendor_type, event_type, radius=5000, page_token=None):
    try:
        # get event/vendor keywords
        event_type = event_type.lower()
        vendor_type = vendor_type.lower()
        keyword = EVENT_KEYWORDS.get(event_type, {}).get(vendor_type, vendor_type)

        # Search for nearby vendors in 5km radius
        response = gmaps.places_nearby(
            location=(lat, lng),
            radius=radius,
            keyword=keyword,
            type="establishment",
            page_token=page_token
        )

        # return JSON results
        if response.get("status") == "OK":
            results = (response.get("results", []) or [])[:9]
            next_token = response.get("next_page_token")
        
            # find Google Places image
            for place in results:
                photos = place.get("photos")
                if photos:
                    place["image_url"] = get_place_image(
                        photos[0].get("photo_reference")
                    )
                else:
                    place["image_url"] = None
            return results, next_token
        else:
            print("Error searching nearby vendors:", response.get("status"))
            return []
    # validation error    
    except Exception as e:
        print("Exception occurred while searching nearby vendors:", e)
        return []
    
# get place images
def get_place_image(photo_reference, max_width=400):
    safe_photo_ref = quote(photo_reference, safe="")
    return (
        "https://maps.googleapis.com/maps/api/place/photo"
        f"?maxwidth={max_width}"
        f"&photo_reference={safe_photo_ref}"
        f"&key={env.get('GOOGLE_MAPS_API_KEY')}"
    )

# get detailed vendor info
def get_vendor_details(place_id):
    try:
        place = gmaps.place(place_id=place_id)
        
        if place.get("status") != "OK":
            print(f"Google API Error: {place.get('status')}")
            return None

        result = place.get("result", {})

        # extract photo reference
        photo_ref = result.get("photos", [{}])[0].get("photo_reference") if result.get("photos") else None
        image_url = get_place_image(photo_ref) if photo_ref else None

        # description
        description = (result.get("editorial_summary") or {}).get("overview")

        return {
            "name": result.get("name"),
            "vicinity": result.get("vicinity"),
            "address": result.get("formatted_address"),
            "rating": result.get("rating"),
            "image_url": image_url,
            "website_url": result.get("website"),
            "phone": result.get("international_phone_number"),
            "hours": result.get("opening_hours", {}).get("weekday_text", []),
            "types": result.get("types", []),
            "description": description,
            "reviews": (result.get("reviews") or [])[:4]   
        }

    except Exception as e:
        print("Error fetching vendor details:", e)
        return None

