import json
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
split_dir = str(script_dir).split("/")
idx_src = split_dir.index("src")
parent_dir = split_dir[idx_src-1]
resources_path = os.path.join(parent_dir, "00_resources/")
print(resources_path)

location_key = input("Location Key: ")
analysis_version = input("Analysis Version: ")
has_landsat = input("Uses Landsat?: ")
has_3dep = input("Uses 3DEP?: ")

logJson = { 
    "mongoDB":{"connection_uri":None},
    "analysis_version": analysis_version,
    "location_key": location_key,
    "year_start": None,
    "year_end": None,
	"has_landsat":has_landsat,
	"has_3dep":has_3dep,
    "run_stats": {
        "start_time": None,
        "end_time": None,
        "duration": None
    },
    "final_output_files": {
    "landsat_temporal": None,
    "3dep_terain": None
    },
    "processed_tifs": {},
    "preprocessing_output": [],
    "tiles": {}
}

with open("%s%s" % (resources_path,location_key+"_log.json"), "w", encoding='utf-8') as output_json:
	output_json.write(json.dumps(logJson, indent=2, ensure_ascii=False))
