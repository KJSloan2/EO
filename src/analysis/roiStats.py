import geopandas as gpd
import numpy as np
import csv
import pandas as pd
from scipy.spatial import cKDTree, distance
import json
######################################################################################
write_parcelStats = open("%s%s" % (r"02_output\\","selectRois_parcelStats.csv"), 'w',newline='', encoding='utf-8')
writer_parcelStats = csv.writer(write_parcelStats)
writer_parcelStats.writerow([
	"ROI_ID","ROI_ZONE","PROP_CL","PROP_CL_AREA_PRCT",
	"LSTF_MEAN","NDVI_MEAN"
	])

######################################################################################
ndviRanges_ = [
	[-2,-0.28],[-0.28,0.015],
	[0.015,0.14],[0.14,0.18],
	[0.18,0.27],[0.27,0.36],
	[0.36,0.74],[0.74,2]
]

data_l8 = json.load(open("%s%s" % (r"02_output\\","temporal_selectRois.json")))
for roiKey,roiObj in data_l8.items():
	#data_naip = json.load(open("%s%s" % (r"02_output\\","naip_roi_75211_2022.json")))

	roiZone = roiObj["zone"]
	l8_coords = roiObj["coords"]
	l8_lstfMean = roiObj["lstf_mean"]
	l8_ndviMean = roiObj["ndvi_mean"]
	parcels_coords = roiObj["parcels"]["coords"]
	parcels_area = roiObj["parcels"]["area"]
	parcels_propCl = roiObj["parcels"]["prop_cl"]
	area_allParcels = sum(parcels_area)

	mean_lstf = np.mean(roiObj["lstf_mean"])
	mean_ndvi = np.mean(roiObj["ndvi_mean"])

	set_propCl = list(dict.fromkeys(parcels_propCl))
	ndviClass_ = []
	for i in range(len(l8_ndviMean)):
		ndviClass = None
		ndvi = l8_ndviMean[i]
		for j in range(len(ndviRanges_)):
			if ndvi >= float(ndviRanges_[j][0])+0.01 and ndvi <= float(ndviRanges_[j][1]):
				ndviClass = j
				break
		ndviClass_.append(ndviClass)
	
	n = len(ndviClass_)
	for i in range(len(ndviRanges_)):
		idx_i = [v for v, val in enumerate(ndviClass_) if val == i]
		prct = (len(idx_i)/n)*100
		print(i,len(idx_i),n,prct)

	l8_points = []
	for coord in l8_coords:
		cx = coord[0]
		cy = coord[1]
		l8_points.append((cx,cy))

	naip_points = []
	naip_rgb = []
	
	'''for i in range(len(data_naip["coords"])):
		for j in range(len(data_naip["coords"][i])):
			cx = data_naip["coords"][i][j][0]
			cy = data_naip["coords"][i][j][1]
			naip_points.append((cx,cy))
			r = data_naip["red"][i][j]
			g = data_naip["green"][i][j]
			b = data_naip["blue"][i][j]
			naip_rgb.append([r,g,b])'''

	kdtree_l8 = cKDTree(l8_points)
	kdtree_naip = cKDTree(naip_points)

	parcelStats_ = {}
	for propClKey in set_propCl:
		parcelStats_[propClKey] = {
			"mean_rgb":[],
			"area_prct_total":None,
			"area_sqft_total":None,
			"mean_lstf":None,
			"mean_ndvi":None
		}

		idx_propClKey = [i for i, val in enumerate(parcels_propCl) if val == propClKey]
		get_propClArea = list(map(lambda idx: parcels_area[idx],idx_propClKey))
		area_propClArea = round((sum(get_propClArea)),2)
		prct_area = round(((area_propClArea/area_allParcels)*100),2)

		parcelStats_[propClKey]["area_prct_total"] = prct_area
		parcelStats_[propClKey]["area_sqft_total"] = area_propClArea

		get_coords = list(map(lambda idx: parcels_coords[idx],idx_propClKey))
		
		pool_lstfMean = []
		pool_ndviMean = []
		pool_rgb = [[],[],[]]
		for coord in get_coords:
			qx = coord[0]
			qy = coord[1]
			query_point = (qx, qy)

			cp_idx_l8 = kdtree_l8.query(query_point, k=4)
			cp_l8 = [l8_points[i] for i in cp_idx_l8[1]]
			cp_idx_l8_valid = []
			for i in range(len(cp_l8)):
				pt = cp_l8[i]
				eucDist = distance.euclidean(query_point, pt)
				if eucDist <= 0.00125:
					cp_idx_l8_valid.append(cp_idx_l8[1][i])
			if len(cp_idx_l8_valid) != 0:
				pool_lstfMean.append(np.mean(list(map(lambda idx: l8_lstfMean[idx],cp_idx_l8_valid))))
				pool_ndviMean.append(np.mean(list(map(lambda idx: l8_ndviMean[idx],cp_idx_l8_valid))))
				#pool_lstfMean.append([l8_lstfMean[i] for i in cp_idx_l8[1]])
				#pool_ndviMean.append([l8_ndviMean[i] for i in cp_idx_l8[1]])

			#cp_idx_naip = kdtree_naip.query(query_point, k=4)
			#get_rgb = naip_rgb[cp_idx_naip]
			#pool_rgb[0].append(get_rgb[0])
			#pool_rgb[1].append(get_rgb[1])
			#pool_rgb[2].append(get_rgb[2])

		parcelStats_[propClKey]["mean_lstf"] = np.mean(pool_lstfMean)
		parcelStats_[propClKey]["mean_ndvi"] = np.mean(pool_ndviMean)
		'''parcelStats_[propClKey]["mean_rgb"] = [
			np.mean(pool_rgb[0]),
			np.mean(pool_rgb[1]),
			np.mean(pool_rgb[2])
			]'''
		print(propClKey.upper(),prct_area,parcelStats_[propClKey]["mean_lstf"])
		writer_parcelStats.writerow([
			roiKey,roiZone,
			propClKey.upper(),prct_area,
			parcelStats_[propClKey]["mean_lstf"],
			parcelStats_[propClKey]["mean_ndvi"]
			])