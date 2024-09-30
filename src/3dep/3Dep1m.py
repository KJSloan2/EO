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
resampling_size = 3
locationId = "B4"
######################################################################################
script_dir = os.path.dirname(os.path.abspath(__file__))
split_dir = str(script_dir).split("/")
idx_src = split_dir.index("src")
parent_dir = split_dir[idx_src-1]
resources_path = os.path.join(parent_dir, "00_resources/")
data_path = os.path.join(parent_dir, "01_data/")
print(resources_path)

logJson = json.load(open("%s%s" % (resources_path,"A0"+"_log.json")))


'''Read parameters to get analysis location, year, etc.
These parameters tell the program what files to read and how to process them'''
'''analysis_parameters = json.load(open("%s%s" % (r"00_resources/","analysis_parameters.json")))
locationKey = analysis_parameters["location_key"]
yearRange = [analysis_parameters["year_start"],analysis_parameters["year_end"]]
analysis_version = analysis_parameters["analysis_version"]
start_time = time.time()'''
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
	Parameters: lat -- Latitude in degrees; lon -- Longitude in degrees; h -- Elevation in meters
	Returns: x, y, z -- ECEF coordinates in meters
	"""
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
#Color palette for color coding points based on elevation
palette = [
	[58, 226, 55], [181, 226, 46], [214, 226, 31], [255, 247, 5], [255, 214, 17], 
	[255, 182, 19], [255, 139, 19], [255, 110, 8], [255, 80, 13], [255, 0, 0], [222, 1, 1],
	[194, 19, 1], [6, 2, 255], [35, 92, 177], [48, 126, 243], [38, 157, 177],
	[48, 200, 226], [50, 211, 239], [59, 226, 133], [63, 243, 143], [134, 226, 111]
]
#Reverse palette order
palette = palette[::-1]
######################################################################################
def compress_and_scale(value, min_value, max_value, target_min=0, target_max=len(palette)):
	'''Performs min-max normalization to scale elevation values. Rescales normalized value
	to a target value (lenght of color palette) and returns the normalized value and index
	of the color to apply to the pixel'''
	# Step 1: Min-Max Normalization (compress between 0 and 1)
	normalized_value = (value - min_value) / (max_value - min_value)
	# Step 2: Scale to the target range (0 to 21)
	scaled_value = normalized_value * (target_max - target_min) + target_min
	# Step 3: Convert to an integer
	return [int(scaled_value),normalized_value]
######################################################################################
def haversine_meters(pt1, pt2):
	'''Calulates the distance between two geographoic points. Takes curvatrure of 
	the Earth into account.'''
	# Radius of the Earth in meters
	R = 6371000
	# Convert latitude and longitude from degrees to radians'
	lat1, lon1 = pt1[1], pt1[0]
	lat2, lon2 = pt2[1], pt2[0]
	phi1 = math.radians(lat1)
	phi2 = math.radians(lat2)
	delta_phi = math.radians(lat2 - lat1)
	delta_lambda = math.radians(lon2 - lon1)
	# Haversine formula
	a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
	c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
	coef_ft = 3.28084
	# Distance in meters
	dist_m = R * c
	dist_ft = dist_m*coef_ft
	dist_ml = round((dist_ft/5280),2)
	return {"ft":dist_ft, "m":dist_m, "ml":dist_ml}
######################################################################################
def gaussian_kernel(size, sigma=1):
	"""
	Creates a gaussian kernal.
	Parameters:
		size (int): Size of the kernel (should be odd).
		sigma (float): Standard deviation of the Gaussian distribution.
	Returns: np.ndarray: 2D array representing the Gaussian kernel.
	"""
	kernel = np.fromfunction(
		lambda x, y: (1/(2*np.pi*sigma**2)) * np.exp(-((x - size//2)**2 + (y - size//2)**2)/(2*sigma**2)),
		(size, size)
	)
	return kernel / np.sum(kernel)
######################################################################################
def apply_gaussian_kernel(data, kernel):
	"""Apply a Gaussian kernel over a 2D array of data using a sliding window.
	Parameters: data (np.ndarray): 2D array of data. kernel (np.ndarray): Gaussian kernel.
	Returns: np.ndarray: Result of applying the Gaussian kernel over the data."""
	# Pad the data
	padded_data = np.pad(data, pad_width=2, mode='constant')
	# Apply the Gaussian filter using a sliding window
	output_data = np.zeros_like(data)
	for y in range(output_data.shape[0]):
		for x in range(output_data.shape[1]):
			window = padded_data[y:y+resampling_size, x:x+resampling_size]
			output_data[y, x] = np.sum(window * kernel)

	return output_data
######################################################################################
elevationData = {"coordinates":[]}
zScaler = 0.000008983152841185062
with rio.open("%s%s%s%s" % (r"ptcloud/01_data/3DEP/","elevation_",locationId,"_USGS_3DEP_1m.tif")) as src_elevation:
	#Make a subdict to log runtime stats for the oli data'
	start_time_oli = time.time()
	'''analysis_parameters["processed_tifs"]["3dep"][locationKey+"_E-3DEP.tif"] = {
		"start_time":start_time_oli, "end_time":None, "duration":None}'''
	
	src_width = src_elevation.width
	src_height = src_elevation.height

	'''analysis_parameters["processed_tifs"]["3dep"][locationKey+"_E-3DEP.tif"]["width"] = src_width
	analysis_parameters["processed_tifs"]["3dep"][locationKey+"_E-3DEP.tif"]["height"] = src_width'''

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
	step_width = bb_width/(src_width/resampling_size)
	step_height = bb_height/(src_height/resampling_size)*-1

	bb_pt3 = [bb_pt1[0],bb_pt2[1]]

	print(step_width, step_height)

	pts = []
	b1_elevation = np.array(b1_elevation)
	pxl_dist = 2.7355724505070387
	width_ft = src_width*pxl_dist
	height_ft = src_height*pxl_dist
	print(f"Distance: {width_ft} feet")

	
with rio.open("%s%s%s%s" % (r"ptcloud/01_data/3DEP/","slope_",locationId,"_USGS_3DEP_1m.tif")) as src_slope:
	b1_slope = src_slope.read(1)

bands_pooled = {"coordinates":[],"elevation":[]}

output_geo = {
	"type": "FeatureCollection",
	"name": "Landsat 8, LST and NDVI Temportal Analysis",
	"features": []
}

output = []
coord_y = bb_pt3[1]
print(len(b1_elevation))

gaussian = gaussian_kernel(resampling_size, sigma=1)
#elevation_smoothed = apply_gaussian_kernel(b1_elevation, gaussian)
#elevation_smoothed = np.array(elevation_smoothed)
elevation_smoothed = np.array(b1_elevation)

slope_smoothed = apply_gaussian_kernel(b1_slope, gaussian)
slope_smoothed = np.array(b1_slope)

pool_b1Elevation = []
for i, (ei, si) in enumerate(zip(elevation_smoothed, slope_smoothed)):
	for j, (ej,sj) in enumerate(zip(ei, si)):
		pool_b1Elevation.append(round((ei[j]),2))

b1Elevation_min = min(pool_b1Elevation)
b1Elevation_max = max(pool_b1Elevation)
print("MIN-MAX: ", b1Elevation_min, b1Elevation_max)

pool_coords = [[],[]]

for i in range(1,src_height-(resampling_size+1),resampling_size):
	'''bands_output["coordinates"].append([])
	bands_output["lstf"].append([])
	bands_output["ndvi"].append([])
	bands_output["rgb"].append([])'''
	coord_x = bb_pt3[0]
	for j in range(1,src_width-(resampling_size+1),resampling_size):
		#bands_output["coordinates"][-1].append([round((coord_x),3),round((coord_y),3)])

		elevation_window = elevation_smoothed[i:i + resampling_size, j:j + resampling_size]
		elv = float(np.mean(elevation_window))
		elv = round((elv),2)

		try:
			coord_x+=step_width
			elv_scaled = compress_and_scale(elv, b1Elevation_min, b1Elevation_max, target_min=0, target_max=len(palette))
			color = palette[elv_scaled[0]]
			
			output.append({"x":coord_x, "y":coord_y, "z":elv*zScaler, "size":1, "color":color})
			pool_coords[0].append(coord_y)
			pool_coords[1].append(coord_x)
			'''output_geo["features"].append(
				{"type": "Feature",
					"properties": {
						"elevation":elv,
					},
					"geometry": {
						"type": "Point",
						"coordinates": [coord_x,coord_y, elv]
					}
				}
			)'''
		except Exception as e:
			print(e)
			continue
	coord_y+=step_height

print(np.mean(pool_coords[0]), np.mean(pool_coords[1]))
######################################################################################
######################################################################################
'''output_fname = locationKey+"_elevation_"+analysis_version
output_path = "%s%s%s%s%s%s%s" % (
	r"02_output/",locationKey,"/",analysis_version,"/",output_fname,".geojson")

with open(output_path, "w") as f:
	json.dump(output_geo, f)'''
######################################################################################

output_path = "%s%s" % (
	r"ptcloud/","3DEP_ptCloud.json")

with open(output_path, "w", encoding='utf-8') as output_json:
	output_json.write(json.dumps(output, ensure_ascii=False))

'''end_time = time.time()
duration = end_time - start_time
#Update the analysis parameters file with runtime stats
analysis_parameters["processed_tifs"]["3dep"] = {
	"start_time":start_time,
	"end_time":end_time,
	"duration":duration
	}

with open("%s%s" % (
	r"00_resources/","analysis_parameters.json"), "w", encoding='utf-8') as output_json:
	output_json.write(json.dumps(analysis_parameters, indent=2, ensure_ascii=False))'''
######################################################################################
print("DONE")
