import os
import json
import re
import base64
import requests
from pathlib import Path
from dotenv import load_dotenv

import google.generativeai as text_genai

try:
    from google import genai as image_genai
except Exception:
    image_genai = None


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Heavy drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    80: "Slight rain showers",
    81: "Rain showers",
    82: "Heavy rain showers",
    95: "Thunderstorm",
}


def geocode_city(city="Vechta", country="DE"):
    if not city:
        city = "Vechta"

    url = "https://geocoding-api.open-meteo.com/v1/search"

    params = {
        "name": city,
        "count": 1,
        "language": "en",
        "format": "json"
    }

    response = requests.get(url, params=params, timeout=12)
    response.raise_for_status()

    data = response.json()

    if "results" not in data or not data["results"]:
        raise ValueError(f"Location not found: {city}")

    result = data["results"][0]

    return {
        "name": result.get("name", city),
        "country": result.get("country_code", country),
        "latitude": result["latitude"],
        "longitude": result["longitude"],
        "timezone": result.get("timezone", "Europe/Berlin")
    }


def get_weather(city="Vechta", country="DE"):
    location = geocode_city(city, country)

    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": location["latitude"],
        "longitude": location["longitude"],
        "current": (
            "temperature_2m,"
            "apparent_temperature,"
            "relative_humidity_2m,"
            "weather_code,"
            "wind_speed_10m,"
            "precipitation"
        ),
        "hourly": "precipitation_probability",
        "forecast_days": 1,
        "timezone": "auto"
    }

    response = requests.get(url, params=params, timeout=12)
    response.raise_for_status()

    data = response.json()
    current = data.get("current", {})

    probabilities = data.get("hourly", {}).get("precipitation_probability", [])
    rain_chance = max([p for p in probabilities if p is not None] or [0])

    weather_code = current.get("weather_code", 0)

    return {
        "city": location["name"],
        "country": location["country"],
        "temperature": round(current.get("temperature_2m", 0)),
        "feels_like": round(current.get("apparent_temperature", 0)),
        "condition": WEATHER_CODES.get(weather_code, "Unknown weather"),
        "humidity": current.get("relative_humidity_2m", 0),
        "wind_speed": current.get("wind_speed_10m", 0),
        "rain": rain_chance,
        "precipitation": current.get("precipitation", 0),
        "latitude": location["latitude"],
        "longitude": location["longitude"],
    }


def get_today_calendar_events():
    return [
        {"time": "09:00", "title": "Work meeting", "type": "meeting"},
        {"time": "18:00", "title": "Gym", "type": "gym"}
    ]


def clean_gemini_json(text):
    if not text:
        raise ValueError("Gemini returned empty response.")

    cleaned = text.strip()
    cleaned = re.sub(r"^```json", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"^```", "", cleaned).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()

    start = cleaned.find("{")
    end = cleaned.rfind("}")

    if start != -1 and end != -1:
        cleaned = cleaned[start:end + 1]

    return json.loads(cleaned)


def find_first_item_by_category(closet_items, categories):
    for item in closet_items:
        item_category = str(item.get("category", "")).lower().strip()
        item_name = str(item.get("name", "")).strip()

        if item_category in categories and item_name:
            return item_name

    return ""


def fallback_outfit(closet_items):
    top = find_first_item_by_category(closet_items, ["top", "tops", "shirt", "sweater", "hoodie"])
    bottom = find_first_item_by_category(closet_items, ["bottom", "bottoms", "pants", "jeans", "trouser"])
    shoes = find_first_item_by_category(closet_items, ["shoes", "shoe", "sneakers", "boots"])
    extra = find_first_item_by_category(closet_items, ["outerwear", "accessory", "accessories", "jacket", "coat"])

    all_names = [item.get("name", "") for item in closet_items if item.get("name")]

    if not top and all_names:
        top = all_names[0]

    if not bottom and len(all_names) > 1:
        bottom = all_names[1]

    if not shoes and len(all_names) > 2:
        shoes = all_names[2]

    if not extra and len(all_names) > 3:
        extra = all_names[3]

    return {
        "top": top or "Add a top item",
        "bottom": bottom or "Add a bottom item",
        "shoes": shoes or "Add shoes",
        "extra": extra or "Umbrella or jacket recommended"
    }


def build_readable_recommendation(result):
    outfit = result.get("outfit", {})
    reasoning = result.get("reasoning", [])
    advice = result.get("advice", "")

    text = f"""Outfit:
- Top: {outfit.get("top", "Not selected")}
- Bottom: {outfit.get("bottom", "Not selected")}
- Shoes: {outfit.get("shoes", "Not selected")}
- Accessories/Outerwear: {outfit.get("extra", "Not selected")}

Reason:
"""

    for reason in reasoning:
        text += f"- {reason}\n"

    text += f"\nExtra tip:\n{advice}"

    return text


def normalize_scores(scores):
    if not isinstance(scores, dict):
        scores = {}

    def safe_score(value, default=8):
        try:
            number = int(value)
            return max(1, min(10, number))
        except Exception:
            return default

    return {
        "comfort": safe_score(scores.get("comfort", 8)),
        "style": safe_score(scores.get("style", 8)),
        "weather": safe_score(scores.get("weather", 8)),
    }


def normalize_gemini_result(result, weather, events, closet_items):
    if not isinstance(result, dict):
        result = {}

    result.setdefault("title", "Smart Outfit Recommendation")

    if "outfit" not in result or not isinstance(result["outfit"], dict):
        result["outfit"] = {}

    fallback = fallback_outfit(closet_items)

    for key in ["top", "bottom", "shoes", "extra"]:
        value = str(result["outfit"].get(key, "")).strip()

        if (
            not value
            or value.lower() in ["no suitable item found", "not available", "none", "n/a"]
        ):
            result["outfit"][key] = fallback[key]

    result["scores"] = normalize_scores(result.get("scores", {}))

    if "reasoning" not in result or not isinstance(result["reasoning"], list):
        result["reasoning"] = []

    if len(result["reasoning"]) == 0:
        result["reasoning"] = [
            f"The temperature is {weather.get('temperature')}°C, so the outfit is selected for today's weather.",
            f"Your schedule includes {', '.join([event.get('title', 'event') for event in events])}.",
            "The outfit uses items from your saved closet.",
            f"Rain chance is {weather.get('rain')}%, so carrying an umbrella or jacket is useful."
        ]

    result["reasoning"] = result["reasoning"][:4]

    result.setdefault(
        "advice",
        f"Check the weather before leaving. Rain chance is {weather.get('rain')}%."
    )

    result["readable_text"] = build_readable_recommendation(result)

    return result


def generate_outfit_recommendation(weather, events, closet_items):
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is missing. Check your .env file.")

    if not closet_items:
        raise ValueError("Your closet is empty. Please add clothing items first.")

    text_genai.configure(api_key=GEMINI_API_KEY)

    prompt = f"""
You are a professional Morning What-to-Wear Assistant.

Recommend ONE complete outfit for today.

IMPORTANT:
Use ONLY these closet items.
Do not invent clothing names.
If category is missing, choose the closest useful closet item.
Do not write "No suitable item found" unless the closet is completely empty.

Weather:
{json.dumps(weather, indent=2)}

Calendar events:
{json.dumps(events, indent=2)}

Closet items:
{json.dumps(closet_items, indent=2)}

Return ONLY valid JSON in this format:

{{
  "title": "Short stylish outfit title",
  "outfit": {{
    "top": "closet item name",
    "bottom": "closet item name",
    "shoes": "closet item name",
    "extra": "closet item name or practical extra"
  }},
  "scores": {{
    "comfort": 8,
    "style": 8,
    "weather": 8
  }},
  "reasoning": [
    "Weather based reason",
    "Schedule based reason",
    "Closet item based reason",
    "Rain/wind/temperature based reason"
  ],
  "advice": "One short practical advice."
}}
"""

    try:
        model = text_genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)

        parsed_result = clean_gemini_json(response.text)
        final_result = normalize_gemini_result(parsed_result, weather, events, closet_items)

        return final_result

    except Exception as e:
        raise ValueError(f"Gemini API error: {str(e)}")


def generate_real_outfit_image(recommendation):
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is missing.")

    if image_genai is None:
        raise ValueError("google-genai is not installed. Run: python3 -m pip install google-genai pillow")

    outfit = recommendation.get("outfit", {})

    top = outfit.get("top", "a stylish top")
    bottom = outfit.get("bottom", "modern pants")
    shoes = outfit.get("shoes", "clean sneakers")
    extra = outfit.get("extra", "umbrella or jacket")

    prompt = f"""
Create a realistic fashion flat-lay product photo.

Show exactly these outfit items:
1. Top: {top}
2. Bottom: {bottom}
3. Shoes: {shoes}
4. Extra item: {extra}

Visual style:
- real clothing product photography
- soft beige studio background
- clothes arranged horizontally from left to right
- top, bottom, shoes, extra item clearly visible
- premium ecommerce fashion style
- clean shadows
- no person
- no model
- no face
- no text
- no logos
- high quality realistic image
"""

    client = image_genai.Client(api_key=GEMINI_API_KEY)

    response = client.models.generate_content(
        model="gemini-3.1-flash-image",
        contents=[prompt],
    )

    for part in response.parts:
        if getattr(part, "inline_data", None) is not None:
            image_bytes = part.inline_data.data
            encoded = base64.b64encode(image_bytes).decode("utf-8")
            return f"data:image/png;base64,{encoded}"

        try:
            image = part.as_image()
            if image:
                import io
                buffer = io.BytesIO()
                image.save(buffer, format="PNG")
                encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
                return f"data:image/png;base64,{encoded}"
        except Exception:
            pass

    raise ValueError("Gemini did not return an image.")
