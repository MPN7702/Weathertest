import json
import requests
from datetime import datetime

LOCATIONS = [
    ("Torsby", 60.136, 13.006),
    ("Sysslebäck", 60.729, 13.006),
    ("Stöllet", 60.416, 13.256),
    ("Likenäs", 60.640, 13.220),
    ("Östmark", 60.314, 12.996),
    ("Höljes", 60.815, 12.790),
    ("Ambjörby", 60.480, 13.115),
    ("Värnäs", 60.285, 13.173),
    ("Vitsand", 60.542, 13.017),
    ("Branäs", 60.689, 13.189),
]

OPENMETEO_MODELS = [
    "icon_eu",
    "dmi_seamless"
]


def fetch_json(url):
    last_error = None

    for _ in range(3):
        try:
            r = requests.get(url, timeout=120)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            last_error = e

    raise last_error


def weathercode_from_yr(symbol):
    symbol = str(symbol).lower()

    if "clearsky" in symbol:
        return 0

    if "fair" in symbol:
        return 1

    if "partlycloudy" in symbol:
        return 2

    if "cloudy" in symbol:
        return 3

    if "fog" in symbol:
        return 45

    if "lightrain" in symbol:
        return 61

    if "rain" in symbol:
        return 63

    if "heavyrain" in symbol:
        return 65

    if "lightsleet" in symbol:
        return 68

    if "sleet" in symbol:
        return 69

    if "lightsnow" in symbol:
        return 71

    if "snow" in symbol:
        return 73

    if "heavysnow" in symbol:
        return 75

    if "showers" in symbol:
        return 80

    if "thunder" in symbol:
        return 95

    return 3


def weathercode_from_smhi(symbol):
    mapping = {
        1: 0,
        2: 1,
        3: 2,
        4: 3,
        5: 3,
        6: 3,
        7: 45,
        8: 61,
        9: 63,
        10: 80,
        11: 95,
        12: 71,
        13: 73,
        14: 75,
        15: 95,
        16: 95,
        17: 95,
        18: 95,
        19: 95,
        20: 95,
        21: 95,
        22: 95,
        23: 95,
        24: 95,
        25: 95,
        26: 95,
        27: 95
    }

    return mapping.get(symbol, 3)


def convert_smhi(smhi):
    hourly = {
        "time": [],
        "temperature_2m": [],
        "surface_pressure": [],
        "wind_speed_10m": [],
        "wind_gusts_10m": [],
        "wind_direction_10m": [],
        "precipitation_probability": [],
        "precipitation": [],
        "weathercode": []
    }

    for row in smhi["timeSeries"]:
        d = row["data"]

        hourly["time"].append(row["time"][:16])

        hourly["temperature_2m"].append(
            d.get("air_temperature")
        )

        hourly["surface_pressure"].append(
            d.get("air_pressure_at_mean_sea_level")
        )

        hourly["wind_speed_10m"].append(
            round(d.get("wind_speed", 0) * 3.6, 1)
        )

        hourly["wind_gusts_10m"].append(
            round(d.get("wind_speed_of_gust", 0) * 3.6, 1)
        )

        hourly["wind_direction_10m"].append(
            d.get("wind_from_direction")
        )

        hourly["precipitation_probability"].append(
            d.get("probability_of_precipitation", 0)
        )

        hourly["precipitation"].append(
            d.get(
                "precipitation_amount_mean_deterministic",
                d.get("precipitation_amount_mean", 0)
            )
        )

        hourly["weathercode"].append(
            weathercode_from_smhi(
                d.get("symbol_code", 4)
            )
        )

    return {
        "latitude": smhi.get("geometry", {}).get("coordinates", [None, None])[1],
        "longitude": smhi.get("geometry", {}).get("coordinates", [None, None])[0],
        "hourly": hourly
    }


def convert_yr(yr):
    hourly = {
        "time": [],
        "temperature_2m": [],
        "surface_pressure": [],
        "wind_speed_10m": [],
        "wind_gusts_10m": [],
        "wind_direction_10m": [],
        "precipitation_probability": [],
        "precipitation": [],
        "weathercode": []
    }

    for row in yr["properties"]["timeseries"]:
        inst = row["data"]["instant"]["details"]

        hourly["time"].append(row["time"][:16])

        hourly["temperature_2m"].append(
            inst.get("air_temperature")
        )

        hourly["surface_pressure"].append(
            inst.get("air_pressure_at_sea_level")
        )

        hourly["wind_speed_10m"].append(
            round(inst.get("wind_speed", 0) * 3.6, 1)
        )

        hourly["wind_gusts_10m"].append(
            round(inst.get("wind_speed_of_gust", 0) * 3.6, 1)
        )

        hourly["wind_direction_10m"].append(
            inst.get("wind_from_direction")
        )

        next1 = (
            row["data"].get("next_1_hours")
            or row["data"].get("next_6_hours")
            or row["data"].get("next_12_hours")
            or {}
        )

        hourly["precipitation_probability"].append(
            next1.get("details", {}).get(
                "probability_of_precipitation",
                0
            )
        )

        hourly["precipitation"].append(
            next1.get("details", {}).get(
                "precipitation_amount",
                0
            )
        )

        symbol = (
            next1.get("summary", {})
            .get("symbol_code", "cloudy")
        )

        hourly["weathercode"].append(
            weathercode_from_yr(symbol)
        )

    return {
        "latitude": yr.get("geometry", {}).get("coordinates", [None, None])[1],
        "longitude": yr.get("geometry", {}).get("coordinates", [None, None])[0],
        "hourly": hourly
    }


def fetch_openmeteo(lat, lon, model):
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}"
        f"&longitude={lon}"
        f"&models={model}"
        "&hourly="
        "temperature_2m,"
        "pressure_msl,"
        "wind_speed_10m,"
        "wind_gusts_10m,"
        "wind_direction_10m,"
        "precipitation_probability,"
        "precipitation,"
        "weathercode"
        "&forecast_days=7"
    )

    data = fetch_json(url)

    if "hourly" in data:
        data["hourly"]["surface_pressure"] = \
            data["hourly"].pop("pressure_msl", [])

    return data


def fetch_weekly(lat, lon):
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}"
        f"&longitude={lon}"
"&daily="
"weathercode,"
"temperature_2m_max,"
"temperature_2m_min,"
"precipitation_probability_max,"
"precipitation_sum,"
"wind_speed_10m_mean,"
"wind_direction_10m_dominant,"
"wind_gusts_10m_mean,"
"surface_pressure_mean,"
"sunrise,"
"sunset"
        "&timezone=auto"
        "&forecast_days=7"
    )

    return fetch_json(url)


weather = {
    "updated": datetime.utcnow().strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
}

for name, lat, lon in LOCATIONS:
    print("Hämtar:", name)

    place = {}

    for model in OPENMETEO_MODELS:
        place[model] = fetch_openmeteo(
            lat,
            lon,
            model
        )

    smhi_raw = fetch_json(
        f"https://smhi-proxy.mr-magoo21.workers.dev/?lat={lat}&lon={lon}"
    )

    yr_raw = fetch_json(
        f"https://yr-proxy.mr-magoo21.workers.dev/?lat={lat}&lon={lon}"
    )

    place["smhi"] = convert_smhi(smhi_raw)
    place["yr"] = convert_yr(yr_raw)

    place["weekly"] = fetch_weekly(lat, lon)

    weather[name] = place

with open("weather.json", "w", encoding="utf-8") as f:
    json.dump(
        weather,
        f,
        ensure_ascii=False,
        separators=(",", ":")
    )

print("weather.json skapad")
