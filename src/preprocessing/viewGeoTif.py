import os
from os import listdir
from os.path import isfile, join

import csv
import json

import numpy as np

import rasterio as rio
from rasterio.plot import show
from rasterio.transform import from_origin

import time

import math

import matplotlib.pyplot as plt
import matplotlib.patches as patches

######################################################################################
######################################################################################
def get_tiff_dimensions(file_path):
	try:
		with rio.open(file_path) as src:
			width = src.width
			height = src.height
		return width, height
	except Exception as e:
		print(f"Error: {e}")
		return None
######################################################################################
locationKey = "transPecos_tx"
fName_oli = "trans_pecos_L8_COMP_OLI_2013.tif"

cellsize = 500
path = r"01_data/transPecos_tx/C02T1/tiles/0-0_.tif"
#with rio.open("%s%s%s%s" % (r"01_data/",locationKey,"/C02T1/",fName_oli)) as src_oli:
with rio.open(path) as src_oli:
	src_crs = src_oli.crs
	src_width = src_oli.width
	src_height = src_oli.height
	print(f"Width: {src_width} pixels")
	print(f"Height: {src_height} pixels")
	print(f"Coordinate Reference System: {src_crs}")

	src_bounds = src_oli.bounds

	bb_pt1 = [src_bounds[0],src_bounds[1]]
	bb_pt2 = [src_bounds[2],src_bounds[3]]
	bb_pt3 = [bb_pt1[0],bb_pt2[1]]
	bb_pt4 = [bb_pt2[0],bb_pt1[1]]

	bb_width = bb_pt2[0] - bb_pt1[0]
	bb_height = bb_pt2[1] - bb_pt1[1]
	
	coord_y = bb_pt3[1]

	step_width = bb_width/(src_width/cellsize)
	step_height = bb_height/(src_height/cellsize)*-1
	
	bands = []
	for band_idx in [1, 2, 3]:
		band = src_oli.read(band_idx)
		cell = np.array(band)
		
		h_, bin_ = np.histogram(cell[np.isfinite(cell)].flatten(), 2000, density=True) 
		cdf = h_.cumsum() # cumulative distribution function
		cdf = 2000 * cdf / cdf[-1] # normalize

		band_equalized = np.interp(cell.flatten(), bin_[:-1], cdf)
		band_equalized = band_equalized.reshape(cell.shape)
		
		bands.append(band_equalized)

	band_data = np.stack(bands, axis=0 )

	band_data = band_data/3000
	band_data = band_data.clip(0, 1)
	band_data = np.transpose(band_data,[1,2,0])
	plt.imshow(band_data, interpolation='nearest')

	#plt.savefig('test.jpg', dpi=300, bbox_inches='tight')
	plt.show()
