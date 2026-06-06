"""
MLB Edge v2.2 — Weather Fetcher
Open-Meteo (free, no key). Physics-based wind direction + air density + carry index.
"""
import math
import requests
import time
from datetime import datetime
from typing import Optional, Dict

from config import (
    STADIUM_COORDS, TEAM_NAMES, REQUEST_TIMEOUT,
    STADIUM_CF_AZIMUTH, DOME_STADIUMS, RETRACTABLE_ROOF
)

class WeatherFetcher:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "MLBEdge/2.2"})

    def get_weather(self, team_id: int) -> Optional[Dict]:
        coords = STADIUM_COORDS.get(team_id)
        if not coords:
            return None
        lat, lon = coords
        team_name = TEAM_NAMES.get(team_id, str(team_id))
        is_dome = team_id in DOME_STADIUMS
        is_retractable = team_id in RETRACTABLE_ROOF

        try:
            r = self.session.get("https://api.open-meteo.com/v1/forecast", params={
                "latitude": lat, "longitude": lon,
                "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,"
                           "wind_direction_10m,precipitation,surface_pressure",
                "hourly": "temperature_2m,precipitation_probability,wind_speed_10m",
                "temperature_unit": "fahrenheit",
                "wind_speed_unit": "mph",
                "forecast_days": 1, "timezone": "auto"
            }, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
            data = r.json()
            current = data.get("current", {})
            hourly = data.get("hourly", {})

            temp_f = current.get("temperature_2m", 72)
            humidity = current.get("relative_humidity_2m", 50)
            wind_speed = current.get("wind_speed_10m", 5)
            wind_deg = current.get("wind_direction_10m", 180)
            precip = current.get("precipitation", 0)
            pressure_hpa = current.get("surface_pressure", 1013.25)

            # Cardinal direction
            cardinals = ['N','NNE','NE','ENE','E','ESE','SE','SSE',
                         'S','SSW','SW','WSW','W','WNW','NW','NNW']
            wind_cardinal = cardinals[int((wind_deg + 11.25) / 22.5) % 16]

            # Precip probability (afternoon window)
            precip_prob = 0
            if hourly and "precipitation_probability" in hourly:
                probs = hourly["precipitation_probability"]
                afternoon = probs[12:22] if len(probs) >= 22 else probs[12:]
                precip_prob = sum(p or 0 for p in afternoon) / max(1, len(afternoon))

            # ── PHYSICS-BASED WIND IMPACT ──
            cf_azimuth = STADIUM_CF_AZIMUTH.get(team_id, 180)
            wind_impact, out_component = self._calc_wind_impact(
                wind_speed, wind_deg, cf_azimuth, is_dome
            )

            # ── AIR DENSITY INDEX ──
            # Lower density = ball carries farther = more runs
            # Standard: 1013.25 hPa, 59°F (15°C), 50% humidity
            density_idx, carry_adj = self._calc_air_density(
                temp_f, pressure_hpa, humidity
            )

            # ── COMPOSITE RUN ADJUSTMENT ──
            # Wind: +19 ft per 5 mph tailwind → roughly +0.3 runs per 5 mph out
            wind_run_adj = out_component * 0.06  # ~0.3 runs per 5mph
            # Temp: +4 ft per 10°F above 70 → ~0.1 runs per 10°F
            temp_run_adj = (temp_f - 70) * 0.01
            # Pressure: lower = less dense = more carry
            press_run_adj = (1013.25 - pressure_hpa) * 0.005
            # Humidity: overrated, net effect ~neutral (slightly negative)
            humid_run_adj = 0  # intentionally zero

            if is_dome:
                total_run_adj = 0.0
            else:
                total_run_adj = wind_run_adj + temp_run_adj + press_run_adj + humid_run_adj
                total_run_adj = max(-1.5, min(1.5, total_run_adj))

            return {
                "team": team_name, "temperature_f": round(temp_f, 1),
                "humidity": round(humidity, 1), "wind_speed_mph": round(wind_speed, 1),
                "wind_direction": wind_cardinal, "wind_degrees": wind_deg,
                "wind_impact": wind_impact,
                "out_component": round(out_component, 1),
                "surface_pressure_hpa": round(pressure_hpa, 1),
                "density_index": round(density_idx, 4),
                "carry_adjustment_ft": round(carry_adj, 1),
                "weather_run_adj": round(total_run_adj, 2),
                "wind_run_adj": round(wind_run_adj, 2),
                "temp_run_adj": round(temp_run_adj, 2),
                "pressure_run_adj": round(press_run_adj, 2),
                "precipitation": round(precip, 2),
                "precip_probability": round(precip_prob, 1),
                "is_dome": is_dome,
                "is_retractable": is_retractable,
                "updated": datetime.now().strftime("%H:%M"),
            }
        except Exception as e:
            print(f"  Weather error for {team_name}: {e}")
            return None

    @staticmethod
    def _calc_wind_impact(wind_speed, wind_deg, cf_azimuth, is_dome):
        """
        Calculate true wind-in/out using stadium orientation.
        Wind direction from Open-Meteo = direction wind comes FROM.
        If wind comes from behind home plate → blowing OUT to CF.
        """
        if is_dome or wind_speed < 3:
            return "neutral", 0.0

        # Wind heading (where it comes FROM)
        # CF azimuth = direction from HP to CF
        # Wind blowing OUT = wind comes from HP direction (behind batter)
        # That means wind_deg ≈ (cf_azimuth + 180) mod 360
        # Calculate angle between wind source and the "behind HP" direction
        behind_hp = (cf_azimuth + 180) % 360
        angle_diff = wind_deg - behind_hp
        # Normalize to -180..180
        while angle_diff > 180: angle_diff -= 360
        while angle_diff < -180: angle_diff += 360

        # Cosine projection: +1 = perfectly blowing out, -1 = perfectly blowing in
        out_component = math.cos(math.radians(angle_diff)) * wind_speed

        if out_component > 8:
            impact = "blowing_out"
        elif out_component > 3:
            impact = "light_out"
        elif out_component < -8:
            impact = "blowing_in"
        elif out_component < -3:
            impact = "light_in"
        elif wind_speed > 10:
            impact = "crosswind"
        else:
            impact = "neutral"

        return impact, round(out_component, 1)

    @staticmethod
    def _calc_air_density(temp_f, pressure_hpa, humidity_pct):
        """
        Calculate relative air density index and estimated carry adjustment.
        Standard atmosphere: 1.225 kg/m³ at 15°C, 1013.25 hPa, 0% humidity.
        Returns (density_ratio, carry_feet_adjustment).
        """
        # Convert to SI
        temp_c = (temp_f - 32) * 5 / 9
        temp_k = temp_c + 273.15
        p_pa = pressure_hpa * 100  # hPa to Pa

        # Saturation vapor pressure (Buck equation, simplified)
        e_sat = 611.21 * math.exp((18.678 - temp_c / 234.5) * (temp_c / (257.14 + temp_c)))
        e_actual = e_sat * humidity_pct / 100

        # Dry air pressure
        p_dry = p_pa - e_actual

        # Density: ρ = (Pd / (Rd * T)) + (Pv / (Rv * T))
        R_d = 287.058  # J/(kg·K) dry air
        R_v = 461.495  # J/(kg·K) water vapor
        density = (p_dry / (R_d * temp_k)) + (e_actual / (R_v * temp_k))

        # Standard density at sea level 15°C
        std_density = 1.225
        ratio = density / std_density

        # Carry adjustment: lower density = more carry
        # Rough: 1% less density ≈ +4 feet on a 400ft fly ball
        carry_ft = (1.0 - ratio) * 400

        return ratio, carry_ft

    def get_all_weather(self, team_ids: list) -> Dict[int, Optional[Dict]]:
        results = {}
        for tid in set(team_ids):
            results[tid] = self.get_weather(tid)
            time.sleep(0.2)
        return results

    def format_summary(self, weather: Dict) -> str:
        if not weather:
            return "Weather data unavailable"
        temp = weather.get("temperature_f", 72)
        ws = weather.get("wind_speed_mph", 5)
        wd = weather.get("wind_direction", "N")
        wi = weather.get("wind_impact", "neutral")
        pp = weather.get("precip_probability", 0)
        run_adj = weather.get("weather_run_adj", 0)
        parts = [f"{temp}°F"]
        if ws > 5:
            parts.append(f"Wind {wd} {ws}mph ({wi.replace('_', ' ')})")
        else:
            parts.append(f"Wind {wd} {ws}mph")
        if abs(run_adj) > 0.15:
            sign = "+" if run_adj > 0 else ""
            parts.append(f"Carry: {sign}{run_adj:.1f}R")
        if pp > 30:
            parts.append(f"{pp:.0f}% rain")
        if weather.get("is_dome"):
            return "Dome — weather neutral"
        return " | ".join(parts)
