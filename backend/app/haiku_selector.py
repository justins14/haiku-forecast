import random
from typing import List, Dict, Set, Tuple
from .haiku_manager import HaikuManager
from datetime import datetime

class HaikuSelector:
    def __init__(self):
        self.haiku_manager = HaikuManager()
        self.error_haiku = {
            "text": ["Nature doesn't err,", "But computers sometimes do,", "We're working on it."],
            "tags": []  # No tags needed for error haiku
        }

    def select_haikus_for_both_days(self, today_conditions: Dict[str, List[str]], 
                                  tomorrow_conditions: Dict[str, List[str]]) -> Tuple[Dict, Dict]:
        """
        Select different haikus for today and tomorrow.
        Returns a tuple of (today's haiku, tomorrow's haiku)
        """
        print(f"Selecting haikus for conditions: Today={today_conditions}, Tomorrow={tomorrow_conditions}")
        
        # Get all potential matching haikus for both days
        today_matches = self._get_scored_haikus(today_conditions)
        tomorrow_matches = self._get_scored_haikus(tomorrow_conditions)
        
        # Get the highest scores
        today_max_score = max(score for score, _ in today_matches) if today_matches else 0
        tomorrow_max_score = max(score for score, _ in tomorrow_matches) if tomorrow_matches else 0
        
        # If either day has no matches, return error haiku for both days
        if today_max_score == 0 or tomorrow_max_score == 0:
            print(f"Warning: No matches found. Today score: {today_max_score}, Tomorrow score: {tomorrow_max_score}")
            return self.error_haiku, self.error_haiku
        
        # Get all haikus with the highest scores
        today_best = [haiku for score, haiku in today_matches if score == today_max_score]
        tomorrow_best = [haiku for score, haiku in tomorrow_matches if score == tomorrow_max_score]
        
        # Select today's haiku first
        today_haiku = random.choice(today_best)
        
        # Create a new list for tomorrow's options, excluding today's haiku
        tomorrow_options = [haiku for haiku in tomorrow_best if haiku["text"] != today_haiku["text"]]
        
        # If we removed all options, use the original list
        if not tomorrow_options:
            print("Warning: No unique options for tomorrow, using different haiku with same score")
            tomorrow_options = [haiku for haiku in tomorrow_best if haiku is not today_haiku]
        
        # If still no options (very rare), use next best score
        if not tomorrow_options:
            print("Warning: Falling back to next best score for tomorrow")
            next_best_score = max(score for score, haiku in tomorrow_matches 
                                if haiku is not today_haiku and score < tomorrow_max_score)
            tomorrow_options = [haiku for score, haiku in tomorrow_matches 
                              if score == next_best_score and haiku is not today_haiku]
        
        # Select tomorrow's haiku from the filtered options
        tomorrow_haiku = random.choice(tomorrow_options)
        
        print(f"Selected haikus: Today='{today_haiku['text'][0]}', Tomorrow='{tomorrow_haiku['text'][0]}'")
        return today_haiku, tomorrow_haiku

    def _get_scored_haikus(self, conditions: Dict[str, List[str]]) -> List[Tuple[int, Dict]]:
        """Helper method to get and score matching haikus"""
        print(f"Scoring haikus for conditions: {conditions}")
        
        morning_tags = set(conditions["morning"])
        afternoon_tags = set(conditions["afternoon"])
        evening_tags = set(conditions["evening"])
        general_tags = set(conditions["general"])
        
        # Get primary weather conditions
        weather_types = {
            'clear', 'partly-cloudy', 'overcast', 'foggy', 'misty',
            'drizzle', 'rainy', 'stormy', 'snowy', 'hail'
        }
        forecast_weather = set()
        for tags in [morning_tags, afternoon_tags, evening_tags, general_tags]:
            for tag in tags:
                base_condition = tag.split('-')[0] if '-' in tag else tag
                if base_condition in weather_types:
                    forecast_weather.add(base_condition)
        
        scored_haikus = []
        for haiku in self.haiku_manager.haikus.values():
            haiku_tags = set(haiku["tags"])
            score = 0
            disqualified = False
            
            # Check for season mismatch
            haiku_season = next((tag for tag in haiku_tags if tag in {"spring", "summer", "autumn", "winter"}), None)
            if haiku_season and haiku_season not in general_tags:
                continue
            
            # Check for weather condition mismatches
            haiku_weather = set()
            for tag in haiku_tags:
                base_condition = tag.split('-')[0] if '-' in tag else tag
                if base_condition in weather_types:
                    haiku_weather.add(base_condition)
            
            # Disqualify if haiku mentions weather not in forecast
            if haiku_weather - forecast_weather:
                continue
            
            # Score matches
            for tag in haiku_tags:
                if '-' in tag:
                    period = tag.split('-')[1]
                    if (period == 'morning' and tag in morning_tags or
                        period == 'afternoon' and tag in afternoon_tags or
                        period == 'evening' and tag in evening_tags):
                        score += 3
                elif tag in general_tags:
                    score += 2
                    if tag in {"spring", "summer", "autumn", "winter"}:
                        score += 1  # Extra point for season match
            
            if score > 0:
                print(f"Haiku scored {score}: {haiku['text'][0]}, tags: {haiku_tags}")
                scored_haikus.append((score, haiku))
        
        return scored_haikus

    # Keep the original select_haiku method for backward compatibility
    def select_haiku(self, conditions: Dict[str, List[str]]) -> Dict:
        """Original method for selecting a single haiku"""
        scored_haikus = self._get_scored_haikus(conditions)
        if not scored_haikus:
            return random.choice(list(self.haiku_manager.haikus.values()))
        
        max_score = max(score for score, _ in scored_haikus)
        best_haikus = [haiku for score, haiku in scored_haikus if score == max_score]
        return random.choice(best_haikus)