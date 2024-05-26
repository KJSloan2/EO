import os
from os import listdir
from os.path import isfile, join

import csv
import json

import numpy as np

import rasterio as rio
from rasterio.plot import show

import time

import math
######################################################################################
'''Read parameters to get analysis location, year, etc.
These parameters tell the program what files to read and how to process them'''
analysis_parameters = json.load(open("%s%s" % (r"00_resources/","analysis_parameters.json")))
locationKey = analysis_parameters["location_key"]
yearRange = [analysis_parameters["year_start"],analysis_parameters["year_end"]]
analysis_version = analysis_parameters["analysis_version"]
start_time = time.time()
######################################################################################
def normailize_linear_instance(val,d_min,d_max):
	'''Applies linear normalization to compress a given value between zero and one'''
	return round(((val-d_min)/(d_max-d_min)),4)

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
	"""
	Apply a Gaussian kernel over a 2D array of data using a sliding window.
	Parameters: data (np.ndarray): 2D array of data. kernel (np.ndarray): Gaussian kernel.
	Returns: np.ndarray: Result of applying the Gaussian kernel over the data.
	"""
	# Pad the data
	padded_data = np.pad(data, pad_width=2, mode='constant')

	# Apply the Gaussian filter using a sliding window
	output_data = np.zeros_like(data)
	for y in range(output_data.shape[0]):
		for x in range(output_data.shape[1]):
			window = padded_data[y:y+5, x:x+5]
			output_data[y, x] = np.sum(window * kernel)

	return output_data
######################################################################################
def haversine_meters(pt1, pt2):
    # Radius of the Earth in meters
    R = 6371000
    # Convert latitude and longitude from degrees to radians'
    lat1, lon1 = pt1[0], pt1[1]
    lat2, lon2 = pt2[0], pt2[1]
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    # Haversine formula
    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    # Distance in meters
    distance = R * c
    return distance
######################################################################################
###################################################################################### 
#Set the names of all tifs to be analyized
filesToProcess = []
for year in range(yearRange[0],yearRange[1]+1,1):
	filesToProcess.append(
		[
			locationKey+"_L8_COMP_OLI_"+str(year)+".tif",
			locationKey+"_L8_ARD_TIRS_"+str(year)+".tif",
		]
	)

'''Each tif name will be added to a txt file in the resoueces folder
The txt file will inform other scipts which json files to analyize'''
######################################################################################
folders_output = list(listdir(r"02_output/"))
if locationKey not in folders_output:
	folder_path = "%s%s" % (r"02_output/",locationKey)
	os.mkdir(folder_path)
	os.mkdir("%s%s%s%s" % (r"02_output/",locationKey,"/",analysis_version))
elif locationKey in folders_output:
	folder_path = "%s%s" % (r"02_output/",locationKey)
	if analysis_version not in list(listdir(folder_path)):
		os.mkdir("%s%s%s%s" % (r"02_output/",locationKey,"/",analysis_version))
######################################################################################
analysis_parameters["processes_tifs"] = {}
#Make subdict for processed onboard land imager data
analysis_parameters["processes_tifs"]["oli"] = {}
#Make subdict for processed thermal infrared sensor data
analysis_parameters["processes_tifs"]["tirs"] = {}
#Make subdict for processed elevation and slope data
analysis_parameters["processes_tifs"]["3dep"] = {}
######################################################################################
analysis_parameters["preprocessing_output"] = []
poolingWindow_size = 2
kernel_size = 5
######################################################################################
for files in filesToProcess:
	fName_oli = files[0]
	fName_tirs = files[1]
	fname_parsed = fName_oli.split("_")
	year = str(fname_parsed[-1].split(".")[0])
	#Bands: 'B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7'
	with rio.open("%s%s%s%s" % (r"01_data/",locationKey,"/C02T1/",fName_oli)) as src_oli:
		#Make a subdict to log runtime stats for the oli data'
		start_time_oli = time.time()
		analysis_parameters["processes_tifs"]["oli"][fName_oli] = {
			"start_time":start_time_oli, "end_time":None, "duration":None}
		
		src_width = src_oli.width
		src_height = src_oli.height
		analysis_parameters["processes_tifs"]["oli"][fName_oli]["width"] = src_width
		analysis_parameters["processes_tifs"]["oli"][fName_oli]["height"] = src_width
		print(f"Width: {src_width} pixels")
		print(f"Height: {src_height} pixels")

		b5_nir = src_oli.read(5)
		b4_red = src_oli.read(4)
		b3_green = src_oli.read(3)
		b2_blue = src_oli.read(2)

		rgb_stack = np.stack((b4_red, b3_green, b2_blue), axis=-1)
		rgb_stack = rgb_stack.astype(np.float32)
		for i in range(3):
			band_min, band_max = np.percentile(rgb_stack[:, :, i], (2, 98))
			rgb_stack[:, :, i] = np.clip((rgb_stack[:, :, i] - band_min) / (band_max - band_min), 0, 1)
		
		red_8bit = rgb_stack[:, :, 0]
		green_8bit = rgb_stack[:, :, 1]
		blue_8bit = rgb_stack[:, :, 2]

		src_bounds = src_oli.bounds
		#BoundingBox(left=-97.07895646117163, bottom=32.59914300847014, right=-96.63725483597005, top=32.99503055418162)
		bb_pt1 = [src_bounds[0],src_bounds[1]]
		bb_pt2 = [src_bounds[2],src_bounds[3]]
		bb_width = bb_pt2[0] - bb_pt1[0]
		bb_height = bb_pt2[1] - bb_pt1[1]

		step_width = bb_width/(src_width/poolingWindow_size)
		step_height = bb_height/(src_height/poolingWindow_size)*-1

		bb_pt3 = [bb_pt1[0],bb_pt2[1]]
		bb_pt4 = [bb_pt2[0],bb_pt1[1]]

		analysis_parameters["processes_tifs"]["oli"][fName_oli]["bounding_box"] = {
			"points":None, "edge_1_lenght":None, "edge_2_lenght":None}
		
		analysis_parameters["processes_tifs"]["oli"][fName_oli]["bounding_box"]["points"] = [bb_pt1, bb_pt2, bb_pt3, bb_pt4]
		analysis_parameters["processes_tifs"]["oli"][fName_oli]["bounding_box"]["edge_1_lenght"] = haversine_meters(bb_pt1, bb_pt3)
		analysis_parameters["processes_tifs"]["oli"][fName_oli]["bounding_box"]["edge_1_lenght"] = haversine_meters(bb_pt1, bb_pt4)

		print(bb_pt3)
		#-97.07895646117163, 32.99503055418162

		print(
			f"bb_width: {bb_width}",f"bb_height: {bb_height}",
			f"step_width: {step_width}",f"step_height: {step_height}"
		)
		#bb_width: 0.4417016252015742 bb_height: 0.39588754571147433 step_width: 0.0002694945852358598 step_height: -0.0002694945852358573

	#Get the current time and calculate the runtime durration for processign the oli data. Add to runtime stats
	end_time_oli = time.time()
	duration_oli = end_time_oli - start_time_oli
	analysis_parameters["processes_tifs"]["oli"][fName_oli]["end_time"] = end_time_oli
	analysis_parameters["processes_tifs"]["oli"][fName_oli]["duration"] = duration_oli
######################################################################################
######################################################################################
	with rio.open("%s%s%s%s" % (r"01_data/",locationKey,"/C02T1L2/",fName_tirs)) as src_tirs:
		#Make a subdict to log runtime stats for the tirs data
		start_time_tirs = time.time()
		analysis_parameters["processes_tifs"]["tirs"][fName_tirs] = {
			"start_time":start_time_tirs, "end_time":None, "duration":None}
		
		src_width = src_oli.width
		src_height = src_oli.height
		analysis_parameters["processes_tifs"]["tirs"][fName_tirs]["width"] = src_width
		analysis_parameters["processes_tifs"]["tirs"][fName_tirs]["height"] = src_width
		print(f"Width: {src_width} pixels")
		print(f"Height: {src_height} pixels")
		b9_lst = src_tirs.read(1)

		bands_pooled = {
			"coordinates":[], "lstf":[], "lstf_range":[], "ndvi":[], "rgb":[]
		}
		
		gaussian = gaussian_kernel(kernel_size, sigma=1)
		lst_smoothed = apply_gaussian_kernel(b9_lst, gaussian)
		lst_smoothed = np.array(lst_smoothed)

		b4_red_smoothed =  np.array(apply_gaussian_kernel(b4_red, gaussian))
		b3_green_smoothed =  np.array(apply_gaussian_kernel(b3_green, gaussian))
		b2_blue_smoothed =  np.array(apply_gaussian_kernel(b2_blue, gaussian))
		b5_nir_smoothed =  np.array(apply_gaussian_kernel(b5_nir, gaussian))

		red_8bit_smoothed =  np.array(apply_gaussian_kernel(red_8bit, gaussian))
		green_8bit_smoothed =  np.array(apply_gaussian_kernel(green_8bit, gaussian))
		blue_8bit_smoothed =  np.array(apply_gaussian_kernel(blue_8bit, gaussian))

		tempRanges = [
			[50,59.99],[60,69.99],[70,79.99],[80,89.99],
			[90,99.99],[100,109.99],[110,119.99],[120,129.99],
			[130,139.99]]
		
	coord_y = bb_pt3[1]
	
	#Get the current time and calculate the runtime durration for processign the tirs data. Add to runtime stats
	end_time_tirs = time.time()
	duration_tirs = end_time_tirs - start_time_tirs
	analysis_parameters["processes_tifs"]["tirs"][fName_tirs]["end_time"] = end_time_tirs
	analysis_parameters["processes_tifs"]["tirs"][fName_tirs]["duration"] = duration_tirs
######################################################################################
######################################################################################
	for i in range(1,src_height-(poolingWindow_size+1),poolingWindow_size):
		bands_pooled["coordinates"].append([])
		bands_pooled["lstf"].append([])
		bands_pooled["lstf_range"].append([])
		bands_pooled["ndvi"].append([])
		bands_pooled["rgb"].append([])
		coord_x = bb_pt3[0]
		for j in range(1,src_width-(poolingWindow_size+1),poolingWindow_size):
			if coord_x > -96:
				print(coord_x,coord_y)

			bands_pooled["coordinates"][-1].append([coord_x,coord_y])

			lst_window = lst_smoothed[i:i + poolingWindow_size, j:j + poolingWindow_size]
			lstf = float(round((np.mean(lst_window)),3))
			bands_pooled["lstf"][-1].append(lstf)

			lstf_range = None
			for k in range(len(tempRanges)):
				tempRange = tempRanges[k]
				if tempRange[0] < lstf < tempRange[1]:
					lstf_range = k
					break

			bands_pooled["lstf_range"][-1].append(lstf_range)

			def window_mean(band,window_size):
				band_window = band[i:i + window_size, j:j + window_size]
				band_window_mean = np.mean(band_window)
				return band_window_mean

			b4_red_windowMean = window_mean(b4_red_smoothed,poolingWindow_size)
			b3_green_windowMean = window_mean(b3_green_smoothed,poolingWindow_size)
			b2_blue_windowMean = window_mean(b2_blue_smoothed,poolingWindow_size)
			b5_nir_windowMean = window_mean(b5_nir_smoothed,poolingWindow_size)
			red_8bit_windowMean = window_mean(red_8bit_smoothed,poolingWindow_size)
			green_8bit_windowMean = window_mean(green_8bit_smoothed,poolingWindow_size)
			blue_8bit_windowMean = window_mean(blue_8bit_smoothed,poolingWindow_size)

			ndvi = float(round(((b5_nir_windowMean - b4_red_windowMean)/(b5_nir_windowMean + b4_red_windowMean)),3))
			bands_pooled["ndvi"][-1].append(ndvi)

			mean_rgb = [int(red_8bit_windowMean*256), int(green_8bit_windowMean*256), int(blue_8bit_windowMean*256)]
			bands_pooled["rgb"][-1].append(mean_rgb)

			coord_x+=step_width
		coord_y+=step_height

	src_oli.close()
	src_tirs.close()
######################################################################################
	output_fname = locationKey+"_"+year+"_"+analysis_version+".json"
	output_path = "%s%s%s%s%s%s" % (r"02_output/",locationKey,"/",analysis_version,"/",output_fname)
	with open(output_path, "w", encoding='utf-8') as output_json:
		output_json.write(json.dumps(bands_pooled, ensure_ascii=False))
	analysis_parameters["preprocessing_output"].append(output_path)

end_time = time.time()
duration = end_time - start_time
#Update the analysis parameters file with runtime stats
analysis_parameters["run_stats"] = {
	"start_time":start_time,
	"end_time":end_time,
	"duration":duration
	}

with open("%s%s" % (r"00_resources/","analysis_parameters.json"), "w", encoding='utf-8') as output_json:
    output_json.write(json.dumps(analysis_parameters, indent=2, ensure_ascii=False))

######################################################################################
print("DONE")