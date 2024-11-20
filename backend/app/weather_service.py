from datetime import datetime, timedelta
import httpx
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass

@dataclass
class WeatherConditions:
    temperature: float
    weather_code: int
    is_day: int
    humidity: float
    wind_speed: float
    time: datetime

@dataclass
class DailyForecast:
    morning: WeatherConditions
    afternoon: WeatherConditions
    evening: WeatherConditions
    date: datetime

class WeatherService:
    BASE_URL = "https://api.open-meteo.com/v1/forecast"
    GEOCODING_URL = "https://nominatim.openstreetmap.org/search"
    TIME_PERIODS = {
        "morning": 9,    # 9 AM
        "afternoon": 14, # 2 PM
        "evening": 19,   # 7 PM
    }
    
    def __init__(self):
        self.client = httpx.AsyncClient()
        self._weather_cache = {}
        self._cache_expiry = {}
    
    async def get_coordinates(self, location: str) -> Optional[Tuple[float, float]]:
        """Get coordinates for a location using OpenStreetMap Nominatim API."""
        try:
            params = {
                "q": location,
                "format": "json",
                "limit": 1
            }
            response = await self.client.get(self.GEOCODING_URL, params=params)
            response.raise_for_status()
            results = response.json()
            
            if results:
                return float(results[0]["lat"]), float(results[0]["lon"])
            return None
        except Exception as e:
            print(f"Error getting coordinates: {e}")
            return None

    async def get_weather_for_location(self, location: str, day: str) -> Optional[DailyForecast]:
        """Get weather forecast for a location by name."""
        coords = await self.get_coordinates(location)
        if not coords:
            return None
        return await self.get_weather(coords[0], coords[1], day)

    async def get_weather(self, latitude: float, longitude: float, day: str) -> Optional[DailyForecast]:
        """
        Get weather for a specific location and day.
        day can be 'today' or 'tomorrow'
        """
        cache_key = f"{latitude},{longitude},{day}"
        if self._is_cache_valid(cache_key):
            return self._weather_cache[cache_key]

        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": [
                "temperature_2m",
                "weathercode",
                "is_day",
                "relativehumidity_2m",
                "windspeed_10m"
            ],
            "timezone": "auto"
        }

        try:
            response = await self.client.get(self.BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()
            
            forecast = self._process_weather_data(data, day)
            self._cache_result(cache_key, forecast)
            
            return forecast
        except Exception as e:
            print(f"Error fetching weather: {e}")
            return None

    def _process_weather_data(self, data: Dict, day: str) -> DailyForecast:
        """Process the API response and return weather conditions for different times of day."""
        base_date = datetime.now()
        if day == "tomorrow":
            base_date += timedelta(days=1)
        
        # Calculate the index offset based on the day
        day_offset = 24 if day == "tomorrow" else 0
        
        # Get weather for each time period
        morning = WeatherConditions(
            temperature=data["hourly"]["temperature_2m"][day_offset + self.TIME_PERIODS["morning"]],
            weather_code=data["hourly"]["weathercode"][day_offset + self.TIME_PERIODS["morning"]],
            is_day=data["hourly"]["is_day"][day_offset + self.TIME_PERIODS["morning"]],
            humidity=data["hourly"]["relativehumidity_2m"][day_offset + self.TIME_PERIODS["morning"]],
            wind_speed=data["hourly"]["windspeed_10m"][day_offset + self.TIME_PERIODS["morning"]],
            time=base_date.replace(hour=self.TIME_PERIODS["morning"])
        )
        
        afternoon = WeatherConditions(
            temperature=data["hourly"]["temperature_2m"][day_offset + self.TIME_PERIODS["afternoon"]],
            weather_code=data["hourly"]["weathercode"][day_offset + self.TIME_PERIODS["afternoon"]],
            is_day=data["hourly"]["is_day"][day_offset + self.TIME_PERIODS["afternoon"]],
            humidity=data["hourly"]["relativehumidity_2m"][day_offset + self.TIME_PERIODS["afternoon"]],
            wind_speed=data["hourly"]["windspeed_10m"][day_offset + self.TIME_PERIODS["afternoon"]],
            time=base_date.replace(hour=self.TIME_PERIODS["afternoon"])
        )
        
        evening = WeatherConditions(
            temperature=data["hourly"]["temperature_2m"][day_offset + self.TIME_PERIODS["evening"]],
            weather_code=data["hourly"]["weathercode"][day_offset + self.TIME_PERIODS["evening"]],
            is_day=data["hourly"]["is_day"][day_offset + self.TIME_PERIODS["evening"]],
            humidity=data["hourly"]["relativehumidity_2m"][day_offset + self.TIME_PERIODS["evening"]],
            wind_speed=data["hourly"]["windspeed_10m"][day_offset + self.TIME_PERIODS["evening"]],
            time=base_date.replace(hour=self.TIME_PERIODS["evening"])
        )
        
        return DailyForecast(morning=morning, afternoon=afternoon, evening=evening, date=base_date)

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached weather data is still valid (less than 1 hour old)."""
        if cache_key not in self._cache_expiry:
            return False
        return datetime.now() < self._cache_expiry[cache_key]

    def _cache_result(self, cache_key: str, forecast: DailyForecast):
        """Cache weather results with a 1-hour expiry."""
        self._weather_cache[cache_key] = forecast
        self._cache_expiry[cache_key] = datetime.now() + timedelta(hours=1)

    def weather_to_tags(self, forecast: DailyForecast) -> Dict[str, List[str]]:
        """Convert weather conditions to detailed tags for haiku selection."""
        conditions = {
            "morning": [],
            "afternoon": [],
            "evening": [],
            "general": []
        }
        
        # Process each time period
        conditions["morning"].extend(self._get_period_tags(forecast.morning, "morning"))
        conditions["afternoon"].extend(self._get_period_tags(forecast.afternoon, "afternoon"))
        conditions["evening"].extend(self._get_period_tags(forecast.evening, "evening"))
        
        # Add season
        season = self._get_season(forecast.date)
        conditions["general"].append(season)
        
        # Add overall temperature trend
        avg_temp = (forecast.morning.temperature + 
                   forecast.afternoon.temperature + 
                   forecast.evening.temperature) / 3
        conditions["general"].append(self._get_temperature_tag(avg_temp))
        
        return conditions
    
    def _get_period_tags(self, weather: WeatherConditions, period: str) -> List[str]:
        """Get weather tags for a specific time period."""
        tags = []
        
        # Add basic weather condition
        condition = self._weather_code_to_condition(weather.weather_code)
        tags.append(f"{condition}-{period}")
        
        # Add temperature for this period
        temp_tag = self._get_temperature_tag(weather.temperature)
        tags.append(f"{temp_tag}-{period}")
        
        # Add humidity condition based on actual humidity
        if weather.humidity >= 80:
            tags.append(f"humid-{period}")
        
        # Add wind conditions based on wind speed
        # Using Beaufort scale as reference:
        # > 29 km/h (8 m/s) for gusty
        # > 19 km/h (5.5 m/s) for breezy
        if weather.wind_speed >= 8:
            tags.append(f"gusty-{period}")
        elif weather.wind_speed >= 5.5:
            tags.append(f"breezy-{period}")
        
        return tags
    
    def _weather_code_to_condition(self, code: int) -> str:
        """Map WMO weather codes to simple conditions."""
        if code == 0:
            return "clear"
        elif code == 1:
            return "mostly-clear"
        elif code == 2:
            return "partly-cloudy"
        elif code == 3:
            return "overcast"
        elif code == 45:
            return "foggy"  # Dense fog
        elif code == 48:
            return "misty"  # Depositing rime fog
        elif code == 51:
            return "drizzle"
        elif code in (53, 55):
            return "rainy"
        elif code in (56, 57):
            return "freezing-rain"
        elif code in (61, 63, 65):
            return "rainy"
        elif code in (66, 67):
            return "freezing-rain"
        elif code in (71, 73, 75):
            return "snowy"
        elif code == 77:
            return "hail"
        elif code in (80, 81, 82):
            return "rainy"
        elif code in (85, 86):
            return "snowy"
        elif code == 95:
            return "stormy"
        elif code in (96, 99):
            return "stormy-hail"
        else:
            return "clear"
    
    def _get_temperature_tag(self, temp: float) -> str:
        """Get temperature condition tag."""
        if temp < 0:
            return "freezing"
        elif temp < 5:
            return "frosty"
        elif temp < 9:
            return "cold"
        elif temp < 15:
            return "cool"
        elif temp < 20:
            return "mild"
        elif temp < 27:
            return "warm"
        else:
            return "hot"
    
    def _get_season(self, date: datetime) -> str:
        """Determine season based on date."""
        month = date.month
        if month in (3, 4, 5):
            return "spring"
        elif month in (6, 7, 8):
            return "summer"
        elif month in (9, 10, 11):
            return "autumn"
        else:
            return "winter"