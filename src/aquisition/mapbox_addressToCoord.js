function downloadResults(results, regionId) {
    const csvContent = "data:text/csv;charset=utf-8," 
        + "LPST ID,Regulated Entity Number,Reported Date,Closure Date,Street_Address,City,County,State,ZipCode,Latitude,Longitude\n" 
        + results.join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    const fNameDownload = regionId + "_geocoded_addresses.csv";
    link.setAttribute("download", fNameDownload);
    document.body.appendChild(link); // Required for FF

    link.click(); // This will download the file
}


document.getElementById('csvFileInput').addEventListener('change', function(event) {
    const file = event.target.files[0];

    // Get the filename, strip the file extension, split with "_", and store the last element in regionId
    const filename = file.name;
    const filenameWithoutExtension = filename.substring(0, filename.lastIndexOf('.'));
    const filenameParts = filenameWithoutExtension.split('_');
    const regionId = filenameParts[filenameParts.length - 1];

    console.log("Region ID:", regionId); // Just to verify

    Papa.parse(file, {
        header: true,
        skipEmptyLines: true,
        complete: function(results) {
            processCSV(results.data, regionId);
        }
    });
});

function processCSV(data, regionId) {
    let results = [];
    let pendingRequests = 0;

    data.forEach((row) => {
        const { 'LPST ID': lpstId, 'Regulated Entity Number': regEntityNumPst, 'Reported Date': reportedDate, 'Closure Date': closureDate, 'Site Address': siteAddress, 'City': city, 'County': county, 'Zip Code': zipCode } = row;
        const state = "TX";
        const address_parts = [siteAddress, city, county, state, zipCode];

        if (address_parts.every(part => part !== null && part !== undefined && part !== '')) {
            const address = address_parts.join(",");
            pendingRequests++;
            geocodeAddress(address, (coords) => {
                if (coords.lat && coords.lng) {
                    results.push(`${lpstId},${regEntityNumPst},${reportedDate},${closureDate},${siteAddress},${city},${county},${state},${zipCode},${coords.lat},${coords.lng}`);
                } else {
                    results.push(`${lpstId},${regEntityNumPst},${reportedDate},${closureDate},${siteAddress},${city},${county},${state},${zipCode},,`); // No coordinates
                }
                pendingRequests--;
                if (pendingRequests === 0) {
                    downloadResults(results, regionId);
                }
            });
        } else {
            console.log("One or more address parts are null or undefined.");
        }
    });
}

function geocodeAddress(address, callback) {
    const accessToken = 'MAPBOX TOKEN';
    const url = `https://api.mapbox.com/geocoding/v5/mapbox.places/${encodeURIComponent(address)}.json?access_token=${accessToken}`;

    fetch(url).then(response => response.json()).then(data => {
        if (data.features && data.features.length > 0) {
            const coords = data.features[0].geometry.coordinates;
            callback({ lng: coords[0], lat: coords[1] });
        } else {
            callback({ lng: null, lat: null });
        }
    }).catch(() => {
        callback({ lng: null, lat: null });
    });
}

function downloadResults(results, regionId) {
    const csvContent = "data:text/csv;charset=utf-8," 
        + "LPST ID,Regulated Entity Number,Reported Date,Closure Date,Street_Address,City,County,State,ZipCode,Latitude,Longitude\n" 
        + results.join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    const fNameDownload = regionId + "_geocoded_addresses.csv";
    link.setAttribute("download", fNameDownload);
    document.body.appendChild(link); // Required for FF

    link.click(); // This will download the file
}