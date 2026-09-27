# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
from zoneinfo import ZoneInfo

from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.manager import A2uiSchemaManager
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.tools import ToolContext
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.genai import types

from app.a2ui_utils import a2ui_callback





def get_weather(query: str) -> str:
    """Simulates a web search. Use it get information on weather.

    Args:
        query: A string containing the location to get weather information for.

    Returns:
        A string with the simulated weather information for the queried location.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        return "It's 60 degrees and foggy."
    return "It's 90 degrees and sunny."


def get_current_time(query: str) -> str:
    """Simulates getting the current time for a city.

    Args:
        city: The name of the city to get the current time for.

    Returns:
        A string with the current time information.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        tz_identifier = "America/Los_Angeles"
    else:
        return f"Sorry, I don't have timezone information for query: {query}."

    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    return f"The current time for query {query} is {now.strftime('%Y-%m-%d %H:%M:%S %Z%z')}"


def search_budget_hostels(city: str, max_price_usd: float = 30.0, room_type: str = "dorm") -> list[dict]:
    """Searches for budget hostels matching destination city, price limit, and room type.

    Args:
        city: Destination city name (e.g., 'Bangkok', 'Tokyo', 'Berlin').
        max_price_usd: Maximum nightly budget in USD.
        room_type: Accommodation type, e.g. 'dorm' or 'private'.

    Returns:
        List of matching hostel options with name, price, rating, and key perks.
    """
    sample_hostels = [
        {
            "name": f"The Social Hub {city}",
            "city": city,
            "price_per_night_usd": min(max_price_usd, 18.0),
            "room_type": room_type,
            "rating": 4.8,
            "perks": ["Free Breakfast", "Guest Kitchen", "Central Location"],
        },
        {
            "name": f"Backpacker Haven {city}",
            "city": city,
            "price_per_night_usd": min(max_price_usd, 22.0),
            "room_type": room_type,
            "rating": 4.6,
            "perks": ["Free Walking Tours", "High-speed WiFi", "Rooftop Terrace"],
        },
    ]
    return [h for h in sample_hostels if h["price_per_night_usd"] <= max_price_usd]


def convert_currency(amount: float, from_currency: str = "USD", to_currency: str = "EUR") -> dict:
    """Converts a monetary amount between currencies using real-time exchange rates.

    Args:
        amount: The monetary amount to convert.
        from_currency: 3-letter source currency code (e.g., 'USD', 'EUR', 'GBP').
        to_currency: 3-letter target currency code (e.g., 'EUR', 'THB', 'JPY').

    Returns:
        Dict containing original amount, base currency, target currency, converted amount, and exchange rate date.
    """
    import json
    import os
    import urllib.request

    api_key = os.getenv("EXCHANGE_RATE_API_KEY")
    url = f"https://api.frankfurter.app/latest?amount={amount}&from={from_currency.upper()}&to={to_currency.upper()}"
    headers = {"User-Agent": "BackpackBuddy/1.0"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
        converted_val = data.get("rates", {}).get(to_currency.upper())
        return {
            "amount": amount,
            "from_currency": from_currency.upper(),
            "to_currency": to_currency.upper(),
            "converted_amount": converted_val,
            "date": data.get("date"),
        }
    except Exception as e:
        return {
            "error": f"Failed to fetch exchange rate: {e}",
            "amount": amount,
            "from_currency": from_currency.upper(),
            "to_currency": to_currency.upper(),
        }


def geocode_address(address: str) -> dict:
    """Turns an address or location name into geographic coordinates (latitude and longitude).

    Args:
        address: The address or location name to geocode (e.g., 'Eiffel Tower', 'Bangkok, Thailand').

    Returns:
        Dict containing name, formatted address, and location coordinates (latitude and longitude).
    """
    import json
    import os
    import urllib.parse
    import urllib.request

    api_key = os.getenv("GOOGLE_MAPS_API_KEY", "")
    encoded_addr = urllib.parse.quote(address)
    geo_url = f"https://maps.googleapis.com/maps/api/geocode/json?address={encoded_addr}&key={api_key}"
    headers = {"User-Agent": "BackpackBuddy/1.0"}

    try:
        req = urllib.request.Request(geo_url, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
        if data.get("status") == "OK" and data.get("results"):
            res = data["results"][0]
            loc = res["geometry"]["location"]
            return {
                "name": address,
                "address": res.get("formatted_address", address),
                "location": {"latitude": loc["lat"], "longitude": loc["lng"]},
            }
    except Exception:
        pass

    try:
        import google.auth
        import google.auth.transport.requests

        credentials, project = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        credentials.refresh(google.auth.transport.requests.Request())
        places_url = "https://places.googleapis.com/v1/places:searchText"
        payload = {"textQuery": address, "pageSize": 1}
        p_headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {credentials.token}",
            "X-Goog-User-Project": project,
            "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location",
        }
        req2 = urllib.request.Request(places_url, data=json.dumps(payload).encode("utf-8"), headers=p_headers, method="POST")
        with urllib.request.urlopen(req2, timeout=5) as resp2:
            data2 = json.loads(resp2.read().decode())
        if data2.get("places"):
            place = data2["places"][0]
            return {
                "name": place.get("displayName", {}).get("text", address),
                "address": place.get("formattedAddress", address),
                "location": place.get("location", {}),
            }
    except Exception as err:
        return {"error": f"Failed to geocode address: {err}", "address": address}

    return {"error": "Address not found", "address": address}


def find_nearby_places(latitude: float, longitude: float, place_type: str = "tourist_attraction", radius_meters: float = 2000.0) -> list[dict]:
    """Finds nearby places of a given type (e.g. 'tourist_attraction', 'restaurant', 'bakery') using Places API (New).

    Args:
        latitude: Latitude coordinate.
        longitude: Longitude coordinate.
        place_type: Type of place to search for (e.g., 'tourist_attraction', 'restaurant', 'hostel').
        radius_meters: Search radius in meters (default 2000.0).

    Returns:
        List of nearby place dicts containing name, address, and location.
    """
    import json
    import os
    import urllib.request

    api_key = os.getenv("GOOGLE_MAPS_API_KEY", "")
    places_url = "https://places.googleapis.com/v1/places:searchNearby"
    payload = {
        "includedTypes": [place_type],
        "maxResultCount": 5,
        "locationRestriction": {
            "circle": {
                "center": {"latitude": latitude, "longitude": longitude},
                "radius": radius_meters,
            }
        },
    }
    p_headers = {
        "Content-Type": "application/json",
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location",
    }
    if api_key:
        p_headers["X-Goog-Api-Key"] = api_key

    try:
        req = urllib.request.Request(places_url, data=json.dumps(payload).encode("utf-8"), headers=p_headers, method="POST")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
    except Exception:
        try:
            import google.auth
            import google.auth.transport.requests

            credentials, project = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
            credentials.refresh(google.auth.transport.requests.Request())
            p_headers["Authorization"] = f"Bearer {credentials.token}"
            p_headers["X-Goog-User-Project"] = project
            if "X-Goog-Api-Key" in p_headers:
                del p_headers["X-Goog-Api-Key"]

            req2 = urllib.request.Request(places_url, data=json.dumps(payload).encode("utf-8"), headers=p_headers, method="POST")
            with urllib.request.urlopen(req2, timeout=5) as resp2:
                data = json.loads(resp2.read().decode())
        except Exception as e:
            return [{"error": f"Places API call failed: {e}"}]

    results = []
    for place in data.get("places", []):
        results.append({
            "name": place.get("displayName", {}).get("text", "Unknown"),
            "address": place.get("formattedAddress", "N/A"),
            "location": place.get("location", {}),
        })
    return results


def generate_travel_image(prompt: str, tool_context: ToolContext) -> dict:
    """Generates an image for budget travel destinations, hostels, or street food using gemini-3.1-flash-lite-image.

    Args:
        prompt: Description of the travel image to generate (e.g., 'A cozy budget hostel rooftop in Bangkok at sunset').
        tool_context: ADK ToolContext used to save artifacts to the session.

    Returns:
        Dict containing status, artifact_filename, and public Cloud Storage URL.
    """
    import uuid
    from google import genai
    from google.genai import types
    from google.cloud import storage

    bucket_name = "qwiklabs-gcp-02-63b2f55175ee-static-assets-bucket"

    try:
        client = genai.Client(
            vertexai=True,
            project="qwiklabs-gcp-02-63b2f55175ee",
            location="global",
        )
        resp = client.models.generate_content(
            model="gemini-3.1-flash-lite-image",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
            ),
        )

        img_bytes = None
        if resp.candidates and resp.candidates[0].content.parts:
            for part in resp.candidates[0].content.parts:
                if part.inline_data:
                    img_bytes = part.inline_data.data
                    break

        if not img_bytes:
            return {"error": "No image data returned from model"}

        filename = f"travel_{uuid.uuid4().hex[:8]}.jpg"

        # 1. Save artifact to Playground Session Artifacts
        artifact_part = types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg")
        tool_context.save_artifact(filename=filename, artifact=artifact_part)

        # 2. Upload image bytes directly to GCS bucket
        storage_client = storage.Client(project="qwiklabs-gcp-02-63b2f55175ee")
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(filename)
        blob.upload_from_string(img_bytes, content_type="image/jpeg")

        public_url = f"https://storage.googleapis.com/{bucket_name}/{filename}"

        return {
            "status": "success",
            "artifact_filename": filename,
            "public_url": public_url,
        }
    except Exception as e:
        return {"error": f"Image generation failed: {e}"}


def generate_travel_video(prompt: str, tool_context: ToolContext) -> dict:
    """Generates a short video for budget travel destinations, hostels, or street food using Google's Omni model (gemini-omni-flash-preview) in the global region.

    Args:
        prompt: Description of the travel video to generate (e.g., 'A short video clip of a tropical beach hostel rooftop in Thailand').
        tool_context: ADK ToolContext used to save artifacts to the session.

    Returns:
        Dict containing status, artifact_filename, and public Cloud Storage URL.
    """
    import base64
    import uuid
    from google import genai
    from google.genai import types
    from google.cloud import storage

    bucket_name = "qwiklabs-gcp-02-63b2f55175ee-static-assets-bucket"

    try:
        client = genai.Client(
            vertexai=True,
            project="qwiklabs-gcp-02-63b2f55175ee",
            location="global",
        )

        res = client.interactions.create(
            model="gemini-omni-flash-preview",
            input=prompt,
        )

        video_bytes = None
        if hasattr(res, "output_video") and res.output_video and getattr(res.output_video, "data", None):
            raw_data = res.output_video.data
            if isinstance(raw_data, str):
                try:
                    video_bytes = base64.b64decode(raw_data)
                except Exception:
                    video_bytes = raw_data.encode("utf-8")
            else:
                video_bytes = raw_data

        if not video_bytes:
            return {"error": "No video data returned from model"}

        filename = f"video_{uuid.uuid4().hex[:8]}.mp4"

        # 1. Save artifact to Playground Session Artifacts
        artifact_part = types.Part.from_bytes(data=video_bytes, mime_type="video/mp4")
        tool_context.save_artifact(filename=filename, artifact=artifact_part)

        # 2. Upload video bytes directly to GCS bucket
        storage_client = storage.Client(project="qwiklabs-gcp-02-63b2f55175ee")
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(filename)
        blob.upload_from_string(video_bytes, content_type="video/mp4")

        public_url = f"https://storage.googleapis.com/{bucket_name}/{filename}"

        return {
            "status": "success",
            "artifact_filename": filename,
            "public_url": public_url,
        }
    except Exception as e:
        return {"error": f"Video generation failed: {e}"}


async def generate_memories_callback(callback_context: CallbackContext):
    await callback_context.add_session_to_memory()
    return None


schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

a2ui_instruction = schema_manager.generate_system_prompt(
    role_description=(
        "You are BackpackBuddy, a budget travel concierge assistant. "
        "Help backpackers find low-cost hostels, street food, free attractions, "
        "geocode locations, search nearby places, convert currency, generate "
        "travel destination images, and generate short travel videos."
    ),
    workflow_description="Analyze the budget travel request and return structured UI when appropriate.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        "{\"Image\": {\"url\": {\"literalString\": \"https://...\"}}}. Never point an "
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "CRITICAL MEMORY REQUIREMENT: You must remember, extract, and strictly account for "
        "all user allergies (e.g., peanut, shellfish, gluten, dairy), dietary restrictions, "
        "and health preferences across all sessions. Whenever recommending hostels, street food, or "
        "activities, check preloaded memories and ensure options are safe and tailored to the user's allergies. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=a2ui_instruction,
    tools=[
        PreloadMemoryTool(),
        search_budget_hostels,
        convert_currency,
        geocode_address,
        find_nearby_places,
        generate_travel_image,
        generate_travel_video,
        get_weather,
        get_current_time,
    ],
    after_agent_callback=generate_memories_callback,
    after_model_callback=a2ui_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
