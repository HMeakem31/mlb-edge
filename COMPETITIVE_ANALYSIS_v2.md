"""
Smart caching layer for MLB data.
Saves API responses to disk with timestamps to avoid redundant calls.
"""
import json
import time
from pathlib import Path

CACHE_DIR = Path(__file__).parent / "data" / "cache"

CACHE_EXPIRY = {
    "team_stats": 6 * 3600,
    "pitcher_stats": 6 * 3600,
    "recent_games": 3 * 3600,
    "linescores": 3 * 3600,
    "boxscores": 3 * 3600,
    "bvp": 6 * 3600,
    "weather": 3 * 3600,
    "umpires": 6 * 3600,
    "lines": 1 * 3600,
    "roster": 6 * 3600,
    "statcast": 12 * 3600,
    "schedule": 6 * 3600,
}

def ensure_cache_dir():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

def get_cache_key(endpoint, identifier):
    safe = str(identifier).replace("/", "_").replace("\\", "_").replace(":", "_")
    return f"{endpoint}_{safe}.json"

def get_cached(endpoint, identifier):
    ensure_cache_dir()
    cache_file = CACHE_DIR / get_cache_key(endpoint, identifier)
    if not cache_file.exists():
        return None
    file_age = time.time() - cache_file.stat().st_mtime
    expiry = CACHE_EXPIRY.get(endpoint, 3 * 3600)
    if file_age > expiry:
        return None
    try:
        with open(cache_file, 'r') as f:
            data = json.load(f)
        return data.get("content")
    except (json.JSONDecodeError, KeyError, IOError):
        return None

def cache_data(endpoint, identifier, content):
    ensure_cache_dir()
    cache_file = CACHE_DIR / get_cache_key(endpoint, identifier)
    try:
        if hasattr(content, 'to_dict'):
            serializable = content.to_dict()
        elif hasattr(content, 'to_list'):
            serializable = content.to_list()
        else:
            serializable = content
        with open(cache_file, 'w') as f:
            json.dump({"content": serializable, "timestamp": time.time()}, f)
    except (TypeError, IOError) as e:
        print(f"  Cache write error: {e}")

def clear_expired_cache():
    ensure_cache_dir()
    now = time.time()
    cleaned = 0
    for cache_file in CACHE_DIR.glob("*.json"):
        try:
            file_age = now - cache_file.stat().st_mtime
            endpoint = cache_file.stem.split("_")[0]
            expiry = CACHE_EXPIRY.get(endpoint, 3 * 3600)
            if file_age > expiry:
                cache_file.unlink()
                cleaned += 1
        except (OSError, IOError):
            continue
    if cleaned > 0:
        print(f"  Cleared {cleaned} expired cache files")

def clear_all_cache():
    ensure_cache_dir()
    for cache_file in CACHE_DIR.glob("*.json"):
        try:
            cache_file.unlink()
        except (OSError, IOError):
            pass
    print("  All cache cleared")

def get_cache_stats():
    ensure_cache_dir()
    stats = {"files": 0, "total_size_mb": 0.0, "by_endpoint": {}}
    for cache_file in CACHE_DIR.glob("*.json"):
        stats["files"] += 1
        stats["total_size_mb"] += cache_file.stat().st_size / (1024 * 1024)
        endpoint = cache_file.stem.split("_")[0]
        if endpoint not in stats["by_endpoint"]:
            stats["by_endpoint"][endpoint] = {"count": 0, "size_mb": 0.0}
        stats["by_endpoint"][endpoint]["count"] += 1
        stats["by_endpoint"][endpoint]["size_mb"] += cache_file.stat().st_size / (1024 * 1024)
    return stats
