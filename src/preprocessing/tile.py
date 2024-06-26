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
analysis_parameters = json.load(open("%s%s" % (r"00_resources/","analysis_parameters.json")))
analysis_parameters_tiles = analysis_parameters['tiles']
######################################################################################
locationKey = "transPecos_tx"
years = [2013]
dir_path = "%s%s%s" % (r"01_data/", locationKey, "/C02T1/tiles/")
tile_folders = list_folders(dir_path)
print(tile_folders)
######################################################################################
cellsize = 1000
for year in years:

	if str(year) not in tile_folders:
		create_folder(dir_path, str(year))

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

		bb_width = bb_pt2[0] - bb_pt1[0]
		bb_height = bb_pt2[1] - bb_pt1[1]

		step_width = bb_width / (src_width / cellsize)
		step_height = bb_height / (src_height / cellsize) * -1
	######################################################################################
		coord_y = bb_pt3[1]
		for i in range(cell_shape[1]):
			coord_x = bb_pt3[0]
			iIdx = i * cellsize
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
				output_fName = tileId + ".tif"

				analysis_parameters_tiles[locationKey][year][tileId] = {
					"geometry": {"pt_1":bb_pt1, "pt_2":bb_pt2, "pt_3":bb_pt3, "pt_4":bb_pt4}
				}
				
				transform = from_origin(0, cellsize, 1, 1)
				output_path = "%s%s%s" % (dir_path, str(year)+"/", output_fName)

				with rio.open( 
					output_path,
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

				jpg_output_path = output_path.replace('.tif', '.jpg')
				plt.savefig(jpg_output_path, format='jpg', bbox_inches='tight', pad_inches=0, dpi=300)

				plt.pause(0.05)  # Pause for 0.25 seconds
				plt.close()

				coord_x += cellsize
			coord_y += cellsize
######################################################################################
with open("%s%s" % (r"00_resources/","analysis_parameters.json"), "w", encoding='utf-8') as output_json:
	output_json.write(json.dumps(analysis_parameters, indent=2, ensure_ascii=False))
######################################################################################