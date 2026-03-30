from datetime import datetime
from zoneinfo import ZoneInfo
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder
from tools.base import Tool
import ssl
import certifi
import json

ssl_context = ssl.create_default_context(cafile=certifi.where())


class TimeTool(Tool):
    def __init__(self):
        # Initialize once (important for performance)
        self.geolocator = Nominatim(
            user_agent="chat_cli_tool",
            ssl_context=ssl_context
        )  
        self.tf = TimezoneFinder()

        # Simple in-memory cache
        self.cache = {}

    def name(self):
        return "get_current_time"

    def description(self):
        return "Returns the current time at a given location (e.g., London, Berlin, New York)"

    def parameters(self):
        return {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "Name of the location (e.g., London, Berlin, New York)"
                }
            },
            "required": ["location"]
        }

    def execute(self, arguments):
        city = arguments.get("location", "").strip()

        if not city:
            return "ERROR: 'city' argument is required"

        city_key = city.lower()

        # --- Cache lookup ---
        if city_key in self.cache:
            tz_name = self.cache[city_key]
        else:
            # --- Step 1: Geocode city -> coordinates ---
            try:
                location = self.geolocator.geocode(city)
            except Exception as e:
                return f"ERROR: Geocoding failed: {e}"

            if not location:
                return f"ERROR: Could not find location '{city}'"

            # --- Step 2: Coordinates -> timezone ---
            try:
                tz_name = self.tf.timezone_at(
                    lat=location.latitude,
                    lng=location.longitude
                )
            except Exception as e:
                return f"ERROR: Timezone lookup failed: {e}"

            if not tz_name:
                return f"ERROR: Could not determine timezone for '{city}'"

            # Save in cache
            self.cache[city_key] = tz_name

        # --- Step 3: Get current time ---
        try:
            now = datetime.now(ZoneInfo(tz_name))
        except Exception as e:
            return f"ERROR: Failed to get time: {e}"

        return f"Current time in {city.title()} is {now.strftime('%Y-%m-%d %H:%M:%S')}"

    def format_call(self, arguments, result):
        input = arguments.get("location", "").strip()
        if not input:
            input=json.dumps(arguments, indent=4)   
        return self.create_tool_call_string(input, result)    