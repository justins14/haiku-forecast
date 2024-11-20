from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from .haiku_selector import HaikuSelector
from .weather_service import WeatherService
from .utils import limiter, cache, CACHE_TIMES
from typing import Optional, List
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
import httpx
from datetime import datetime
import asyncio

app = FastAPI(title="Haiku Forecast API")

# Add rate limiter to app
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
haiku_selector = HaikuSelector()
weather_service = WeatherService()

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return HTTPException(
        status_code=429,
        detail="Too many requests. Please try again later."
    )

@app.get("/api/locations/search")
@limiter.limit("5/minute")
async def search_locations(
    request: Request,
    query: str = Query(..., min_length=2),
    limit: int = Query(default=5, le=10)
) -> List[dict]:
    """
    Search for locations using OpenStreetMap Nominatim.
    Returns a list of matching cities.
    """
    if not query:
        return []
    
    # Check cache first
    cache_key = f"location_search:{query.lower()}"
    cached_results = await cache.get(cache_key)
    if cached_results is not None:
        return cached_results
        
    try:
        # Try multiple search strategies
        locations = []
        
        # Strategy 1: Direct search
        params = {
            "q": query,
            "format": "json",
            "limit": limit * 2,  # Get more results to filter
            "addressdetails": 1,
            "accept-language": "en",
            "featuretype": "city"  # Focus on cities
        }
        
        # Strategy 2: Search with wildcard
        params_wildcard = {
            "q": f"{query}*",  # Add wildcard
            "format": "json",
            "limit": limit * 2,
            "addressdetails": 1,
            "accept-language": "en",
            "featuretype": "city"
        }
        
        async with httpx.AsyncClient() as client:
            # Make both requests concurrently
            responses = await asyncio.gather(
                client.get(
                    "https://nominatim.openstreetmap.org/search",
                    params=params,
                    headers={"User-Agent": "HaikuForecast/1.0"}
                ),
                client.get(
                    "https://nominatim.openstreetmap.org/search",
                    params=params_wildcard,
                    headers={"User-Agent": "HaikuForecast/1.0"}
                )
            )
            
            # Combine and process results
            all_results = []
            for response in responses:
                response.raise_for_status()
                all_results.extend(response.json())
            
            # Track seen locations to avoid duplicates
            seen_locations = set()
            
            for result in all_results:
                # Get the city/town/village name
                place_name = None
                for place_type in ["city", "town", "village", "municipality"]:
                    if place_type in result["address"]:
                        place_name = result["address"][place_type]
                        break
                
                if not place_name:
                    continue
                
                state = result["address"].get("state", "")
                country = result["address"].get("country", "")
                
                # Build location string
                location = f"{place_name}"
                if state:
                    location += f", {state}"
                if country:
                    location += f", {country}"
                
                # Skip if we've seen this location
                if location in seen_locations:
                    continue
                seen_locations.add(location)
                
                # Check if the location name contains our search query
                if (query.lower() in place_name.lower() or 
                    query.lower() in location.lower()):
                    locations.append({
                        "display_name": location,
                        "lat": float(result["lat"]),
                        "lon": float(result["lon"])
                    })
            
            # Sort results by relevance
            # Places that start with the query come first
            locations.sort(key=lambda x: (
                not x["display_name"].lower().startswith(query.lower()),
                len(x["display_name"])
            ))
            
            # Limit final results
            locations = locations[:limit]
            
            # Cache the results
            await cache.set(
                cache_key,
                locations,
                expire=int(CACHE_TIMES['location_search'].total_seconds())
            )
            
            return locations
            
    except Exception as e:
        print(f"Error searching locations: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error searching locations"
        )

@app.get("/api/haikus")
@limiter.limit("30/minute")
async def get_haikus(
    request: Request,
    location: str = "New York"
):
    """Get haikus matching the weather conditions for both today and tomorrow."""
    
    # Check cache
    cache_key = f"haikus:{location}"
    cached_result = await cache.get(cache_key)
    if cached_result is not None:
        return cached_result
    
    # Get weather for both days
    today_forecast = await weather_service.get_weather_for_location(location, "today")
    tomorrow_forecast = await weather_service.get_weather_for_location(location, "tomorrow")
    
    if not today_forecast or not tomorrow_forecast:
        raise HTTPException(
            status_code=404,
            detail="Location not found or weather data unavailable"
        )
    
    # Process both days
    today_conditions = weather_service.weather_to_tags(today_forecast)
    tomorrow_conditions = weather_service.weather_to_tags(tomorrow_forecast)
    
    today_haiku = haiku_selector.select_haiku(today_conditions)
    tomorrow_haiku = haiku_selector.select_haiku(tomorrow_conditions)
    
    result = {
        "today": {
            "text": today_haiku["text"],
            "conditions": today_conditions,
            "forecast": {
                "morning": {
                    "temperature": today_forecast.morning.temperature,
                    "condition": weather_service._weather_code_to_condition(today_forecast.morning.weather_code)
                },
                "afternoon": {
                    "temperature": today_forecast.afternoon.temperature,
                    "condition": weather_service._weather_code_to_condition(today_forecast.afternoon.weather_code)
                },
                "evening": {
                    "temperature": today_forecast.evening.temperature,
                    "condition": weather_service._weather_code_to_condition(today_forecast.evening.weather_code)
                }
            }
        },
        "tomorrow": {
            "text": tomorrow_haiku["text"],
            "conditions": tomorrow_conditions,
            "forecast": {
                "morning": {
                    "temperature": tomorrow_forecast.morning.temperature,
                    "condition": weather_service._weather_code_to_condition(tomorrow_forecast.morning.weather_code)
                },
                "afternoon": {
                    "temperature": tomorrow_forecast.afternoon.temperature,
                    "condition": weather_service._weather_code_to_condition(tomorrow_forecast.afternoon.weather_code)
                },
                "evening": {
                    "temperature": tomorrow_forecast.evening.temperature,
                    "condition": weather_service._weather_code_to_condition(tomorrow_forecast.evening.weather_code)
                }
            }
        }
    }
    
    # Cache the result
    await cache.set(
        cache_key,
        result,
        expire=int(CACHE_TIMES['weather'].total_seconds())
    )
    
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 