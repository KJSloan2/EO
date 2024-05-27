import os
from os import listdir
from os.path import isfile, join

import time
import math
import json

import numpy as np

import rasterio as rio
from rasterio.plot import show
######################################################################################
'''Read parameters to get analysis location, year, etc.
These parameters tell the program what files to read and how to process them'''
analysis_parameters = json.load(open("%s%s" % (r"00_resources/","analysis_parameters.json")))
locationKey = analysis_parameters["location_key"]
yearRange = [analysis_parameters["year_start"],analysis_parameters["year_end"]]
analysis_version = analysis_parameters["analysis_version"]
start_time = time.time()
######################################################################################
def get_tiff_dimensions(file_path):
	'''Gets the bounds and dimensions of a given geoTiff file'''
	try:
		with rio.open(file_path) as src:
			width = src.width
			height = src.height
		return width, height
	except Exception as e:
		print(f"Error: {e}")
		return None
######################################################################################
def geodetic_to_ecef(lat, lon, h):
    """
    Convert geodetic coordinates to ECEF.
    
    Parameters:
    lat -- Latitude in degrees
    lon -- Longitude in degrees
    h -- Elevation in meters
    
    Returns:
    x, y, z -- ECEF coordinates in meters
    """
    # Constants
    a = 6378137.0  # WGS-84 Earth semimajor axis (meters)
    f = 1 / 298.257223563  # WGS-84 flattening factor
    e2 = 2 * f - f ** 2  # Square of eccentricity

    # Convert latitude and longitude from degrees to radians
    lat_rad = math.radians(lat)
    lon_rad = math.radians(lon)

    # Calculate prime vertical radius of curvature
    N = a / math.sqrt(1 - e2 * math.sin(lat_rad) ** 2)

    # Calculate ECEF coordinates
    x = (N + h) * math.cos(lat_rad) * math.cos(lon_rad)
    y = (N + h) * math.cos(lat_rad) * math.sin(lon_rad)
    z = (N * (1 - e2) + h) * math.sin(lat_rad)

    return x, y, z
######################################################################################
######################################################################################
#Set the names of all tifs to be analyized
filesToProcess = []
for year in range(yearRange[0],yearRange[1]+1,1):
	filesToProcess.append(
		[
			locationKey+"_E-3DEP.tif",
			locationKey+"_S-3DEP.tif",
		]
	)

poolingWindow_size = 1

with rio.open("%s%s%s%s" % (r"01_data/",locationKey,"/3DEP/",locationKey+"_E-3DEP.tif")) as src_elevation:
	#Make a subdict to log runtime stats for the oli data'
	start_time_oli = time.time()
	analysis_parameters["processes_tifs"]["3dep"][locationKey+"_E-3DEP.tif"] = {
		"start_time":start_time_oli, "end_time":None, "duration":None}
	
	src_width = src_elevation.width
	src_height = src_elevation.height

	analysis_parameters["processes_tifs"]["3dep"][locationKey+"_E-3DEP.tif"]["width"] = src_width
	analysis_parameters["processes_tifs"]["3dep"][locationKey+"_E-3DEP.tif"]["height"] = src_width

	print(f"Width: {src_width} pixels")
	print(f"Height: {src_height} pixels")

	b1_elevation = src_elevation.read(1)
	
	#Get the bo bounds of the geotif
	src_bounds = src_elevation.bounds

	#Get the boundining box (bb) points and calc the bb width and height
	bb_pt1 = [src_bounds[0],src_bounds[1]]
	bb_pt2 = [src_bounds[2],src_bounds[3]]
	bb_width = bb_pt2[0] - bb_pt1[0]
	bb_height = bb_pt2[1] - bb_pt1[1]
	
	#Calculate the stepsize btwn pixels based on pooling window size
	step_width = bb_width/(src_width/poolingWindow_size)
	step_height = bb_height/(src_height/poolingWindow_size)*-1

	bb_pt3 = [bb_pt1[0],bb_pt2[1]]

with rio.open("%s%s%s%s" % (r"01_data/",locationKey,"/3DEP/",locationKey+"_S-3DEP.tif")) as src_slope:
	b1_slope = src_slope.read(1)

bands_pooled = {
	"coordinates":[],
	"elevation":[]
}

output_geo = {
	"type": "FeatureCollection",
	"name": "Landsat 8, LST and NDVI Temportal Analysis",
	"features": []
}

coord_y = bb_pt3[1]
for i, (ei, si) in enumerate(zip(b1_elevation, b1_slope)):
	coord_x = bb_pt3[0]
	bands_pooled["coordinates"].append([])
	bands_pooled["elevation"].append([])
	for j, (ej,sj) in enumerate(zip(ei, si)):
		elv = geodetic_to_ecef(coord_y, coord_x, float(ej))[2]
		bands_pooled["elevation"][-1].append(float(ej))
		bands_pooled["coordinates"][-1].append([coord_x,coord_y])

		coord_x+=step_width

		output_geo["features"].append(
			{"type": "Feature",
				"properties": {
					"elevation":elv,
				},
				"geometry": {
					"type": "Point",
					"coordinates": [coord_x,coord_y, elv]
				}
			}
		)

	coord_y+=step_height
######################################################################################
######################################################################################
output_fname = locationKey+"_elevation_"+analysis_version
output_path = "%s%s%s%s%s%s%s" % (
	r"02_output/",locationKey,"/",analysis_version,"/",output_fname,".geojson")

with open(output_path, "w") as f:
    json.dump(output_geo, f)
######################################################################################
output_fname = locationKey+"_elevation_"+analysis_version
output_path = "%s%s%s%s%s%s%s" % (
	r"02_output/",locationKey,"/",analysis_version,"/",output_fname,".json")

with open(output_path, "w", encoding='utf-8') as output_json:
	output_json.write(json.dumps(bands_pooled, ensure_ascii=False))

end_time = time.time()
duration = end_time - start_time
#Update the analysis parameters file with runtime stats
analysis_parameters["processes_tifs"]["3dep"] = {
	"start_time":start_time,
	"end_time":end_time,
	"duration":duration
	}

with open("%s%s" % (
	r"00_resources/","analysis_parameters.json"), "w", encoding='utf-8') as output_json:
	
	output_json.write(json.dumps(analysis_parameters, indent=2, ensure_ascii=False))

######################################################################################
print("DONE")