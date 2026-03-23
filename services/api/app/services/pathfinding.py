CRIME_SCORING = {
    "violent-crime": 10,
    "sexual-offences": 10,
    "possession-of-weapons": 10,
    "robbery": 5,
    "theft-from-the-person": 5,
    "public-order": 3,
    "drugs": 3,
    "anti-social-behaviour": 2,
    "burglary": 2,
    "vehicle-crime": 2,
    "criminal-damage-arson": 2,
    "shoplifting": 1,
    "bicycle-theft": 1,
    "other-theft": 1,
    "other-crime": 1
}

class PathfindingEngine:

    def __init__(self):
        # Maps points to different types of crime based on severity.
        # Allows for better weightign based on crime types.
        self.crimeScoring = CRIME_SCORING
        
        # Applies a fixed penalty for areas with low lighting.
        self.lightingPenalty = 1.5

    def normaliseCrimeType(self, crime_type: str) -> str:
        # Normalises crime type strings from the UK Police API to match scoring keys.
        return crime_type.strip().lower().replace(" ", "-")

    def calculateCrimeRates(self, crimes: list[str]) -> float:
        # Calculates the total points for the crimes in an area.
        totalPoints = 0
        for crime_type in crimes:
            normalised = self.normaliseCrimeType(crime_type)
            points = self.crimeScoring.get(normalised, 1)
            totalPoints += points
            
        # Based on the points an area has, it is weighted differently.
        if totalPoints == 0:
            # No crime, no weighting penalty.
            return 1.0
        elif totalPoints <= 5:
            # Low risk, 25% penalty.
            return 1.25
        elif totalPoints <= 15:
            # Medium risk, 100% penalty.
            return 2.0
        else:
            # High risk, 200% penalty.
            return 3.0

    def calculateCost(self, routes: list[dict]):
        """
        Processes the routes to determine the safety score and identify the best path.
        Returns (fastest, safest) or raises ValueError if no routes provided.
        """
        if not routes:
            raise ValueError("No routes provided to calculateCost.")

        for route in routes:
            multiplier = self.calculateCrimeRates(route.get('crimes_list', []))
            weighted_score = route['base_time'] * multiplier

            if route.get('is_dark'):
                weighted_score *= self.lightingPenalty

            route['safety_score'] = round(weighted_score, 2)

        fastest = min(routes, key=lambda x: x['base_time'])
        safest = min(routes, key=lambda x: x['safety_score'])

        # Flag if both options resolve to the same route
        are_same = fastest['safety_score'] == safest['safety_score'] and \
                   fastest['base_time'] == safest['base_time']

        return {
            "fastest": fastest,
            "safest": safest,
            "are_same": are_same
        }
