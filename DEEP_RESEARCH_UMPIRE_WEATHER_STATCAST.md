"""
MLB Edge v2.0 — Configuration
Park factors, stadium coordinates, API keys, performance settings.
Optimized for slow computers with aggressive caching defaults.
"""
from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
CACHE_DIR = DATA_DIR / "cache"

DATA_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
CACHE_DIR.mkdir(exist_ok=True)

ODDS_API_KEY = ""
PARALLEL_WORKERS = 4
API_DELAY = 0.1
REQUEST_TIMEOUT = 15
MAX_RETRIES = 3
RETRY_DELAY = 2

STATCAST_ENABLED = False
STATCAST_DAYS = 7
BOXSCORE_ENABLED = True
BVP_LIMIT = 5
RECENT_GAMES = 3
LINESCORE_INNINGS = 2

MLB_API = "https://statsapi.mlb.com/api/v1"
MLB_SCHEDULE = "https://statsapi.mlb.com/api/v1/schedule"
OPEN_METEO = "https://api.open-meteo.com/v1/forecast"
THE_ODDS_API = "https://api.the-odds-api.com/v4/sports"
REFMETRICS = "https://www.refmetrics.com/mlb/umpires"

TEAM_IDS = {
    "ARI": 109, "ATL": 144, "BAL": 110, "BOS": 111, "CHC": 112,
    "CWS": 145, "CIN": 113, "CLE": 114, "COL": 115, "DET": 116,
    "HOU": 117, "KC": 118, "LAA": 108, "LAD": 119, "MIA": 146,
    "MIL": 158, "MIN": 142, "NYM": 121, "NYY": 147, "OAK": 133,
    "PHI": 143, "PIT": 134, "SD": 135, "SF": 137, "SEA": 136,
    "STL": 138, "TB": 139, "TEX": 140, "TOR": 141, "WSH": 120,
}
TEAM_NAMES = {v: k for k, v in TEAM_IDS.items()}

STADIUM_COORDS = {
    109: (33.4453, -112.0667), 144: (33.8907, -84.4677),
    110: (39.2839, -76.6218), 111: (42.3467, -71.0972),
    112: (41.9481, -87.6553), 145: (41.8298, -87.6336),
    113: (39.0974, -84.5061), 114: (41.4962, -81.6852),
    115: (39.7561, -104.9942), 116: (42.3379, -83.0493),
    117: (29.7573, -95.3557), 118: (39.0517, -94.4804),
    108: (33.8003, -117.8827), 119: (34.0736, -118.2400),
    146: (25.7781, -80.2198), 158: (43.0284, -87.9712),
    142: (44.9817, -93.2781), 121: (40.7570, -73.8458),
    147: (40.8295, -73.9262), 133: (37.7516, -122.2006),
    143: (39.9060, -75.1665), 134: (40.4468, -80.0056),
    135: (32.7076, -117.1570), 137: (37.7786, -122.3893),
    136: (47.5914, -122.3326), 138: (38.6226, -90.1850),
    139: (27.7681, -82.6534), 140: (32.7473, -97.0833),
    141: (43.6414, -79.3894), 120: (38.8730, -77.0075),
}

PARK_FACTORS = {
    109: 1.02, 144: 1.03, 110: 1.01, 111: 1.04, 112: 0.97,
    145: 1.01, 113: 1.03, 114: 0.98, 115: 1.40, 116: 0.99,
    117: 1.02, 118: 1.01, 108: 0.98, 119: 0.97, 146: 1.00,
    158: 1.01, 142: 0.99, 121: 0.98, 147: 1.02, 133: 1.01,
    143: 1.03, 134: 0.96, 135: 0.95, 137: 0.96, 136: 0.99,
    138: 1.01, 139: 0.99, 140: 1.01, 141: 1.00, 120: 0.99,
}

# Stadium center field azimuth (degrees clockwise from North, home plate → CF)
# Used for accurate wind in/out calculation. Dome stadiums marked with is_dome.
STADIUM_CF_AZIMUTH = {
    109: 3,   144: 190, 110: 12,  111: 65,  112: 225,
    145: 255, 113: 330, 114: 170, 115: 340, 116: 15,
    117: 347, 118: 255, 108: 205, 119: 335, 146: 195,
    158: 180, 142: 335, 121: 135, 147: 70,  133: 285,
    143: 195, 134: 100, 135: 190, 137: 265, 136: 185,
    138: 180, 139: 315, 140: 195, 141: 315, 120: 355,
}
DOME_STADIUMS = {139, 146}  # TB (Tropicana), MIA (loanDepot)
RETRACTABLE_ROOF = {117, 136, 140, 141, 158}  # HOU, SEA, TEX, TOR, MIL
