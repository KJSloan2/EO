import geopandas as gpd
from shapely.geometry import Point, Polygon

import numpy as np
import csv
import pandas as pd
from scipy.spatial import cKDTree
import json


json_temporal = json.load(open("%s%s" % (r"02_output\\","DFW_2015-2022.json")))
lstf_mean = json_temporal["lstf_mean"]

df_parcels = pd.read_csv(str("%s%s" % (r"02_output\\","parcelData_filtered.csv")),encoding="utf-8")
#OBJECTID,PROP_CL,PROP_CAT,BLDG_CL,AREA_FT,X,Y
parcels_objid = list(df_parcels["OBJECTID"])
parcels_propCl = list(df_parcels["PROP_CL"])
parcels_propCt = list(df_parcels["PROP_CT"])
parcels_bldgCl = list(df_parcels["BLDG_CL"])
parcels_area = list(df_parcels["AREA_FT"])
parcels_x = list(df_parcels["LON"])
parcels_y = list(df_parcels["LAT"])

l8_points = []
lstf_mean = []
for i in range(len(json_temporal["coord"])):
	for j in range(len(json_temporal["coord"][i])):
		#-97.07883979540574, 32.994986835666516
		cx = json_temporal["coord"][i][j][0]
		cy = json_temporal["coord"][i][j][1]
		l8_points.append((cx,cy))
		lstf_mean.append(json_temporal["lstf_mean"][i][j])
                                                                                                                                                 
kdtree = cKDTree(l8_points)

dataOut_fileName = "parcelStats.csv"
write_dataOut = open("%s%s" % (r"02_output\\",dataOut_fileName), 'w',newline='', encoding='utf-8')
writer_dataOut = csv.writer(write_dataOut)
writer_dataOut.writerow(["OBJECTID","PROP_CL","PROP_CT","BLDG_CL","AREA_FT","LON","LAT","LST_F_MEAN"])
for i in range(len(parcels_objid)):
	qx = parcels_x[i]
	qy = parcels_y[i]
	query_point = (qx, qy)

	cp_idx = kdtree.query(query_point)[1]
	#closest_point = parcel_centroids[closest_point_index]
	lstFMean = lstf_mean[cp_idx]
	if len(parcels_bldgCl[i]) <= 2:
		bldg_cl = "RESIDENTIAL"
	else:
		bldg_cl = parcels_bldgCl[i]
	print(parcels_objid[i])
	writer_dataOut.writerow([
		parcels_objid[i],
		parcels_propCl[i],
		parcels_propCt[i],
		bldg_cl,
		parcels_area[i],
		qx,qy,
		lstFMean
		])
	
print("DONE")