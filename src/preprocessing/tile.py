import os
from os import listdir
from os.path import isfile, join

import numpy as np

import rasterio as rio
from rasterio.plot import show
from rasterio.transform import from_origin
from rasterio.windows import Window

import math

import json

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import time

from shapely.geometry import Point, Polygon

from geopy.distance import distance
from geopy.point import Point

from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

######################################################################################
locationKey = "A0"
############################### GLOBAL FUNCTIONS #####################################
######################################################################################
def list_folders(directory):
	try:
		# List all items in the given directory
		items = os.listdir(directory)
		# Filter out items that are directories
		folders = [item for item in items if os.path.isdir(os.path.join(directory, item))]
		return folders
	except Exception as e:
		print(f"Error (list_folders): {e}")
		return []
######################################################################################
def list_files(directory):
    try:
        # List all files and directories in the given directory
        files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
        return files
    except FileNotFoundError:
        print(f"Directory not found: {directory}")
        return []
    except PermissionError:
        print(f"Permission denied: {directory}")
        return []
######################################################################################
def create_folder(directory, folder_name):
	try:
		# Construct the full path of the new folder
		folder_path = os.path.join(directory, folder_name)
		# Create the folder
		os.makedirs(folder_path, exist_ok=True)
		print(f"Folder '{folder_name}' created successfully in '{directory}'.")
	except Exception as e:
		print(f"Error (create_folder): {e}")
######################################################################################
def get_tiff_dimensions(file_path):
	'''Gets the bounds and dimensions of a given geoTiff file'''
	try:
		with rio.open(file_path) as src:
			width = src.width
			height = src.height
		return width, height
	except Exception as e:
		print(f"Error (get_tiff_dimensions): {e}")
		return None
######################################################################################
def haversine_meters(pt1, pt2):
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
######################################################################################
logJson = json.load(open("%s%s" % (r"00_resources/",locationKey+"_"+"log.json")))
############################### MONGODB CONNECTION ###################################
######################################################################################
uri = ""
# Create a new client and connect to the server
#client = MongoClient(uri, server_api=ServerApi('1'))
# Send a ping to confirm a successful connection

#query = {"FEATURE_CLASS": "Airport"}

usgs_features = []

try:
	client = MongoClient(uri, server_api=ServerApi('1'))
	client.admin.command('ping')
	db = client['usgs']
	collection = db['features_tx']
	#documents = collection.find(query)
	documents = collection.find

	# Step 5: Print the documents
	for document in documents:
		#for key, value in document.items():
		#	print(key, value)
		propKeys = ['FEATURE_ID', 'FEATURE_NAME' ,'FEATURE_CLASS', 'COUNTY_NAME', 'ELEV_IN_FT']
		featureObj = {}
		for propKey in propKeys:
			featureObj[propKey] = document[propKey]
		usgs_features.append(featureObj)
		print('\n')
except Exception as e:
	print(e)
	pass

'''if features have successfully been added from the MongoDb database,
	set has_usgsFeatures to True. This controls whether to look for usgs features
	in the ROI bounding box later'''

if len(usgs_features) != 0:
	has_usgsFeatures = True
else:
	has_usgsFeatures = False
######################################################################################
################################ TILE RASTER #########################################
######################################################################################
def update_point(pt, movement):
	latitude, longitude = (pt[0], pt[1])
	distance_east_meters, distance_south_meters = (movement[1], movement[0])
	# Create a Point object for the starting location
	start_point = Point(latitude, longitude)
	# Move the point to the east (90 degrees) by the specified distance
	east_point = distance(meters=distance_east_meters).destination(point=start_point, bearing=90)
	# Move the resulting point to the south (180 degrees) by the specified distance
	final_point = distance(meters=distance_south_meters).destination(point=east_point, bearing=180)
	return final_point.latitude, final_point.longitude
######################################################################################
######################################################################################
'''Create a list of files from the given data directory
Read each file name, check if it is a .tif.
If file is a tif, store file year. Sort years, log start and end year'''
files = list_files("%s%s" % (r"01_data/", locationKey))
years = []
for f in files:
	f_split = f.split(".")
	if f_split[-1] == "tif":
		#print(f_split)
		years.append(int((f_split[0].split("_"))[1]))
years_argSort = np.argsort(years)
year_start = years[years_argSort[0]]
year_end = years[years_argSort[-1]]
years_sorted = list(map(lambda idx: years[idx], years_argSort))
logJson["year_start"] = year_start
logJson["year_end"] = year_end

data_dir_path = "%s%s%s" % (r"01_data/", locationKey, "/tiles/")
tile_folders = list_folders(data_dir_path)
for year in years:
	# Check that each year of data has a folder created.
	if str(year) not in tile_folders:
		# If a folder for the year does not exist, make one
		dirpath_year = data_dir_path + "/" + str(year)
		create_folder(data_dir_path, str(year))
		create_folder(dirpath_year, "jpgs")
		create_folder(dirpath_year, "geoTiffs")
	##################################################################################
	logJson['tiles'][year] = {}
	fName_oli = locationKey + "_" + str(year) + ".tif"
	cellsize = 300
	with rio.open("%s%s%s%s" % (r"01_data/", locationKey, "/", fName_oli)) as src:
		src_crs = src.crs
		src_width = src.width
		src_height = src.height
		print(f"Width: {src_width} pixels")
		print(f"Height: {src_height} pixels")
		print(f"Coordinate Reference System: {src_crs}")

		tiles_shape = [math.floor(src_width / cellsize), math.floor(src_height / cellsize)]
		print(f"Cells in X and Y: {tiles_shape}")
		src_bounds = src.bounds

		# bb_pt1: SW
		bb_pt1 = [src_bounds[0], src_bounds[1]]
		# bb_pt2: NE
		bb_pt2 = [src_bounds[2], src_bounds[3]]
		# bb_pt3: SE
		bb_pt3 = [bb_pt1[0], bb_pt2[1]]
		# bb_pt4: NW
		bb_pt4 = [bb_pt2[0], bb_pt1[1]]

		#print(bb_pt1, bb_pt2, bb_pt3, bb_pt4)
		bb_width = bb_pt2[0] - bb_pt1[0]
		bb_height = bb_pt2[1] - bb_pt1[1]

		bb_height = haversine_meters(bb_pt1, bb_pt3)["m"]
		bb_width = haversine_meters(bb_pt1, bb_pt4)["m"]

		metersPerPixelWidth = float(bb_width / src_width)
		metersPerPixelHeight = float(bb_height / src_height)

		movement = [(metersPerPixelHeight * cellsize), (metersPerPixelWidth * cellsize)]
		
		step_width = bb_width / (src_width / cellsize)
		step_height = bb_height / (src_height / cellsize) * -1

		print(movement)
		print(tiles_shape)

		lat_start = bb_pt3[1]
		lon_start = bb_pt3[0]
		for i in range(tiles_shape[1]):
			iIdx = i * cellsize
			for j in range(tiles_shape[0]):
				jIdx = j * cellsize
				bb_pt_nw = [lat_start, lon_start]
				bb_pt_se = update_point(bb_pt_nw, movement)
				bb_pt_sw = [bb_pt_se[0], bb_pt_nw[1]]
				bb_pt_ne = [bb_pt_nw[0], bb_pt_se[1]]

				print([lon_start, lat_start])
				print([bb_pt_se[1], bb_pt_se[0]])

				lon_start = bb_pt_se[1]

				# Make a shapley polygon with the bounding box coordinates
				bb_polygon = Polygon([
					(bb_pt_nw[0], bb_pt_nw[1]),
					(bb_pt_ne[0], bb_pt_ne[1]),
					(bb_pt_se[0], bb_pt_se[1]),
					(bb_pt_sw[0], bb_pt_sw[1])
				])
				
				if has_usgsFeatures:
					for featureObj in usgs_features:
						pt = Point(featureObj['PRIM_LAT_DEC'], featureObj['PRIM_LON_DEC'])

				bands = []
				for band_idx in range(1, src.count + 1):
					band = src.read(band_idx)
					cell = np.array(band[iIdx:iIdx + cellsize, jIdx:jIdx + cellsize])
					cell_reshape = cell.reshape(cell.shape)
					bands.append(cell_reshape.reshape(cell.shape))
				band_data = np.stack(bands, axis=0)

				bands_viz = []
				for band_idx in [4, 3, 2]:
					band = src.read(band_idx)
					cell = np.array(band[iIdx:iIdx + cellsize, jIdx:jIdx + cellsize])

					# Histogram equalization (optional)
					h_, bin_ = np.histogram(cell[np.isfinite(cell)].flatten(), 3000, density=True)
					cdf = h_.cumsum()  # cumulative distribution function
					cdf = 3000 * cdf / cdf[-1]  # normalize

					band_equalized = np.interp(cell.flatten(), bin_[:-1], cdf)
					band_equalized = band_equalized.reshape(cell.shape)

					bands_viz.append(band_equalized)

				# Stack the list of bands into a NumPy array and then perform the division
				band_data_viz = np.stack(bands_viz, axis=0) / 3000
				band_data_viz = band_data_viz.clip(0, 1)
				band_data_viz = np.transpose(band_data_viz, [1, 2, 0])

				band_data = band_data.clip(0, 1)
				band_data = np.transpose(band_data, [1, 2, 0])

				plt.axis('off')

				tileId = str(i) + "-" + str(j)

				logJson['tiles'][year][tileId] = {
					"geometry": {"pt_nw": bb_pt_nw, "pt_ne": bb_pt_ne, "pt_se": bb_pt_se, "pt_sw": bb_pt_sw}
				}
				
				window = Window(jIdx, iIdx, cellsize, cellsize)
				transform = src.window_transform(window)
				tiff_output_path = "%s%s%s" % (data_dir_path, str(year) + "/geoTiffs/", locationKey + "_" + str(year) + "_" + tileId + ".tif")
				
				with rio.open(
					tiff_output_path,
					"w",
					driver="GTiff",
					height=cellsize,
					width=cellsize,
					count=src.count,
					dtype=band_data.dtype,
					crs=src.crs,
					transform=transform,
				) as dst:
					dst.write(band_data.transpose((2, 0, 1)))

				jpg_output_path = "%s%s%s" % (data_dir_path, str(year) + "/jpgs/", locationKey + "_" + str(year) + "_" + tileId + ".jpg")
				
				plt.imshow(band_data_viz, interpolation='nearest')
				plt.savefig(jpg_output_path, format='jpg', bbox_inches='tight', pad_inches=0, dpi=cellsize)

				plt.close()

			lon_start = bb_pt3[0]
			lat_start = bb_pt_se[0]

with open("%s%s" % (r"00_resources/",locationKey+"_"+"log.json"), "w", encoding='utf-8') as output_json:
	output_json.write(json.dumps(logJson, indent=2, ensure_ascii=False))
