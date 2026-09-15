import requests
import re
import json
from datetime import datetime

url = "https://fangstrapport.se/sjö/övre-fryken/vattentemperatur"

html = requests.get(
    url,
    headers={"User-Agent": "Mozilla/5.0"},
    timeout=20
).text

match = re.search(r'(\d+,\d+)', html)

if match:
    temperatur = float(match.group(1).replace(",", "."))

    data = {
        "ovre_fryken": temperatur,
        "updated": datetime.utcnow().strftime("%Y-%m-%d")
    }

    with open("water_temp.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Övre Fryken: {temperatur}°C")

else:
    raise Exception("Ingen temperatur hittades")
