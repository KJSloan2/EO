import json
'''This script crates a json used for storing input parameters used
across multiple scripts and tracks important runtime stats.'''

#user is prompted to enter the location, window of time and version of the analysis
ui_cityName = input("Enter location city name:  ")
ui_stateAbv = input("Enter location state abreviation (TX, IL, WI etc.):    ")

locationKey = ui_cityName.lower()+"_"+ui_stateAbv.lower()

ui_yearRange = input("Enter analysis years eg. 2019-2024:   ")
parse_yearRange = ui_yearRange.split("-")
yearStart = int(parse_yearRange[0])
yearEnd = int(parse_yearRange[1])

ui_analysisVersion = input("Enter analysis version (eg. V1, V2...): ")

#create a dictionary to store the user input information
analysis_parameters = {
    "analysis_verson":ui_analysisVersion,
    "location_key":locationKey,
    "year_start":yearStart,
    "year_end":yearEnd,
    "geotiffs_processed":{},
    "run_stats":{}
}

#write the user input information to json for use in other scrips
output_path = "%s%s" % (r"EO/00_resources/","analysis_parameters.json")
with open(output_path, "w", encoding='utf-8') as output_json:
    output_json.write(json.dumps(analysis_parameters, indent=2, ensure_ascii=False))
