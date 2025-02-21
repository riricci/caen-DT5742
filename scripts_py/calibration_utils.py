import sys
import subprocess
import numpy as np
import uproot
import scipy.stats
import matplotlib.pyplot as plt
import time
sys.path.append("/eu/caen-dt5742b/python/")
from rwave import rwaveclient
from rwaveclient_root import acquire_data, handle_data, save_waveforms_to_root
import argparse
from matplotlib.backends.backend_pdf import PdfPages
 
HOST = 'localhost'
PORT = 30001
OUTPUT_FILE = "calibration_data.root"
TREE_NAME = "calibration_tree"
VOLTAGES = np.arange(-0.4, 0.4, 0.15)  # Voltage range from -0.4V to 0.4V


# pulser settings - STILL OK FOR NOW
########################################################
def configure_pulser_calib():
    """Configures pulser for calibration by setting ARB mode and initializing DC offset."""
    cmds = [
        "/eu/aimtti/aimtti-cmd.py --address aimtti-tgp3152-00 --cmd 'WAVE ARB'",
        "/eu/aimtti/aimtti-cmd.py --address aimtti-tgp3152-00 --cmd 'ARBLOAD DC'",
        "/eu/aimtti/aimtti-cmd.py --address aimtti-tgp3152-00 --cmd 'DCOFFS 0'"
    ]
    for cmd in cmds:
        subprocess.run(cmd, shell=True, check=True)
    time.sleep(0.1)

def set_pulser_voltage(voltage, sleep):
    """Sets the pulser DC offset."""
    cmd = f"/eu/aimtti/aimtti-cmd.py --address aimtti-tgp3152-00 --cmd 'DCOFFS {voltage}'"
    subprocess.run(cmd, shell=True, check=True)
    time.sleep(sleep)  # Allow voltage stabilization



# data conversion to numpy arrays - TO BE UPDATED OR TRASHED BRUTALLY
########################################################
# def convert_calibration_data(data_dict):
#     """Convert collected calibration data to numpy arrays."""
#     for key in data_dict:
#         data_dict[key] = np.array(data_dict[key], dtype=np.float32)
#     return data_dict



# calibration data taking - TO BE UPDATED
########################################################
import argparse
import numpy as np
import scipy.stats as stats
import matplotlib.pyplot as plt

def take_calibration_data():
    """Acquire calibration data and perform linear regression for each cell."""
    
    # Argument parsing
    parser = argparse.ArgumentParser(
        description="Calibration data acquisition.",
        usage="python calibration_script.py --vmin MIN --vmax MAX --step STEP --output_file filename.root --plot_cell CELL --save_pdf"
    )
    parser.add_argument("--vmin", type=float, default=-0.4, help="Minimum voltage for calibration (default: -0.4V).")
    parser.add_argument("--vmax", type=float, default=0.4, help="Maximum voltage for calibration (default: 0.4V).")
    parser.add_argument("--step", type=float, default=0.15, help="Step size for voltage increments (default: 0.15V).")
    parser.add_argument("--sleep", type=float, default=0.1, help="Sleep time for voltage stabilization (default: 0.1s).")
    parser.add_argument("--output_file", type=str, default="calibration_data.root", help="Output ROOT file.")
    parser.add_argument("--plot_cell", type=int, default=0, help="Cell index to plot (default: 0).")
    parser.add_argument("--save_pdf", action="store_true", help="Save plots of all cells to a PDF file.")
    parser.add_argument("--load_calibration", type=str, default=None, help="Use calibration file.")
    parser.add_argument("--plot_waveforms", action="store_true", help="Plot waveforms.")
    parser.add_argument("--save_to_root", action="store_true", help="Save data to ROOT file.")
    parser.add_argument("--save_calibration", action="store_true", help="Save calibration parameters to .npz file.")
    
    args = parser.parse_args()

    # Define voltage range and other parameters
    voltages = np.arange(args.vmin, args.vmax + args.step, args.step)
    voltages = voltages[voltages <= 0.5]  # Limit to 0.5V
    s = args.sleep
    output_file = args.output_file
    plot_cell = args.plot_cell
    save_pdf = args.save_pdf
    load_calibration = args.load_calibration
    plot_waveforms = args.plot_waveforms
    save_to_root = args.save_to_root
    save_calibration = args.save_calibration

    # Data structure to hold calibration data
    calibration_data = {cell: {"voltages": [], "amplitudes": []} for cell in range(1024)}

    configure_pulser_calib()

    for v in voltages:
        set_pulser_voltage(v, s)
        data = acquire_data(0x0003)
        selected_ch = 1

        # Iterate over events and extract waveform values with smart indexing
        for event_index, event in enumerate(data):
            first_cell = event[selected_ch]["first_cell"]
            waveform = event[selected_ch]["waveform"]

            # Access waveform with calculated indices without using np.roll
            for cell_index in range(1024):
                aligned_index = (cell_index + first_cell) % 1024
                amplitude = waveform[aligned_index]

                # Store amplitude and corresponding voltage for each cell
                calibration_data[cell_index]["voltages"].append(v)
                calibration_data[cell_index]["amplitudes"].append(amplitude)

    
    # Perform linear regression for each cell using the mean amplitude across events
    fit_results = {}
    for cell, data in calibration_data.items():
        voltages = np.array(data["voltages"])
        amplitudes = np.array(data["amplitudes"])

        # Calculate the mean amplitude for each voltage step
        unique_voltages = np.unique(voltages)
        mean_amplitudes = np.array([
            np.mean(amplitudes[voltages == uv]) for uv in unique_voltages
        ])

        # Perform linear regression using scipy.stats.linregress
        slope, intercept, r_value, p_value, std_err = stats.linregress(unique_voltages, mean_amplitudes)
        
        # Store the fit results
        fit_results[cell] = {
            "slope": slope,
            "intercept": intercept,
            "r_value": r_value,
            "std_err": std_err
        }
        
        # Optionally plot the results for a specific cell
        if plot_waveforms and cell == plot_cell:
            plt.figure(figsize=(8, 6))
            plt.scatter(unique_voltages, mean_amplitudes, label='Data', color='blue')
            plt.plot(unique_voltages, slope * unique_voltages + intercept, label='Fit', color='red')
            plt.xlabel('Voltage (V)')
            plt.ylabel('Mean Amplitude')
            plt.title(f'Cell {cell}: Slope={slope:.3f}, Intercept={intercept:.3f}')
            plt.legend()
            plt.show()

    # Optionally save fit results
    if save_calibration:
        # Convert cell indices to strings before saving
        fit_results_str = {str(cell): params for cell, params in fit_results.items()}

        # Save with np.savez
        np.savez("calibration_parameters.npz", **fit_results_str)


# testing calibration
def apply_calibration_to_data():
    """Applies calibration parameters to waveform data and saves calibrated data to a ROOT file."""
    # Argument parsing
    parser = argparse.ArgumentParser(
        description="Calibration data acquisition.",
        usage="python calibration_script.py --vmin MIN --vmax MAX --step STEP --output_file filename.root --plot_cell CELL --save_pdf"
    )
    parser.add_argument("--vmin", type=float, default=-0.4, help="Minimum voltage for calibration (default: -0.4V).")
    parser.add_argument("--vmax", type=float, default=0.4, help="Maximum voltage for calibration (default: 0.4V).")
    parser.add_argument("--step", type=float, default=0.15, help="Step size for voltage increments (default: 0.15V).")
    parser.add_argument("--sleep", type=float, default=0.1, help="Sleep time for voltage stabilization (default: 0.1s).")
    parser.add_argument("--output_file", type=str, default="calibration_data.root", help="Output ROOT file.")
    parser.add_argument("--plot_cell", type=int, default=0, help="Cell index to plot (default: 0).")
    parser.add_argument("--save_pdf", action="store_true", help="Save plots of all cells to a PDF file.")
    parser.add_argument("--load_calibration", type=str, default=None, help="Use calibration file.")
    parser.add_argument("--plot_waveforms", action="store_true", help="Plot waveforms.")
    parser.add_argument("--save_to_root", action="store_true", help="Save data to ROOT file.")
    parser.add_argument("--save_calibration", action="store_true", help="Save calibration parameters to .npz file.")
    
    args = parser.parse_args()

    # Define voltage range and other parameters
    voltages = np.arange(args.vmin, args.vmax + args.step, args.step)
    voltages = voltages[voltages <= 0.5]  # Limit to 0.5V
    s = args.sleep
    output_file = args.output_file
    plot_cell = args.plot_cell
    save_pdf = args.save_pdf
    load_calibration = args.load_calibration
    plot_waveforms = args.plot_waveforms
    save_to_root = args.save_to_root
    save_calibration = args.save_calibration
    # Load calibration parameters
    
    calibration_data = np.load(load_calibration, allow_pickle=True)
    calibration_data = {int(cell): calibration_data[cell].item() for cell in calibration_data}
    
    # Container for calibrated data to be saved in ROOT format
    calibrated_data = {cell: {"voltages": [], "amplitudes": []} for cell in range(1024)}

    configure_pulser_calib()

    for v in voltages:
        set_pulser_voltage(v, s)
        data = acquire_data(0x0003)
        selected_ch = 1
        all_original_waveforms = []
        all_calibrated_waveforms = []
        all_uncalibrated_waveforms = []
        # Iterate over events and extract waveform values with smart indexing
        for event_index, event in enumerate(data):
            first_cell = event[selected_ch]["first_cell"]
            waveform = event[selected_ch]["waveform"]
            calibrated_waveform = np.zeros(1024, dtype=float)
            copy_waveform = np.zeros(1024, dtype=float)
            

            # Access waveform with calculated indices without using np.roll
            for cell_index in range(1024):
                aligned_index = (cell_index + first_cell) % 1024
                slope = calibration_data[cell_index]["slope"]
                intercept = calibration_data[cell_index]["intercept"]
                copy_waveform[aligned_index] = (waveform[aligned_index] - intercept) / slope
                
                #back to adc counts considering 12-bits ADC for -0.5 to 0.5 V
                calibrated_waveform[aligned_index] = int((copy_waveform[aligned_index] + 0.5) * 4095)

            all_original_waveforms.append(waveform)
            all_calibrated_waveforms.append(calibrated_waveform)
        # # Plot the waveforms for comparison (for the current event)
        

        if plot_waveforms:
            plt.figure(figsize=(10, 6))
            # plt.plot(all_original_waveforms[0], label="Original Waveform", color="blue")
            plt.plot(all_calibrated_waveforms[0], label="Calibrated Waveform", color="red", linestyle="--")
            plt.title(f"Waveform Comparison at Voltage {v}V")
            plt.xlabel("Cell Index")
            plt.ylabel("Amplitude (Voltage)")
            plt.legend()
            plt.show()
            
            plt.figure(figsize=(10, 6))
            plt.plot(all_original_waveforms[0], label="Original Waveform", color="blue")
            # plt.plot(all_calibrated_waveforms[1], label="Calibrated Waveform", color="red", linestyle="--")
            plt.title(f"Waveform Comparison at Voltage {v}V")     
            plt.xlabel("Cell Index")
            plt.ylabel("Amplitude (ADC)")
            plt.legend()
            plt.show()

    
# plotting calibration curves for the selected cell for ch1
########################################################
# used only as control plot for now - used at the end of data taking

# def fit_adc_vs_voltage(voltage_data, ch1_waveform, cell_idx=0):
#     """Fits ADC vs Voltage for a chosen cell and returns slope, intercept."""
#     adc_values = np.array(ch1_waveform)[:, cell_idx]  # select requested cell
#     slope, intercept, _, _, _ = scipy.stats.linregress(voltage_data, adc_values)    
#     return slope, intercept

# def single_plot_adc_vs_voltage(voltage_data, ch1_waveform, cell_idx, fit_params):
#     """Plots ADC vs Voltage for a chosen cell using precomputed fit parameters."""
#     plt.figure()  # Crea una nuova figura

#     adc_values = np.array(ch1_waveform)[:, cell_idx]  # Corretto anche questo!
#     slope, intercept = fit_params[cell_idx]
#     fitted_values = slope * voltage_data + intercept

#     # Plot
#     plt.scatter(voltage_data, adc_values, label=f'Cell {cell_idx} Data', c='black', s=10)
#     plt.plot(voltage_data, fitted_values, label=f'Fit: y = {slope:.2f}x + {intercept:.2f}', c='red', linewidth=0.8)
#     plt.xlabel('Voltage (V)')
#     plt.ylabel('ADC Value')
#     plt.title(f'ADC vs Voltage for Cell {cell_idx}')
#     plt.legend()
#     # plt.show() # for some reason it "gives fastidio" to the pdf file writing. Debugging needed. --> separate plotting function?

        
# def plot_all_cells_pdf(num_cells, data_dict, fit_params, args): 
    
#     cells_per_page = 24 # 6 rows x 4 columns
#     cols = 4
#     rows = 6
#     num_pages = int(np.ceil(num_cells / cells_per_page)) # ceil approximates to the upper integer of the resulting division

#     with PdfPages(f'all_cells_plots_step{args.step}.pdf') as pdf:
#         for page in range(num_pages):
#             fig, axes = plt.subplots(rows, cols, figsize=(12, 18))
#             axes = axes.flatten() # to handle more easily the axes
#             for i in range (cells_per_page):
#                 cell_idx = page * cells_per_page + i
#                 if cell_idx >= num_cells:
#                     break # when done, exit the loop and finish                    
#                 ax = axes[i]
#                 adc_values = np.array(data_dict["ch1_waveform"])[:, cell_idx]
#                 slope, intercept = fit_params[cell_idx]
#                 fitted_values = slope * data_dict["voltage"] + intercept

#                 ax.scatter(data_dict["voltage"], adc_values, color='black', s=10, label=f'Cell {cell_idx}')
#                 ax.plot(data_dict["voltage"], fitted_values, color='red', linewidth=0.8)
#                 ax.set_xlabel('Voltage (V)')
#                 ax.set_ylabel('ADC')
#                 ax.set_title(f'Cell {cell_idx}')
#                 ax.legend(fontsize=8)
                        
#                     # # we hate empty suplots, let's remove them
#                     # for j in range(i + 1, len(axes)):
#                     #     if axes[j].has_data():
#                     #         continue  # if axes has data, skip to the next one
#                     #     fig.delaxes(axes[j])
#                 # finalize and close all this 
#             plt.tight_layout()
#             pdf.savefig(fig)
#             plt.close()
    
    

# def plot_hist_from_npz(npz_file):
#     """Plots ADC vs Voltage for all cells using precomputed fit parameters."""
#     fit_params = np.load(npz_file)
#     p0_list = []
#     p1_list = []

#     for cell in range(1024):
#         # Extracting p0 and p1 for each cell
#         p0 = fit_params[str(cell)][0]
#         p1 = fit_params[str(cell)][1]
#         # Appending them to the respective lists
#         p0_list.append(p0)
#         p1_list.append(p1)
        
#     # Creating subplots for histograms
#     fig, axs = plt.subplots(1, 2, figsize=(12, 6))
#     fig.suptitle('Calibration Parameters Distribution')

#     # Histogram for p0 (Intercept)
#     axs[0].hist(p0_list, bins=100, color='blue', alpha=0.7)
#     axs[0].set_xlabel('p1')
#     axs[0].set_ylabel('Frequency')
#     axs[0].set_title('Slope')

#     # Histogram for p1 (Slope)
#     axs[1].hist(p1_list, bins=100, color='red', alpha=0.7)
#     axs[1].set_xlabel('p0')
#     axs[1].set_ylabel('Frequency')
#     axs[1].set_title('Incercept')

#     plt.tight_layout(rect=[0, 0.03, 1, 0.95])  # Adjust layout to make space for title
#     plt.show()


#     # for cell in fit_params:
#     #     slope, intercept = fit_params[cell]
#     #     single_plot_adc_vs_voltage(data_dict["voltage"], data_dict["ch1_waveform"], cell, fit_params)
#     #     plt.show()



# # TO BE REFINED OR REMOVED!  
# def calibrate(npz_file, p0_list, p1_list):
#     """Use fit parameters for calibration during data taking."""
#     #first we load the fit parameters
#     fit_params = np.load(npz_file)
#     p0_list = []
#     p1_list = []

#     for cell in range(1024):
#         # Extracting p0 and p1 for each cell
#         p0 = fit_params[str(cell)][0]
#         p1 = fit_params[str(cell)][1]
#         # Appending them to the respective lists
#         p0_list.append(p0)
#         p1_list.append(p1)
    
#     return p0_list, p1_list
        
#     # STUFF TO BE DONE
#     # now we can use them to calibrate the data from the cells
    
# # TO BE REFINED OR REMOVED!    
# def CAENDGZ_volt_to_adc(V):
#     V_min = -0.5    # V_min is at ADC = 0
#     V_max = 0.5     # V_max is at = 4095
#     ADC_max = 4095  # Maximum ADC range for 12-bit ADC
#     Delta_V = (V_max - V_min) / (ADC_max + 1)  # Step

#     # Conversion
#     ADC_value = int((V - V_min) / Delta_V)
    
#     # Check limits
#     if ADC_value < 0:
#         ADC_value = 0
#     elif ADC_value > ADC_max:
#         ADC_value = ADC_max
    
#     return ADC_value





# TOMORROW NEVER KNOWS
        # TO BE UPDATED!
        # if calibration_file: #to be done
        #     # formula to calibrate waveforms: ch1_waveform_calibrated = (ch1_waveform - p1) / p0
        #     fit_params = np.load(calibration_file)
        #     p0_list = []
        #     p1_list = []
        #     for cell in range(1024):
        #         # Extracting p0 and p1 for each cell
        #         p0 = fit_params[str(cell)][1]
        #         p1 = fit_params[str(cell)][0]
        #         # Appending them to the respective lists
        #         p0_list.append(p0)
        #         p1_list.append(p1)
        
            
            #  CONVERSION!
            # for i, event in enumerate(data):    
            #     old_waveform = event.get(1, np.zeros(1024)) # Channel 1 pre-calibration
            #     new_waveform=np.zeros(1024) # Channel 1 post-calibration
            #     for cell in range(1024):
            #         # print(f'cell: {cell}, old_waveform{cell}: {old_waveform[cell]},p0: {p0_list[cell]}')
            #         # print((old_waveform[cell]-p0_list[cell])/p1_list[cell]) #this is RIGHT
            #         new_waveform[cell] = (old_waveform[cell] - p0_list[cell]) / p1_list[cell]
            #         # now convert to adc
            #         new_waveform[cell] = CAENDGZ_volt_to_adc(new_waveform[cell])
            #     all_new_waveforms.append(new_waveform) 

            #     # mean_new_waveform = np.mean(all_new_waveforms, axis=0)
            #     data_dict["voltage"].append(v)
            #     data_dict["event"].append(0)  
            #     data_dict["ch1_waveform"].append(all_new_waveforms)