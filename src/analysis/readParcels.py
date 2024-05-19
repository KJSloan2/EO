import json
import geopandas as gpd
import fiona
import time
import numpy as np
import csv
import pandas as pd

file_path = r"01_data\parcels\Parcel Shapefile.geojson"

#gdf = gpd.read_file(file_path)
'''taxpaname_1', 'school', 'city', 'propnam', 'taxpaadd_3', 'prop_cl',
'legal_3', 'st_dir', 'taxpacnty', 'unitid', 'res_com', 'taxpacity', 'objectid',
'legal_4', 'taxpaadd_4', 'county', 'legal_1', 'nscbd', 'st_type', 'taxpaadd_2',
'appraisaly', 'taxpazip', 'gis_acct', 'legal_5', 'busname', 'acct', 'totexempt',
'st_num', 'taxpaname_2', 'legal_2', 'taxpasta', 'mutiacct', 'taxpaadd_1',
'dacouncil', 'sptbcode', 'area_feet', 'st_name', 'mapsco_gr', 'bldg_cl'''

dataOut_fileName = "parcelData.csv"
write_dataOut = open("%s%s" % (r"02_output\\",dataOut_fileName), 'w',newline='', encoding='utf-8')
writer_dataOut = csv.writer(write_dataOut)
writer_dataOut.writerow(["OBJECTID","PROP_CL","PROP_CATEGORY","BLDG_CL","AREA_FT","X","Y"])

df_parcelTypes = pd.read_csv(str("%s%s" % (r"00_resources\\","parcelTypes.csv")),encoding="utf-8")
parcelTypes_category = list(df_parcelTypes["TYPE"])
parcelTypes_desc = list(df_parcelTypes["DESC"])

with fiona.open(file_path) as src:
	for feature in src:
		properties = feature['properties']
		prop_cl = properties['prop_cl']
		if prop_cl in parcelTypes_desc:
			try:
				prop_cl = " ".join(prop_cl.split(","))
				bldg_cl = " ".join(properties['bldg_cl'].split(","))
				area_feet = properties['area_feet']
				objectid = properties['objectid']
				prop_category = parcelTypes_category[parcelTypes_desc.index(prop_cl)]
				geometry = feature['geometry']
				geometry_type = geometry['type']
				if geometry_type.lower() == "multipolygon":
					geometry_coords = geometry['coordinates']
					x = []
					y = []
					for polygon in geometry_coords:
						for coords in polygon:
							for coord in coords:
								x.append(float(coord[0]))
								y.append(float(coord[1]))
					cx = np.mean(x)
					cy = np.mean(y)
					writer_dataOut.writerow([objectid,prop_cl,prop_category,bldg_cl,area_feet,cx,cy])
			except:
				pass
print("DONE")