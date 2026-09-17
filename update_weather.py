import json
import requests
from datetime import datetime, timedelta
from pathlib import Path

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


def weather_group(code):

    if code in [0, 1]:
        return "clear"

    if code in [2, 3]:
        return "cloudy"

    if code in [45, 48]:
        return "fog"

    if code in [51, 53, 55, 56, 57]:
        return "drizzle"

    if code in [61, 63, 65, 66, 67, 80, 81, 82]:
        return "rain"

    if code in [71, 73, 75, 77, 85, 86]:
        return "snow"

    if code in [95, 96, 99]:
        return "thunder"

    return "other"


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
def daily_summary(hourly, target_date):

    times = hourly["time"]
    temps = hourly["temperature_2m"]
    rain = hourly["precipitation"]
    weathercodes = hourly["weathercode"]

    day_temps = []
    day_rain = []

    rain_hours = []
    weather_votes = {}

    for idx, t in enumerate(times):

        if t[:10] == target_date:

            day_temps.append(temps[idx])
            day_rain.append(rain[idx])

            code = weathercodes[idx]

            weather_votes[code] = (
                weather_votes.get(code, 0) + 1
            )

            if (rain[idx] or 0) >= 0.1:
                rain_hours.append(t[11:16])

    if not day_temps:
        return None

    dominant_weathercode = max(
        weather_votes,
        key=weather_votes.get
    )

    return {
        "minTemp": round(min(day_temps), 1),
        "maxTemp": round(max(day_temps), 1),
        "rainAmount": round(sum(day_rain), 1),
        "rainHours": rain_hours,
        "weathercode": dominant_weathercode
    }

def fetch_actual_day(lat, lon, date):

    url = (
        "https://archive-api.open-meteo.com/v1/archive"
        f"?latitude={lat}"
        f"&longitude={lon}"
        f"&start_date={date}"
        f"&end_date={date}"
        "&daily="
        "temperature_2m_min,"
        "temperature_2m_max,"
        "precipitation_sum"
        "&hourly=precipitation,weathercode"
        "&timezone=auto"
    )

    data = fetch_json(url)

    actual_rain_hours = []
    actual_weather_votes = {}

    for idx, value in enumerate(
        data["hourly"]["precipitation"]
    ):

        code = data["hourly"]["weathercode"][idx]

        actual_weather_votes[code] = (
            actual_weather_votes.get(code, 0) + 1
        )

        if value >= 0.1:

            actual_rain_hours.append(
                data["hourly"]["time"][idx][11:16]
            )

    daily = data["daily"]

    dominant_weathercode = max(
        actual_weather_votes,
        key=actual_weather_votes.get
    )

    return {
        "minTemp": daily["temperature_2m_min"][0],
        "maxTemp": daily["temperature_2m_max"][0],
        "rainAmount": daily["precipitation_sum"][0],
        "rainHours": actual_rain_hours,
        "weathercode": dominant_weathercode
    }


def calculate_rain_timing_score(
    predicted_hours,
    actual_hours
):

    predicted = set(predicted_hours or [])
    actual = set(actual_hours or [])

    if not predicted and not actual:
        return 100.0

    if not predicted or not actual:
        return 0.0

    correct = 0

    for actual_time in actual:

        actual_dt = datetime.strptime(
            actual_time,
            "%H:%M"
        )

        found = False

        for offset in (-1, 0, 1):

            check_time = (
                actual_dt +
                timedelta(hours=offset)
            ).strftime("%H:%M")

            if check_time in predicted:
                found = True
                break

        if found:
            correct += 1

    precision = correct / len(predicted)
    recall = correct / len(actual)

    if precision + recall == 0:
        return 0.0

    score = (
        2 * precision * recall
    ) / (
        precision + recall
    )

    print(
        "F1:",
        "correct=", correct,
        "predicted=", len(predicted),
        "actual=", len(actual),
        "score=", round(score * 100, 1)
    )

    return round(score * 100, 1)
def calculate_model_stats(history):

    models = [
        "smhi",
        "yr",
        "dmi_seamless",
        "icon_eu"
    ]

    stats = {}

    for model in models:

        temp_errors = []
        rain_errors = []
        rain_timing_scores = []

        rain_hits_total = 0
        rain_actual_total = 0
        weather_hits = 0
        weather_total = 0

        counted_actual_dates = set()

        min_biases = []
        max_biases = []
        rain_biases = []

        min_errors = []
        max_errors = []

        for bucket in ["day1", "day2", "day3"]:

            for date, forecast in history.get(bucket, {}).items():

                actual = history.get("actual", {}).get(date)

                if not actual:
                    continue

                model_data = forecast.get(model)

                if not model_data:
                    continue

if (
    model_data.get("weathercode") is not None
    and
    actual.get("weathercode") is not None
):
    if (
        weather_group(model_data["weathercode"])
        ==
        weather_group(actual["weathercode"])
    ):
        weather_hits += 1

    weather_total += 1

                weather_total += 1
                min_err = abs(
                    model_data["minTemp"]
                    - actual["minTemp"]
                )

                max_err = abs(
                    model_data["maxTemp"]
                    - actual["maxTemp"]
                )

                min_bias = (
                    model_data["minTemp"]
                    - actual["minTemp"]
                )

                max_bias = (
                    model_data["maxTemp"]
                    - actual["maxTemp"]
                )

                min_biases.append(min_bias)
                max_biases.append(max_bias)

                min_errors.append(min_err)
                max_errors.append(max_err)

                rain_err = abs(
                    model_data["rainAmount"]
                    - actual["rainAmount"]
                )

                rain_bias = (
                    model_data["rainAmount"]
                    - actual["rainAmount"]
                )

                rain_biases.append(rain_bias)

                temp_errors.append(
                    (min_err + max_err) / 2
                )

                rain_errors.append(rain_err)

                predicted_hours = model_data.get(
                    "rainHours",
                    []
                )

                actual_hours = actual.get(
                    "rainHours",
                    []
                )

                timing_score = calculate_rain_timing_score(
                    predicted_hours,
                    actual_hours
                )

                rain_timing_scores.append(
                    timing_score
                )

                if date not in counted_actual_dates:

                    predicted = set(
                        predicted_hours or []
                    )

                    for actual_time in actual_hours:

                        actual_dt = datetime.strptime(
                            actual_time,
                            "%H:%M"
                        )

                        found = False

                        for offset in (-1, 0, 1):

                            check_time = (
                                actual_dt
                                + timedelta(hours=offset)
                            ).strftime("%H:%M")

                            if check_time in predicted:
                                found = True
                                break

                        if found:
                            rain_hits_total += 1

                    rain_actual_total += len(
                        actual_hours
                    )

                    counted_actual_dates.add(date)

        if temp_errors:

            avg_temp = round(
                sum(temp_errors) / len(temp_errors),
                2
            )

            avg_rain = round(
                sum(rain_errors) / len(rain_errors),
                2
            )

            avg_rain_bias = round(
                sum(rain_biases) / len(rain_biases),
                2
            )

            avg_min_bias = round(
                sum(min_biases) / len(min_biases),
                2
            )

            avg_max_bias = round(
                sum(max_biases) / len(max_biases),
                2
            )

            avg_min_error = round(
                sum(min_errors) / len(min_errors),
                2
            )

            avg_max_error = round(
                sum(max_errors) / len(max_errors),
                2
            )

            avg_rain_timing = round(
                sum(rain_timing_scores)
                / len(rain_timing_scores),
                1
            ) if rain_timing_scores else 0

            score = round(
                100
                - (avg_temp * 10)
                - avg_rain
                + (avg_rain_timing * 0.05),
                1
            )

            print(
                model,
                "hits:",
                rain_hits_total,
                "actual:",
                rain_actual_total
            )

            stats[model] = {
                "samples": len(temp_errors),

                "temp_error": avg_temp,

                "min_temp_error": avg_min_error,
                "max_temp_error": avg_max_error,

                "min_temp_bias": avg_min_bias,
                "max_temp_bias": avg_max_bias,

                "rain_error": avg_rain,
                "rain_bias": avg_rain_bias,

                "rain_timing_score":
                    avg_rain_timing,

                "rain_hits":
                    rain_hits_total,

                "rain_actual_hours":
                    rain_actual_total,

                "weather_hits":
                    weather_hits,

                "weather_total":
                    weather_total,

                "weather_accuracy":
                    round(
                        weather_hits * 100 /
                        weather_total,
                        1
                    ) if weather_total else 0,

                "score":
                    score
            }

    return dict(
        sorted(
            stats.items(),
            key=lambda x: x[1]["score"],
            reverse=True
        )
    )

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
print("Dag 1-3 prognoser för Torsby:")

weekly = weather["Torsby"]["weekly"]["daily"]
print(weather["Torsby"].keys())
print(weather["Torsby"]["smhi"]["hourly"].keys())
for i in range(3):
    print(
        weekly["time"][i],
        weekly["temperature_2m_min"][i],
        weekly["temperature_2m_max"][i],
        weekly["precipitation_sum"][i]
    )

history_file = Path("forecast-history.json")

if history_file.exists():
    with open(
        "forecast-history.json",
        "r",
        encoding="utf-8"
    ) as f:
        history = json.load(f)
else:
    history = {
        "day1": {},
        "day2": {},
        "day3": {},
        "actual": {}
    }

weekly = weather["Torsby"]["weekly"]["daily"]

for i in range(3):

    key = f"day{i + 1}"
    date = weekly["time"][i][:10]

    history[key][date] = {}

    history[key][date]["smhi"] = daily_summary(
    weather["Torsby"]["smhi"]["hourly"],
    date
    )

    history[key][date]["yr"] = daily_summary(
        weather["Torsby"]["yr"]["hourly"],
        date
    )

    history[key][date]["dmi_seamless"] = daily_summary(
        weather["Torsby"]["dmi_seamless"]["hourly"],
        date
    )

    history[key][date]["icon_eu"] = daily_summary(
        weather["Torsby"]["icon_eu"]["hourly"],
        date
    )

dates_to_check = set()

for bucket in ["day1", "day2", "day3"]:
    dates_to_check.update(
        history.get(bucket, {}).keys()
    )

today = datetime.utcnow().strftime("%Y-%m-%d")

for date in sorted(dates_to_check):

    if date > today:
        continue

    try:
        history["actual"][date] = fetch_actual_day(
            60.136,
            13.006,
            date
        )

        print(
            f"Actual sparad för {date}:",
            history["actual"][date]
        )

    except Exception as e:
        print(
            f"Actual-data kunde inte hämtas för {date}:",
            e
        )

history["model_stats"] = calculate_model_stats(
    history
)

print(
    json.dumps(
        history["model_stats"],
        indent=2,
        ensure_ascii=False
    )
)

with open(
    "forecast-history.json",
    "w",
    encoding="utf-8"
) as f:
    json.dump(
        history,
        f,
        ensure_ascii=False,
        indent=2
    )
with open("weather.json", "w", encoding="utf-8") as f:
    json.dump(
        weather,
        f,
        ensure_ascii=False,
        separators=(",", ":")
    )

print("weather.json skapad")
