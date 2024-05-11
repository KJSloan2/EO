import numpy as np
import json
######################################################################################
def normailize_linear_instance(val,d_min,d_max):
	return round(((val-d_min)/(d_max-d_min)),6)
######################################################################################
fNames_data = []
fNames = []
with open(r"EO/00_resources/processed_tifs.txt", 'r') as file:
	for line in file:
		fNames.append(str(line.strip()).split("_"))
		fNames_data.append(line.strip()+".json")
	file.close()

locationKey = fNames[0][0]+"_"+fNames[0][1]
yearStart = fNames[0][2]
yearEnd = fNames[-1][2]
analysis_version = fNames[0][3]
data_path = "%s%s%s%s%s" % (r"EO/02_output/",locationKey,"/",analysis_version,"/")
######################################################################################
temporalData_ = {}
data_ = json.load(open("%s%s" % (data_path, fNames_data[0])))
data_lst = data_["lstf"]
print(len(data_lst),len(data_lst[0]))
######################################################################################
data_combined = {
	"coordinates":[],
	"lstf":[],"lstf_range":[],
	"ndvi":[]
	}

for i in range(len(data_lst)):
	for key,obj in data_combined.items():
		obj.append([])
		for j in range(len(data_lst[0])):
			obj[-1].append([])

#roi_json = json.load(open("%s%s" % (r"00_resources\\","roi_DallasTx.json")))
#roi_bb = roi_json["roi_main"]
######################################################################################
for fName in fNames_data:
	fPath = "%s%s" % (data_path, fName)
	data_ = json.load(open(fPath))
	for i in range(len(data_["lstf"])):
		for j in range(len(data_["lstf"][i])):
			data_combined["lstf"][i][j].append(float(data_["lstf"][i][j]))
			data_combined["ndvi"][i][j].append(float(data_["ndvi"][i][j]))
			data_combined["coordinates"][i][j].append(data_["coordinates"][i][j])
			#data_combined["lstn"][i][j].append(float(data_["lst_norm"][i][j]))
######################################################################################
ndviRanges_ = [
	[-2,-0.28],[-0.28,0.015],
	[0.015,0.14],[0.14,0.18],
	[0.18,0.27],[0.27,0.36],
	[0.36,0.74],[0.74,2]
]
######################################################################################
output_ = {
	"lstf_mean":[],"lstf_delta":[],"lstf_skew":[],"lstn_delta":[],"lstf_slope":[],
	"ndvi_mean":[],"ndvi_delta":[],"ndvi_skew":[],"ndvi_slope":[],
	"coordinates":[]
}

output_geo = {
	"type": "FeatureCollection",
	"name": "Landsat 8, LST and NDVI Temportal Analysis",
	"features": []
}
######################################################################################
#output_["coordinates"] = data_combined["coordinates"][0]
for i in range(len(data_combined["lstf"])):
	for key,obj in output_.items():
		obj.append([])
	for j in range(len(data_combined["lstf"][i])):
		try:
			coordinate = data_combined["coordinates"][i][j][0]
			lstf = data_combined["lstf"][i][j]
			ndvi = data_combined["ndvi"][i][j]
			#print("DATA: ",len(lstf),len(ndvi))

			if len(lstf) != 0 and len(ndvi) != 0:

				lstf_x = list(range(0, len(lstf)))
				lstf_coefficients = np.polyfit(lstf_x, lstf, 1)
				lstf_m = lstf_coefficients[0]
				lstf_b = lstf_coefficients[1]

				ndvi_x = list(range(0, len(ndvi)))
				ndvi_coefficients = np.polyfit(ndvi_x, ndvi, 1)
				ndvi_m = ndvi_coefficients[0]
				ndvi_b = ndvi_coefficients[1]

				lstn_deltas = []
				lstf_deltas = []
				ndvi_deltas = []

				for k in range(1,len(data_combined["lstf"][i][j])-1,1):
					#lstn_deltas.append(data_combined["lstn"][i][j][k]-data_combined["lstn"][i][j][k-1])
					lstf_deltas.append(data_combined["lstf"][i][j][k]-data_combined["lstf"][i][j][k-1])
					ndvi_deltas.append(data_combined["ndvi"][i][j][k]-data_combined["ndvi"][i][j][k-1])

				#print("DELTAS: ",len(lstf_deltas),len(ndvi_deltas))
				if len(lstf_deltas) != 0 and len(ndvi_deltas) != 0:
					#lstn_delta = np.mean(lstn_deltas)
					
					lstf_delta = np.mean(lstf_deltas)
					ndvi_delta = np.mean(ndvi_deltas)

					lstf_mean = np.mean(data_combined["lstf"][i][j])
					ndvi_mean = np.mean(data_combined["ndvi"][i][j])
					
					output_["lstf_mean"][-1].append(lstf_mean)
					#lstf_skew = np.mean(((data_combined["lstf"][i][j] - lstf_mean) / np.std(data_combined["lstf"][i][j])) ** 3)
					#ndvi_skew = np.mean(((data_combined["ndvi"][i][j] - ndvi_mean) / np.std(data_combined["ndvi"][i][j])) ** 3)

					lstf_skew = 0
					ndvi_skew = 0

					#output_["lstn_delta"][-1].append(lstn_delta)
					output_["lstf_delta"][-1].append(lstf_delta)
					output_["lstf_skew"][-1].append(lstf_skew)
					output_["lstf_slope"][-1].append(lstf_m)

					output_["ndvi_delta"][-1].append(ndvi_delta)
					output_["ndvi_skew"][-1].append(ndvi_skew)
					output_["ndvi_slope"][-1].append(ndvi_m)

					output_["coordinates"][-1].append(coordinate)

					output_data = {
						"lstf_mean":lstf_mean,
						"lstf_slope":lstf_m,
						"ndvi_mean":ndvi_mean,
						"ndvi_slope":ndvi_m
					}
					
					nanVals = 0
					for key,val in output_data.items():
						if np.isnan(val):
							output_data[key] = 0
							nanVals+=1

					if nanVals == 0:
						output_geo["features"].append(
							{"type": "Feature",
								"properties": {
									"lstf_mean":output_data["lstf_mean"],
									"lstf_slope":output_data["lstf_slope"],
									"ndvi_mean":output_data["ndvi_mean"],
									"ndvi_slope":output_data["ndvi_slope"]
								},
								"geometry": {
									"type": "Point",
									"coordinates": coordinate
								}
							}
						)
			else:
				print("EMPTY")
		except Exception as e:
			print("ERROR", e)
			continue
######################################################################################
output_fname = locationKey+"_"+yearStart+"-"+yearEnd+"_"+analysis_version+".json"
outputGeo_fname = locationKey+"_"+yearStart+"-"+yearEnd+"_"+analysis_version+".geojson"
print(outputGeo_fname)
#with open("%s%s" % (data_path, outputGeo_fname), "w", encoding='utf-8') as output_geojson:
#	output_geojson.write(json.dumps(output_geo, ensure_ascii=False))

with open("%s%s" % (data_path, outputGeo_fname), "w") as f:
    json.dump(output_geo, f)

'''with open("%s%s" % (data_path, output_fname), "w", encoding='utf-8') as output_json:
	output_json.write(json.dumps(output_, ensure_ascii=False))'''
######################################################################################
print("DONE")


