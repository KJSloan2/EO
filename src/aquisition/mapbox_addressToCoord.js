document.getElementById('csvFileInput').addEventListener('change', function(event) {
    const file = event.target.files[0];
    const reader = new FileReader();

    reader.onload = function(e) {
        const text = e.target.result;
        processCSV(text);
    };

    reader.readAsText(file);
});

function processCSV(csvText) {
    const rows = csvText.split('\n');
    let results = [];

    rows.forEach((row, index) => {
        if (index > 0 && row) { // Skip header or empty rows
            const columns = row.split(','); // Assuming CSV is comma-separated
            const address_parts = [columns[4],columns[6],"TX",columns[8]];
            //adress_parts example input: [2803 AVE H, LUBBOCK, TX, 79404]
            const address = address_parts.join(",");

            geocodeAddress(address, (coords) => {
                results.push(`${address},${coords.lat},${coords.lng}`);
                if (results.length === rows.length - 1) { // -1 to account for header
                    downloadResults(results);
                }
            });
        }
    });
}

function geocodeAddress(address, callback) {
    const accessToken = 'MAPBOX TOKEN';
    const url = `https://api.mapbox.com/geocoding/v5/mapbox.places/${encodeURIComponent(address)}.json?access_token=${accessToken}`;

    fetch(url).then(response => response.json()).then(data => {
        const coords = data.features[0].geometry.coordinates;
        callback({ lng: coords[0], lat: coords[1] });
    });
}

function downloadResults(results) {
    const csvContent = "data:text/csv;charset=utf-8," 
        + "Address,City,State,Zip Code,Latitude,Longitude\n" 
        + results.join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", "geocoded_addresses.csv");
    document.body.appendChild(link); // Required for FF

    link.click(); // This will download the file
}