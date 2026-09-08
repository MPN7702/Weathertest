async function loadSMHI(){

    const response = await fetch(
      "smhi-proxy.mr-magoo21.workers.dev"
    );

    const json = await response.json();

    const first = json.timeSeries[0];

    const data = first.data;

    document.getElementById("output").innerHTML = `
        <p>Temperatur: ${data.air_temperature} °C</p>
        <p>Vind: ${data.wind_speed} m/s</p>
        <p>Kastvind: ${data.wind_speed_of_gust} m/s</p>
        <p>Tryck: ${data.air_pressure_at_mean_sea_level} hPa</p>
        <p>Molnighet: ${data.cloud_area_fraction}</p>
        <p>Regn: ${data.precipitation_amount_mean_deterministic} mm</p>
        <p>WeatherCode: ${data.symbol_code}</p>
    `;

}

loadSMHI();
