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
        
        # Remove today's haiku from tomorrow's options if possible
        if today_haiku in tomorrow_best and len(tomorrow_best) > 1:
            tomorrow_best.remove(today_haiku)
        
        # Select tomorrow's haiku
        tomorrow_haiku = random.choice(tomorrow_best)
        
        return today_haiku, tomorrow_haiku

    def _get_scored_haikus(self, conditions: Dict[str, List[str]]) -> List[Tuple[int, Dict]]:
        """Helper method to get and score matching haikus"""
        # Collect all time-specific tags
        specific_tags = (
            conditions["morning"] +
            conditions["afternoon"] +
            conditions["evening"]
        )
        
        # Add seasonal tags from general conditions
        seasonal_tags = [tag for tag in conditions["general"] 
                        if tag in {"spring", "summer", "autumn", "winter"}]
        specific_tags.extend(seasonal_tags)
        
        # Get general weather tags (non-seasonal)
        general_tags = [tag for tag in conditions["general"] 
                       if tag not in {"spring", "summer", "autumn", "winter"}]
        
        # Get all potential matching haikus
        all_matching_haikus = self.haiku_manager.get_haikus_by_tags(specific_tags + general_tags)
        
        # Score each haiku based on matches
        scored_haikus = []
        for haiku in all_matching_haikus:
            haiku_tags = set(haiku["tags"])
            
            # Count specific matches (time-based and seasonal)
            specific_matches = len([tag for tag in specific_tags if tag in haiku_tags])
            
            # Count general matches
            general_matches = len([tag for tag in general_tags if tag in haiku_tags])
            
            # Score calculation: specific matches are weighted more heavily
            score = (specific_matches * 2) + general_matches
            
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