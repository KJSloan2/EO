import os
from os import listdir
from os.path import isfile, join
import time

import csv
import json

import numpy as np

import rasterio as rio
from rasterio.plot import show
######################################################################################
'''Read parameters to get analysis location, year, etc.
These parameters tell the program what files to read and how to process them'''
analysis_parameters = json.load(open("%s%s" % (r"EO/00_resources/","analysis_parameters.json")))
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
folders_output = list(listdir(r"EO/02_output/"))
if locationKey not in folders_output:
	folder_path = "%s%s" % (r"EO/02_output/",locationKey)
	os.mkdir(folder_path)
	os.mkdir("%s%s%s%s" % (r"EO/02_output/",locationKey,"/",analysis_version))
elif locationKey in folders_output:
	folder_path = "%s%s" % (r"EO/02_output/",locationKey)
	if analysis_version not in list(listdir(folder_path)):
		os.mkdir("%s%s%s%s" % (r"EO/02_output/",locationKey,"/",analysis_version))
######################################################################################
analysis_parameters["processes_tifs"] = {}
with open(r'EO/00_resources/processed_tifs.txt', 'w') as processedFiles:
	poolingWindow_size = 2
	kernel_size = 5
######################################################################################
	for files in filesToProcess:
		fName_oli = files[0]
		fName_tirs = files[1]
		fname_parsed = fName_oli.split("_")
		year = str(fname_parsed[-1].split(".")[0])
		#Bands: 'B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7'
		with rio.open("%s%s%s%s" % (r"EO/01_data/",locationKey,"/C02T1/",fName_oli)) as src_oli:
			src_width = src_oli.width
			src_height = src_oli.height
			print(f"Width: {src_width} pixels")
			print(f"Height: {src_height} pixels")

			b5_nir = src_oli.read(5)
			b4_red = src_oli.read(4)
			b3_green = src_oli.read(3)
			b2_blue = src_oli.read(2)

			src_bounds = src_oli.bounds
			#BoundingBox(left=-97.07895646117163, bottom=32.59914300847014, right=-96.63725483597005, top=32.99503055418162)
			bb_pt1 = [src_bounds[0],src_bounds[1]]
			bb_pt2 = [src_bounds[2],src_bounds[3]]
			bb_width = bb_pt2[0] - bb_pt1[0]
			bb_height = bb_pt2[1] - bb_pt1[1]

			step_width = bb_width/(src_width/poolingWindow_size)
			step_height = bb_height/(src_height/poolingWindow_size)*-1

			bb_pt3 = [bb_pt1[0],bb_pt2[1]]
			print(bb_pt3)
			#-97.07895646117163, 32.99503055418162

			print(
				f"bb_width: {bb_width}",f"bb_height: {bb_height}",
				f"step_width: {step_width}",f"step_height: {step_height}"
			)
			#bb_width: 0.4417016252015742 bb_height: 0.39588754571147433 step_width: 0.0002694945852358598 step_height: -0.0002694945852358573

		#Bands: 'ST_B10'
		with rio.open("%s%s%s%s" % (r"EO/01_data/",locationKey,"/C02T1L2/",fName_tirs)) as src_tirs:
			src_width = src_oli.width
			src_height = src_oli.height
			print(f"Width: {src_width} pixels")
			print(f"Height: {src_height} pixels")
			b9_lst = src_tirs.read(1)

			bands_pooled = {
				"coordinates":[],"lstf":[],"lstf_range":[],"ndvi":[],
			}
			
			gaussian = gaussian_kernel(kernel_size, sigma=1)
			lst_smoothed = apply_gaussian_kernel(b9_lst, gaussian)
			lst_smoothed = np.array(lst_smoothed)

			b4_red_smoothed =  np.array(apply_gaussian_kernel(b4_red, gaussian))
			b5_nir_smoothed =  np.array(apply_gaussian_kernel(b5_nir, gaussian))

			tempRanges = [
				[50,59.99],[60,69.99],[70,79.99],[80,89.99],
				[90,99.99],[100,109.99],[110,119.99],[120,129.99],
				[130,139.99]]
			
		coord_y = bb_pt3[1]
		for i in range(1,src_height-(poolingWindow_size+1),poolingWindow_size):
			bands_pooled["coordinates"].append([])
			bands_pooled["lstf"].append([])
			bands_pooled["lstf_range"].append([])
			bands_pooled["ndvi"].append([])
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

				b4_red_window = b4_red_smoothed[i:i + poolingWindow_size, j:j + poolingWindow_size]
				b4_red_windowMean = np.mean(b4_red_window)

				b5_nir_window = b5_nir_smoothed[i:i + poolingWindow_size, j:j + poolingWindow_size]
				b5_nir_windowMean = np.mean(b5_nir_window)

				ndvi = float(round(((b5_nir_windowMean - b4_red_windowMean)/(b5_nir_windowMean + b4_red_windowMean)),3))
				bands_pooled["ndvi"][-1].append(ndvi)
				coord_x+=step_width	
			coord_y+=step_height

		src_oli.close()
		src_tirs.close()
######################################################################################
		output_fname = locationKey+"_"+year+"_"+analysis_version+".json"
		processedFiles.write(f'{str(output_fname).split(".")[0]}\n')
		output_path = "%s%s%s%s%s%s" % (r"EO/02_output/",locationKey,"/",analysis_version,"/",output_fname)
		with open(output_path, "w", encoding='utf-8') as output_json:
			output_json.write(json.dumps(bands_pooled, ensure_ascii=False))
	processedFiles.close()

end_time = time.time()
duration = end_time - start_time
#Update the analysis parameters file with runtime stats
analysis_parameters["run_stats"] = {
	"start_time":start_time,
	"end_time":end_time,
	"duration":duration
	}

with open("%s%s" % (r"EO/00_resources/","analysis_parameters.json"), "w", encoding='utf-8') as output_json:
    output_json.write(json.dumps(analysis_parameters, indent=2, ensure_ascii=False))

######################################################################################
print("DONE")