document.addEventListener('DOMContentLoaded', function () {
    const { DeckGL, ColumnLayer, ScatterplotLayer } = deck;
  
    let columnLayer;
    /*function updateLayers(radius) {
      columnLayer.props.radius = radius;
      deck.setProps({ layers: [columnLayer] });
    }*/
  
    function updateLayers(radius) {
      // Create a new instance of ColumnLayer with the updated radius
      const updatedColumnLayer = new ColumnLayer({
        id: 'columnLayer',
        data: columnLayer.props.data,
        diskResolution: 2,
        radius: radius,
        elevationScale: 3000,
        getPosition: d => d.centroid,
        getFillColor: d => [d.value_normalized * 255, 100, 125, 255],
        getElevation: d => d.value_normalized
      });
    
      // Replace the existing layer with the updated one
      deck.setProps({ layers: [updatedColumnLayer] });
    }
  
    function createSlider(id, min, max, value, step, inputHandler) {
      const slider = document.createElement('input');
      slider.type = 'range';
      slider.min = min;
      slider.max = max;
      slider.value = value;
      slider.step = step;
      slider.addEventListener('input', inputHandler);
  
      document.getElementById(id).appendChild(slider);
  
      return slider;
    }
  
    function loadJSON(filePath) {
      fetch(filePath)
        .then(response => response.json())
        .then(data => {
  
          const radiusSlider = createSlider('slider1', 1, 100, 50, 1, () => {
            const radius = parseInt(radiusSlider.value);
            updateLayers(radius);
          });
  
          const calculateCenter = (coordinates) => {
            const numCoords = coordinates.length;
            const sumLat = coordinates.reduce((sum, coord) => sum + coord[1], 0);
            const sumLng = coordinates.reduce((sum, coord) => sum + coord[0], 0);
            const avgLat = sumLat / numCoords;
            const avgLng = sumLng / numCoords;
            return { latitude: avgLat, longitude: avgLng };
          };
  
          // Get the center of coordinates from the "centroid" property
          const centerCoordinates = calculateCenter(data.map(entry => entry.centroid));
  
          const normalizeValues = (data) => {
            // Extract values
            const values = data.map(entry => entry.value);
  
            // Calculate min and max values
            const minValue = Math.min(...values);
            const maxValue = Math.max(...values);
  
            const normalizedData = data.map(entry => ({
              ...entry,
              value_normalized: (entry.value - minValue) / (maxValue - minValue),
            }));
  
            return normalizedData;
          };
  
          // Apply normalization to jsonData
          const normalizedJsonData = normalizeValues(data);
  
          // Update jsonData with normalized values
          data.forEach((entry, index) => {
            Object.assign(entry, normalizedJsonData[index]);
          });
          console.log(parseInt(radiusSlider.value));
          columnLayer = new ColumnLayer({
            id: 'columnLayer',
            data: data,
            diskResolution: 2,
            radius: parseInt(radiusSlider.value),
            elevationScale: 3000,
            getPosition: d => d.centroid,
            getFillColor: d => [d.value_normalized * 255, 100, 125, 255],
            getElevation: d => d.value_normalized
          });
  
          new DeckGL({
            container: 'deck-container',
            mapStyle: 'https://basemaps.cartocdn.com/gl/dark-matter-nolabels-gl-style/style.json',
            initialViewState: {
              longitude: centerCoordinates.longitude,
              latitude: centerCoordinates.latitude,
              zoom: 10,
              maxZoom: 15,
              pitch: 60
            },
            controller: true,
            layers: [columnLayer]
          });
        })
        .catch(error => {
          console.error('Error loading JSON file', error);
        });
    }
  
    // Call the loadJSON function with the file path
    loadJSON('../data/temporalMetricsExport.json');
  });