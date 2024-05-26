//Dataset: https://developers.google.com/earth-engine/datasets/catalog/USGS_3DEP_10m#description'

var coords = [[30.246751587433387, -99.03194078292289], [30.3785471175046, -98.83013513945758]];

var point1 = coords[0];
var point2 = coords[1];

function calculateCenter(lat1, lon1, lat2, lon2) {
  var centerLat = (lat1 + lat2) / 2;
  var centerLon = (lon1 + lon2) / 2;
  return [centerLat, centerLon];
}

var mapCenter = calculateCenter(point1[1], point1[0], point2[1], point2[0]);
Map.setCenter(mapCenter[0],mapCenter[1], 10);

var roi = ee.Geometry.BBox(
  coords[0][1],coords[0][0],
  coords[1][1],coords[1][0]
  );

var dataset = ee.Image('USGS/3DEP/10m')
var elevation = dataset.select('elevation');
var elevation_clip = elevation.clip(roi);
var slope = ee.Terrain.slope(elevation);
var slope_clip = elevation.clip(roi);

Map.addLayer(elevation_clip, {min: 0, max: 3000,   palette: [
    '3ae237', 'b5e22e', 'd6e21f', 'fff705', 'ffd611', 'ffb613', 'ff8b13',
    'ff6e08', 'ff500d', 'ff0000', 'de0101', 'c21301', '0602ff', '235cb1',
    '307ef3', '269db1', '30c8e2', '32d3ef', '3be285', '3ff38f', '86e26f'
  ],
}, 'elevation_clip');
Map.addLayer(slope, {min: 0, max: 60}, 'slope');


var place_key = "fredrickberg_tx";

Export.image.toDrive({
  image: elevation_clip,
  description: 'elevation_'+place_key+'USGS_3DEP',
  folder: '3DEP',
  region: roi,
  scale: 30,
  fileFormat: 'GeoTIFF'
});

Export.image.toDrive({
  image: slope_clip,
  description: 'slope_'+place_key+'USGS_3DEP',
  folder: '3DEP',
  region: roi,
  scale: 30,
  fileFormat: 'GeoTIFF'
});