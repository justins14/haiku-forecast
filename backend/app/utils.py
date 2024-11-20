from datetime import datetime, timedelta
from typing import Optional, Any, Dict, Tuple
from slowapi import Limiter
from slowapi.util import get_remote_address
import time

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

class SimpleCache:
    def __init__(self, cleanup_interval: int = 3600):
        self._cache: Dict[str, Tuple[Any, datetime]] = {}
        self._last_cleanup = time.time()
        self._cleanup_interval = cleanup_interval  # in seconds
        
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache if it exists and hasn't expired"""
        self._maybe_cleanup()
        
        if key not in self._cache:
            return None
            
        value, expiry = self._cache[key]
        if datetime.now() > expiry:
            del self._cache[key]
            return None
            
        return value
            
    async def set(self, key: str, value: Any, expire: int):
        """Set value in cache with expiration in seconds"""
        self._maybe_cleanup()
        expiry = datetime.now() + timedelta(seconds=expire)
        self._cache[key] = (value, expiry)
            
    async def delete(self, key: str):
        """Delete value from cache"""
        self._cache.pop(key, None)
        
    def _maybe_cleanup(self):
        """Run cleanup if enough time has passed since last cleanup"""
        now = time.time()
        if now - self._last_cleanup > self._cleanup_interval:
            self.clear()
            self._last_cleanup = now
        
    def clear(self):
        """Clear all expired entries"""
        now = datetime.now()
        expired_keys = [
            key for key, (_, expiry) in self._cache.items() 
            if now > expiry
        ]
        for key in expired_keys:
            del self._cache[key]
            
    @property
    def size(self) -> int:
        """Return number of items in cache"""
        return len(self._cache)

# Cache expiration times
CACHE_TIMES = {
    'location_search': timedelta(hours=24),  # Cache location searches for 24 hours
    'coordinates': timedelta(days=7),        # Cache coordinates for 7 days
    'weather': timedelta(minutes=30)         # Cache weather for 30 minutes
}

# Initialize cache with cleanup every hour
cache = SimpleCache(cleanup_interval=3600) 