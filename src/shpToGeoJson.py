import geopandas as gpd
######################################################################################
# Load the shapefile
fName = "Dallas_Structures.shx"
shapefile_path = "%s%s" % (r"01_data\shapefiles\\",fName)
gdf = gpd.read_file(shapefile_path)

# Convert to GeoJSON
geojson_str = gdf.to_json()

geojson_file = "%s%s%s" % (r"01_data\feature_collections\\",str(fName.split(".")[0]),".geojson")
with open(geojson_file, "w") as f:
    f.write(geojson_str)
######################################################################################
print("DONE")