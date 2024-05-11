import subprocess
'''This script executes programs in their proper order of operation.
Run this script to process geoTiffs and conduct spatial and temporal analysis'''
subprocess.run(["python", r"src/bandPreprocessing.py"], check=True)
subprocess.run(["python", r"src/normalizeLst.py"], check=True)
subprocess.run(["python", r"src/temporalAnalysis.py"], check=True)