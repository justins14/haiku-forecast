import random
from typing import List, Dict, Set
from .haiku_manager import HaikuManager
from datetime import datetime

class HaikuSelector:
    def __init__(self):
        self.haiku_manager = HaikuManager()

    def select_haiku(self, conditions: Dict[str, List[str]]) -> Dict:
        """
        Select an appropriate haiku based on given conditions.
        Prioritizes haikus that match multiple specific conditions (time-based or seasonal)
        before falling back to general weather conditions.
        
        Args:
            conditions: Dictionary with keys 'morning', 'afternoon', 'evening', and 'general',
                      each containing a list of relevant tags
        """
        print(f"Selecting haiku for conditions: {conditions}")  # Debug log
        
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
        
        print(f"Specific tags: {specific_tags}")  # Debug log
        print(f"General tags: {general_tags}")    # Debug log
        
        # Get all potential matching haikus
        all_matching_haikus = self.haiku_manager.get_haikus_by_tags(specific_tags + general_tags)
        
        if not all_matching_haikus:
            print("No matches found, selecting random haiku")  # Debug log
            return random.choice(list(self.haiku_manager.haikus.values()))
        
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
        
        # Get the highest score
        max_score = max(score for score, _ in scored_haikus)
        
        # Select all haikus with the highest score
        best_haikus = [haiku for score, haiku in scored_haikus if score == max_score]
        
        # Return a random haiku from the best matches
        selected = random.choice(best_haikus)
        print(f"Selected haiku with tags: {selected['tags']}")  # Debug log
        return selected