import requests
import os
import threading

MAPS_API_KEY = os.environ.get("MAPS_API_KEY", "")


def geocode_address(address: str) -> tuple:
    """Convert address to lat/lng using Google Maps Geocoding API."""
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": f"{address}, New York City", "key": MAPS_API_KEY}
    resp = requests.get(url, params=params, timeout=3)
    data = resp.json()
    if data.get("status") == "OK":
        loc = data["results"][0]["geometry"]["location"]
        return loc["lat"], loc["lng"]
    raise ValueError(f"Could not geocode: {address}")


def fetch_properties(address: str, preference: str) -> list:
    """Do the actual Maps API call and return raw results."""
    lat, lng = geocode_address(address)
    keyword   = "house for sale" if preference.lower() in ("buy", "purchase", "sale") else "apartment for rent"
    url       = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params    = {"location": f"{lat},{lng}", "radius": 800, "keyword": keyword, "key": MAPS_API_KEY}
    resp      = requests.get(url, params=params, timeout=3)
    return resp.json().get("results", [])[:3]


def send_properties_sms(to_number: str, address: str, preference: str, results: list):
    """Send property suggestions via SMS in the background."""
    try:
        from twilio.rest import Client as TwilioClient
        account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
        auth_token  = os.environ.get("TWILIO_AUTH_TOKEN")
        from_number = os.environ.get("TWILIO_PHONE_NUMBER")

        if not results:
            body = f"Before You Sign: No nearby {preference} listings found near {address}. Try StreetEasy.com for that area."
        else:
            lines = [f"Before You Sign - Nearby {preference.title()} Options near {address}:\n"]
            for i, p in enumerate(results, 1):
                lines.append(f"{i}. {p.get('name','Unknown')} - {p.get('vicinity','')}")
            lines.append("\nCheck StreetEasy.com for full listings.")
            body = "\n".join(lines)

        client = TwilioClient(account_sid, auth_token)
        client.messages.create(
            body=body,
            from_="whatsapp:+14155238886",
            to=f"whatsapp:{to_number}"
        )
        print(f"Property SMS sent to {to_number}")
    except Exception as e:
        print(f"Property SMS error: {e}")


def find_nearby_properties(address: str, preference: str, caller_number: str = "") -> str:
    """
    Instantly returns a voice response, then sends full details via SMS in background.
    This prevents Vapi from timing out.
    """
    pref_label = "buy" if preference.lower() in ("buy", "purchase", "sale") else "rent"

    try:
        results = fetch_properties(address, preference)

        # Send SMS in background — don't block the voice response
        if caller_number:
            thread = threading.Thread(
                target=send_properties_sms,
                args=(caller_number, address, pref_label, results),
                daemon=True
            )
            thread.start()

        if not results:
            return (
                f"I searched nearby but couldn't find active {pref_label} listings right now. "
                "I'm sending you a text with StreetEasy's link for that neighborhood."
            )

        # Speak only the first result — send the rest via SMS
        first = results[0]
        name  = first.get("name", "a property")
        area  = first.get("vicinity", "nearby")
        count = len(results)

        return (
            f"I found {count} nearby options to {pref_label} close to {address}. "
            f"The closest one is {name} at {area}. "
            f"I'm sending all {count} suggestions to your phone right now so you have the details."
        )

    except Exception as e:
        print(f"Property search error: {e}")
        return (
            "I had trouble searching nearby properties right now. "
            "I'd recommend checking StreetEasy or Zillow for that neighborhood."
        )
