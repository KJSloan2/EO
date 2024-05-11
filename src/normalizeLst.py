import numpy as np
import json
######################################################################################
def normailize_val(val,d_min,d_max):
	return round(((val-d_min)/(d_max-d_min)),6)
######################################################################################
fNames_data = []
with open(r"00_resources\processed_tifs.txt", 'r') as file:
	for line in file:
		fNames_data.append(line.strip()+".json")
######################################################################################
pool_lst=[]
for fName in fNames_data:
	fPath = "%s%s" % (r"02_output\\",fName)
	data_ = json.load(open(fPath))
	for i in range(len(data_["lstf"])):
		for val in data_["lstf"][i]:
			if len(pool_lst) == 0:
				pool_lst.append(val)
			else:
				if val > max(pool_lst) or val < min(pool_lst):
					pool_lst.append(val)
######################################################################################
lst_min = min(pool_lst)
lst_max = max(pool_lst)
for fName in fNames_data:
	print(fName)
	fPath = "%s%s" % (r"02_output\\",fName)
	data_ = json.load(open(fPath))
	data_["lst_norm"] = []
	for i in range(len(data_["lstf"])):
		data_["lst_norm"].append([])
		for val in data_["lstf"][i]:
			data_["lst_norm"][-1].append(normailize_val(val,lst_min,lst_max))
		
	output_path = "%s%s" % (r"02_output\\",fName)
	with open(output_path, "w", encoding='utf-8') as output_json:
		output_json.write(json.dumps(data_, indent=2, ensure_ascii=False))
######################################################################################
print("DONE")