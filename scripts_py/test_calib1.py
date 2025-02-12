import subprocess
import numpy as np
import uproot
import time
import matplotlib.pyplot as plt
from rwave import rwaveclient
from rwaveclient_root import acquire_data
from calibration_utils import take_calibration_data

HOST = 'localhost'
PORT = 30001
OUTPUT_FILE = "calibration_data.root"
TREE_NAME = "calibration_tree"
VOLTAGES = np.arange(-0.4, 0.4, 0.15)  # Voltage range from -0.4V to 0.4V

if __name__ == "__main__":
    take_calibration_data(VOLTAGES, OUTPUT_FILE)