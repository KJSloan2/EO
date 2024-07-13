import os
from os import listdir
from os.path import isfile, join

import numpy as np

import rasterio as rio
from rasterio.plot import show
from rasterio.transform import from_origin

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
		print(f"An error occurred: {e}")
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
		print(f"An error occurred: {e}")
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
def update_point(pt, movement):
	latitude, longitude = (pt[0], pt[1])
	distance_east_meters, distance_south_meters = (movement[0], movement[1])
	# Create a Point object for the starting location
	start_point = Point(latitude, longitude)
	# Move the point to the east (90 degrees) by the specified distance
	east_point = distance(meters=distance_east_meters).destination(point=start_point, bearing=90)
	# Move the resulting point to the south (180 degrees) by the specified distance
	final_point = distance(meters=distance_south_meters).destination(point=east_point, bearing=180)
	return final_point.latitude, final_point.longitude
######################################################################################
################################# GET PARAMETERS #####################################
######################################################################################
analysis_parameters = json.load(open("%s%s" % (r"00_resources/","analysis_parameters.json")))
analysis_parameters_tiles = analysis_parameters['tiles']
######################################################################################
locationKey = "transPecos_tx"
years = [2013]
dir_path = "%s%s%s" % (r"01_data/", locationKey, "/C02T1/tiles/")
tile_folders = list_folders(dir_path)
######################################################################################
############################### MONGODB CONNECTION ###################################
######################################################################################
uri = "mongodb+srv://kjsloan2:dji3iniMpResidi0ZdrOne@cluster0.ql0cic1.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
# Create a new client and connect to the server
client = MongoClient(uri, server_api=ServerApi('1'))
# Send a ping to confirm a successful connection

#query = {"FEATURE_CLASS": "Airport"}
analysis_parameters = json.load(open("%s%s" % (r"00_resources/","analysis_parameters.json")))

usgs_features = []
try:
	client.admin.command('ping')
	db = client['usgs']
	collection = db['features_tx']
	#documents = collection.find(query)
	documents = collection.find

	# Step 5: Print the documents
	for document in documents:
		'''for key, value in document.items():
			print(key, value)'''
		propKeys = ['FEATURE_ID', 'FEATURE_NAME' ,'FEATURE_CLASS', 'COUNTY_NAME', 'ELEV_IN_FT']
		featureObj = {}
		for propKey in propKeys:
			featureObj[propKey] = document[propKey]
		usgs_features.append(featureObj)

		print('\n')
except Exception as e:
	print(e)

'''if features have successuflly been added from the MongoDb database,
	set has_usgsFeatures to True. This controls wheather to look for usgs features
	in the ROI bounding box later'''

if len(usgs_features) != 0:
	has_usgsFeatures = True
else:
	has_usgsFeatures = False
######################################################################################
################################ TILE RASTER #########################################
######################################################################################
cellsize = 1000
for year in years:

	if str(year) not in tile_folders:
		dirpath_year = dir_path+"/"+str(year)
		create_folder(dir_path, str(year) )
		create_folder(dirpath_year, "jpgs")
		create_folder(dirpath_year, "geoTiffs")


	analysis_parameters_tiles[locationKey] = {year:{}}
	fName_oli = locationKey+"_L8_COMP_OLI_"+str(year)+".tif"
	with rio.open("%s%s%s%s" % (r"01_data/", locationKey, "/C02T1/", fName_oli)) as src_oli:
		src_crs = src_oli.crs
		src_width = src_oli.width
		src_height = src_oli.height
		print(f"Width: {src_width} pixels")
		print(f"Height: {src_height} pixels")
		print(f"Coordinate Reference System: {src_crs}")

		cell_shape = [math.floor(src_width / cellsize), math.floor(src_height / cellsize)]
		print(f"Cells in X and Y: {cell_shape}")
		src_bounds = src_oli.bounds

		bb_pt1 = [src_bounds[0], src_bounds[1]]
		bb_pt2 = [src_bounds[2], src_bounds[3]]
		bb_pt3 = [bb_pt1[0], bb_pt2[1]]
		bb_pt4 = [bb_pt2[0], bb_pt1[1]]

		#print(bb_pt1, bb_pt2, bb_pt3, bb_pt4)

		bb_width = bb_pt2[0] - bb_pt1[0]
		bb_height = bb_pt2[1] - bb_pt1[1]

		distEW = haversine_meters(bb_pt1, bb_pt4)["m"]
		distNS = haversine_meters(bb_pt1, bb_pt3)["m"]
		print(distEW, distNS)

		step_width = bb_width / (src_width / cellsize)
		step_height = bb_height / (src_height / cellsize) * -1
	######################################################################################

		coord_y = bb_pt3[1]
		for i in range(cell_shape[1]):
			#coord_x reset to x val of pt3 at start of new i loop
			coord_x = bb_pt3[0]
			iIdx = i * cellsize
			cell_pt1 = [coord_x, coord_y]
			cell_pt2 = [coord_x+cellsize, coord_y]
			cell_pt3 = [coord_x+cellsize, coord_y+cellsize]
			cell_pt4 = [coord_x, coord_y+cellsize]

			#make a shapley polygon with the bounding box coodinates
			bb_polygon = Polygon([
				(cell_pt1[0],cell_pt1[1]),
				(cell_pt2[0],cell_pt2[1]),
				(cell_pt3[0],cell_pt3[1]),
				(cell_pt4[0],cell_pt4[1])
				])
			
			#iterate over usgs features. Test if feature is in bb_polygon
			if has_usgsFeatures == True:
				for  featureObj in usgs_features:
					pt = Point(featureObj['PRIM_LAT_DEC'], featureObj['PRIM_LON_DEC'])
			for j in range(cell_shape[0]):
				jIdx = j * cellsize
				bands = []
				for band_idx in [1, 2, 3]:
					band = src_oli.read(band_idx)
					cell = np.array(band[iIdx:iIdx + cellsize, jIdx:jIdx + cellsize])

					h_, bin_ = np.histogram(cell[np.isfinite(cell)].flatten(), 3000, density=True)
					cdf = h_.cumsum()  # cumulative distribution function
					cdf = 3000 * cdf / cdf[-1]  # normalize

					band_equalized = np.interp(cell.flatten(), bin_[:-1], cdf)
					band_equalized = band_equalized.reshape(cell.shape)

					bands.append(band_equalized)

				band_data = np.stack(bands, axis=0)

				band_data = band_data / 3000
				band_data = band_data.clip(0, 1)
				band_data = np.transpose(band_data, [1, 2, 0])

				plt.imshow(band_data, interpolation='nearest')
				plt.axis('off')

				tileId = str(i) + "-" + str(j)

				analysis_parameters_tiles[locationKey][year][tileId] = {
					"geometry": {"pt_1":cell_pt1, "pt_2":cell_pt2, "pt_3":cell_pt3, "pt_4":cell_pt4}
				}
				
				transform = from_origin(0, cellsize, 1, 1)
				tiff_output_path = "%s%s%s" % (dir_path, str(year)+"/geoTiffs/", locationKey+"_"+str(year)+"_"+tileId+".tif")

				with rio.open( 
					tiff_output_path,
					'w',
					driver='GTiff',
					height=cellsize,
					width=cellsize,
					count=len(bands),
					dtype=band_data.dtype,
					crs=src_crs,
					transform=transform
				) as dst:
					for band_idx, band in enumerate(bands, start=1):
						dst.write(band, band_idx)

				#jpg_output_path = output_path.replace('.tif', '.jpg')
				jpg_output_path = "%s%s%s" % (dir_path, str(year)+"/jpgs/", locationKey+"_"+str(year)+"_"+tileId + ".jpg")
				plt.savefig(jpg_output_path, format='jpg', bbox_inches='tight', pad_inches=0, dpi=300)

				plt.pause(0.05)  # Pause for 0.25 seconds
				plt.close()

				coord_x += cellsize
			coord_y += cellsize
######################################################################################
################################ UPDATE PARAMETERS ###################################
######################################################################################
with open("%s%s" % (r"00_resources/","analysis_parameters.json"), "w", encoding='utf-8') as output_json:
	output_json.write(json.dumps(analysis_parameters, indent=2, ensure_ascii=False))