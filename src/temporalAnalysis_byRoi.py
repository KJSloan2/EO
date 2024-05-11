import json
from shapely.geometry import Point, Polygon
import re
import numpy as np
import csv
import pandas as pd
import fiona
from scipy.spatial import cKDTree, distance

analysis_version = "V6"
locationKey = "dallasTx"
data_path = "%s%s%s%s%s" % (r"02_output\locations\\",locationKey,"\\",analysis_version,"\\")
######################################################################################
######################################################################################
'''
	Construct filter polygons for specified tabulation areas or custom geometries.
	Input: geojson of geographic boundaries
	Output: Object with containers for aggregating specidied data categories and 
			filter geometry as shapely.geometry Polygon
'''
fPath_referenceGeometry = r"00_resources\geographic_references\DallasZipCodes_2018.geojson"

#target_geoids = [75247, 75246, 75237,75225, 75080, 75211, 75208, 75217, 75204, 75225, 75080, 75244, 75232]
target_geoids = [75211, 75208]
rois_ = {}
with fiona.open(fPath_referenceGeometry) as fc_referenceGeometry:
	for feature in fc_referenceGeometry:
		geoid = feature["properties"]["ZipCode"]
		if geoid in target_geoids:
			geometry_coordinates = []
			if feature["geometry"]["type"] == "Polygon":
				geometry_coordinates.append([])
				for i in range(len(feature["geometry"]["coordinates"][0])):
					coordinate = feature["geometry"]["coordinates"][0][i]
					#-96.7787125437603, 32.7923936288935
					cx = float(coordinate[0])
					cy = float(coordinate[1])
					geometry_coordinates[-1].append([cx,cy])
					#print("ROI POLYGON: ",[cx,cy])

			elif feature["geometry"]["type"] == "MultiPolygon":
				multiPolygon_coordinates = feature["geometry"]["coordinates"]
				for polygon in multiPolygon_coordinates:
					geometry_coordinates.append([])
					for coordinate in polygon[0]:
						cx = float(coordinate[0])
						cy = float(coordinate[1])
						geometry_coordinates[-1].append([cx,cy])


			rois_[geoid] = {
				"geometry_type":feature["geometry"]["type"],
				"zone":None,
				"polygon":geometry_coordinates,
				"lstf_mean":[], "ndvi_mean":[],
				"lstn_delta":[], "lstf_delta":[],
				"ndvi_delta":[], "ndvi_class":[],
				"points":[], "kdTree":None,
				"parcels":{
					"prop_cl":[], "prop_ct":[], "bldg_cl":[],
					"area":[], "coords":[]
				}
			}
			print(geoid)
######################################################################################		
output_filteredTemporalData = {
	"type": "FeatureCollection",
	"name": "Filtered Landsat 8, LST and NDVI Temportal Analysis",
	"features": []
}

fPath_temporalData = r"02_output\locations\dallasTx\V4\dallasTx_2015-2023_V4.geojson"
with fiona.open(fPath_temporalData) as fc_temporalData:
	for feature in fc_temporalData:
		coordinate = feature["geometry"]["coordinates"]
		cx = coordinate[0]
		cy = coordinate[1]
		l8_point = Point([cx,cy])
		properties = feature["properties"]
		
		for geoid,roiObj in rois_.items():
			pt_isWithin = 0
			for geometry in roiObj["polygon"]:
				if l8_point.within(Polygon(geometry)):
					pt_isWithin+=1
			if pt_isWithin > 0:
				roiObj["points"].append([cx,cy])
				roiObj["lstf_mean"].append(properties["lstf_mean"])
				roiObj["ndvi_mean"].append(properties["ndvi_mean"])
				#roiObj["lstf_delta"].append(properties["lstf_delta"])
				#roiObj["ndvi_delta"].append(properties["ndvi_delta"])
				#break
				output_filteredTemporalData["features"].append(
					{"type": "Feature",
						"properties": {
							"zipCode":geoid,
							"lstf_mean":properties["lstf_mean"],
							"lstf_slope":properties["lstf_slope"],
							"ndvi_mean":properties["ndvi_mean"],
							"ndvi_slope":properties["ndvi_slope"]
						},
						"geometry": {
							"type": "Point",
							"coordinates": coordinate
						}
					}
				)
				break
			else:
				continue
			break

outputGeo_fname = "filteredTemporal_"+locationKey+"_"+"2015"+"-"+"2023"+"_temp_"+analysis_version+".geojson"

#with open("%s%s" % (data_path, outputGeo_fname), "w") as f:
#    json.dump(output_filteredTemporalData, f)

######################################################################################
#Make kdTrees for each sub-roi from the points within each sub-roi
for geoid,roiObj in rois_.items():
	print(geoid, len(roiObj["points"]))
	if len(roiObj["points"]) > 0:
		roiObj["kdTree"] = cKDTree(roiObj["points"])
	else:
		print(geoid,"NO POINTS")
######################################################################################
######################################################################################	
'''
	Read the filtered parcels dataset. This contains parcels within the main ROI. 
	This section of code filters parcels to those within the selected areas (specific
	zipcodes, tracts, custom geometries etc).
'''
df_parcelsFiltered = pd.read_csv("%s%s" % (r"02_output\\","parcelData_filtered.csv"),encoding="utf-8")
#"OBJECTID","PROP_CL","PROP_CT","BLDG_CL","AREA_FT","TABULATION_AREA","LON","LAT"
parcelsFiltered_objId = list(df_parcelsFiltered["OBJECTID"])
parcelsFiltered_propCl = list(df_parcelsFiltered["PROP_CL"])
parcelsFiltered_propCt = list(df_parcelsFiltered["PROP_CT"])
parcelsFiltered_bldgCl = list(df_parcelsFiltered["BLDG_CL"])
parcelsFiltered_area = list(df_parcelsFiltered["AREA_FT"])
parcelsFiltered_lat = list(df_parcelsFiltered["LAT"])
parcelsFiltered_lon = list(df_parcelsFiltered["LON"])

for i in range(len(parcelsFiltered_objId)):
	cx = parcelsFiltered_lon[i]
	cy = parcelsFiltered_lat[i]
	#print("PARCEL: ",[cx,cy])
	pt_parcel = Point([cx,cy])

	for geoid,roiObj in rois_.items():
		pt_isWithin = 0
		for geometry in roiObj["polygon"]:
			if pt_parcel.within(Polygon(geometry)):
				pt_isWithin+=1
		if pt_isWithin > 0:
			roiObj["parcels"]["prop_cl"].append(parcelsFiltered_propCl[i])
			roiObj["parcels"]["prop_ct"].append(parcelsFiltered_propCt[i])
			roiObj["parcels"]["bldg_cl"].append(parcelsFiltered_bldgCl[i])
			roiObj["parcels"]["area"].append(parcelsFiltered_area[i])
			roiObj["parcels"]["coords"].append([parcelsFiltered_lat[i],parcelsFiltered_lon[i]])
######################################################################################

write_subRoiStats = open("%s%s%s%s" % (data_path,"subRoiStats_",analysis_version,"_temp.csv"), 'w',newline='', encoding='utf-8')
writer_subRoiStats = csv.writer(write_subRoiStats)
writer_subRoiStats.writerow([
	"GEOID","ROI_ZONE",
	"LSTF_MEAN","LSTF_STD","LSTF_MIN","LSTF_MAX",
	"NDVI_MEAN","NDVI_STD","NDVI_MIN","NDVI_MAX",
	])
		
write_dataOut = open("%s%s%s%s" % (data_path,"parcelStats_",analysis_version,"_temp.csv"), 'w',newline='', encoding='utf-8')
writer_dataOut = csv.writer(write_dataOut)
writer_dataOut.writerow([
	"GEOID","ROI_ZONE","LON","LAT",
	"LSTF_MEAN","LSTF_DELTA","LSTN_DELTA",
	"NDVI_MEAN","NDVI_DELTA","PROP_CL",
	"PROP_CT", "BLDG_CL", "AREA","PARCEL_LON","PARCEL_LAT"
	])

#ROI_ID,ROI_ZONE,X,Y,LSTF_MEAN,LSTF_DELTA,LSTN_DELTA,NDVI_MEAN,NDVI_DELTA
for geoid,roiObj in rois_.items():
	subRoi_lstfMean = np.mean(roiObj["lstf_mean"])
	subRoi_lstfStd = np.std(roiObj["lstf_mean"])
	subRoi_lstfMin = min(roiObj["lstf_mean"])
	subRoi_lstfMax = max(roiObj["lstf_mean"])

	subRoi_ndviMean = np.mean(roiObj["ndvi_mean"])
	subRoi_ndviStd = np.std(roiObj["ndvi_mean"])
	subRoi_ndviMin = min(roiObj["ndvi_mean"])
	subRoi_ndviMax = max(roiObj["ndvi_mean"])

	writer_subRoiStats.writerow([
		geoid,None,
		subRoi_lstfMean,subRoi_lstfStd,subRoi_lstfMin,subRoi_lstfMax,
		subRoi_ndviMean,subRoi_ndviStd,subRoi_ndviMin,subRoi_ndviMax,
		
	])

	for i in range(len(roiObj["parcels"]["coords"])):
		query_coordinate = roiObj["parcels"]["coords"][i]
		qx = query_coordinate[1]
		qy = query_coordinate[0]
		query_point = (qx, qy)
		#cp_idx = roiObj["kdTree"].query(query_point)[1]

		store_dist = []
		for j in range(len(roiObj["points"])):
			pt = roiObj["points"][j]
			eucDist = distance.euclidean(query_point, pt)
			store_dist.append(eucDist)
		argsort_dist = np.argsort(store_dist)
		cp_idx = argsort_dist[0]
		if store_dist[cp_idx] <= 0.00125:
			cp = roiObj["points"][cp_idx]
			cp_lstfMean = roiObj["lstf_mean"][cp_idx]
			cp_ndviMean = roiObj["ndvi_mean"][cp_idx]

			writer_dataOut.writerow([
				geoid,roiObj["zone"],
				cp[0],cp[1],
				cp_lstfMean,
				None,
				None,
				cp_ndviMean,
				None,
				roiObj["parcels"]["prop_cl"][i].upper(),
				roiObj["parcels"]["prop_ct"][i],
				roiObj["parcels"]["bldg_cl"][i],
				roiObj["parcels"]["area"][i],
				qx,qy
				])
######################################################################################
######################################################################################
'''
	Read the temporally analyized dataset.
	For each point in the data, check if it is within one of the selected geometries.
	If it is, add the data associated with the point to the sub-roi object the point
	is within. Add the point to the "points" list of of the sub-roi. With the points
	list, create a kdTree, which will be used to recall data for parcel analysis.
'''
#data_temporal = json.load(open("%s%s" % (r"02_output\\","DFW_2015-2022.json")))
'''data_temporal = json.load(open(r"02_output\locations\dallasTx\V4\dallasTx_2015-2023_V4.json"))
l8_points = []
l8_idx = []
for i in range(len(data_temporal["coordinates"])):
	for j in range(len(data_temporal["coordinates"][i])):
		coord = data_temporal["coordinates"][i][j]
		cx = coord[0]
		cy = coord[1]
		point = Point([cx,cy])
		#print("TEMEPORAL: ",[cx,cy])
		#Check if the point is within one of the sub-rois
		for roiId,roiObj in rois_.items():
			roi_polygon = Polygon(roiObj["polygon"])
			isWithin = point.within(roi_polygon)
			if isWithin:
				#print([cx,cy])
				l8_points.append([cx,cy])
				l8_idx.append([i,j])
				roiObj["points"].append([cx,cy])
				roiObj["lstf_mean"].append(data_temporal["lstf_mean"][i][j])
				roiObj["ndvi_mean"].append(data_temporal["ndvi_mean"][i])
				#rois_[roiId]["lstn_delta"].append(data_temporal["lstn_delta"][i][j])
				roiObj["lstf_delta"].append(data_temporal["lstf_delta"][i][j])
				roiObj["ndvi_delta"].append(data_temporal["ndvi_delta"][i])
				break'''
######################################################################################
'''df_parcels = pd.read_csv(str("%s%s" % (r"02_output\\","parcelData_filtered.csv")),encoding="utf-8")
#OBJECTID,PROP_CL,PROP_CAT,BLDG_CL,AREA_FT,X,Y
parcels_objid = list(df_parcels["OBJECTID"])
parcels_propCl = list(df_parcels["PROP_CL"])
parcels_propCt = list(df_parcels["PROP_CT"])
parcels_bldgCl = list(df_parcels["BLDG_CL"])
parcels_area = list(df_parcels["AREA_FT"])
parcels_x = list(df_parcels["LON"])
parcels_y = list(df_parcels["LAT"])

for i in range(len(parcelsFiltered_objId)):
	cx = parcelsFiltered_lon[i]
	cy = parcelsFiltered_lat[i]
	point = Point((cx,cy))
	for roiId,roiObj in rois_.items():
		polygon = Polygon(roiObj["polygon"])
		is_within = point.within(polygon)
		if is_within:
			rois_[roiId]["parcels"]["coords"].append([cx,cy])
			rois_[roiId]["parcels"]["prop_cl"].append(parcelsFiltered_propCl[i])
			rois_[roiId]["parcels"]["area"].append(parcelsFiltered_area[i])
			break
######################################################################################

output_path = "%s%s%s%s%s" % (r"02_output\locations\\",locationKey,"\\",analysis_version,"\\")

with open("%s%s%s%s" % (output_path,"temporal_selectRois_",analysis_version,".json"), "w", encoding='utf-8') as output_json:
	output_json.write(json.dumps(rois_, indent=2, ensure_ascii=False))
######################################################################################
write_dataOut = open("%s%s%s%s" % (output_path,"selectRoisStats_",analysis_version,".csv"), 'w',newline='', encoding='utf-8')
writer_dataOut = csv.writer(write_dataOut)
writer_dataOut.writerow(["ROI_ID","ROI_ZONE","X","Y","LSTF_MEAN","LSTF_DELTA","LSTN_DELTA","NDVI_MEAN","NDVI_DELTA","PROP_CL"])
#ROI_ID,ROI_ZONE,X,Y,LSTF_MEAN,LSTF_DELTA,LSTN_DELTA,NDVI_MEAN,NDVI_DELTA
for roiId,roiObj in rois_.items():
	for i in range(len(roiObj["coords"])):
		writer_dataOut.writerow([
			roiId,roiObj["zone"],
			roiObj["coords"][i][0],
			roiObj["coords"][i][1],
			roiObj["lstf_mean"][i],
			roiObj["lstf_delta"][i],
			None,
			roiObj["ndvi_mean"][i],
			roiObj["ndvi_delta"][i],
			roiObj["parcels"]["prop_cl"][i].upper()])
######################################################################################
print("DONE")'''