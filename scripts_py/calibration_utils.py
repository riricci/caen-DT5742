import subprocess
import numpy as np
import uproot
import scipy.stats
import matplotlib.pyplot as plt
import time
from rwave import rwaveclient
from rwaveclient_root import acquire_data
import argparse
from matplotlib.backends.backend_pdf import PdfPages

HOST = 'localhost'
PORT = 30001
OUTPUT_FILE = "calibration_data.root"
TREE_NAME = "calibration_tree"
VOLTAGES = np.arange(-0.4, 0.4, 0.15)  # Voltage range from -0.4V to 0.4V


# pulser settings
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


# data conversion to numpy arrays
########################################################
def convert_calibration_data(data_dict):
    """Convert collected calibration data to numpy arrays."""
    for key in data_dict:
        data_dict[key] = np.array(data_dict[key], dtype=np.float32)
    return data_dict

# ROOT file writing using uproot for any dictionary
########################################################
def save_to_root(data_dict, filename):
    """Saves the collected [calibration] data to a ROOT file."""
    with uproot.recreate(filename) as file:
        file[TREE_NAME] = data_dict
    print(f"Calibration data saved to {filename}")

# to be checked/updated - not used for now
# def load_calib_data_from_root(filename, tree_name="calibration_tree"):
#     """Load data from root doing conversion to numpy."""
#     with uproot.open(filename) as file:
#         tree = file[tree_name]
#         voltage_data = tree["voltage"].array(library="np")  # Converte in NumPy direttamente
#         ch0_data = tree["ch0_waveform"].array(library="np")
#         ch1_data = tree["ch1_waveform"].array(library="np")
#     return voltage_data, ch0_data, ch1_data

# p0 and p1 calibration parameters extraction and writing to ROOT file
# TO BE CHECKED/UPDATED
########################################################
# def calc_calibration_parameters(voltage_data, ch_waveform):
#     """Performs calibration for each one of the 1024 cells."""
#     num_cells = ch_waveform.shape[1]  # Dovrebbe essere 1024
#     calibration_params = []
    
#     for cell in range(num_cells):
#         adc_values = ch_waveform[:, cell]  # ADC per la cella specifica
#         slope, intercept, _, _, _ = scipy.stats.linregress(voltage_data, adc_values)
#         calibration_params.append((slope, intercept))
    
#     return np.array(calibration_params)  # Restituisce una lista di (slope, intercept) per cella


# calibration data taking
########################################################
def take_calibration_data():
    """Acquire calibration data using argparse to set parameters dynamically."""
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
    
    args = parser.parse_args()

    voltages = np.arange(args.vmin, args.vmax + args.step, args.step)
    s = args.sleep 
    output_file = args.output_file
    plot_cell = args.plot_cell
    save_pdf = args.save_pdf

    data_dict = {"voltage": [], "event": [], "ch1_waveform": []}

    configure_pulser_calib()
    for v in voltages:
        set_pulser_voltage(v,s)
        all_ch1_waveforms = []
        data = acquire_data()
        
        if data is None:
            print(f"Failed to acquire data for voltage {v}V")
            continue

        for i, event in enumerate(data):
            ch1_waveform = event.get(1, np.zeros(1024))  # Channel 1
            all_ch1_waveforms.append(ch1_waveform)   

        mean_ch1_waveform = np.mean(all_ch1_waveforms, axis=0)
        data_dict["voltage"].append(v)
        data_dict["event"].append(0)  
        data_dict["ch1_waveform"].append(mean_ch1_waveform)

    #converting and saving data to ROOT file
    data_dict = convert_calibration_data(data_dict)
    save_to_root(data_dict, output_file)

    #preparing fitting parameters
    num_cells = len(data_dict["ch1_waveform"][0])  # 1024 celle
    fit_params = {}
    for cell in range(num_cells):
        slope, intercept = fit_adc_vs_voltage(data_dict["voltage"], data_dict["ch1_waveform"], cell_idx=cell)
        fit_params[cell] = (slope, intercept)    

    # saving to .npz file and doing control plot
    np.savez(output_file.replace(".root", "_fit_params.npz"), **{str(k): v for k, v in fit_params.items()})
    
    if save_pdf:
        plot_all_cells_pdf(num_cells, data_dict, fit_params, args)
        pass
                
    if plot_cell: #to be adjusted because cells go from 0 to 1023 and 0 will result as false...
        single_plot_adc_vs_voltage(data_dict["voltage"], data_dict["ch1_waveform"], plot_cell, fit_params)
        plt.show()
    
    # back to DC=0 V for other uses
    set_pulser_voltage(0, s)


    
# plotting calibration curves for the selected cell for ch1
########################################################
# used only as control plot for now - used at the end of data taking

def fit_adc_vs_voltage(voltage_data, ch1_waveform, cell_idx=0):
    """Fits ADC vs Voltage for a chosen cell and returns slope, intercept."""
    adc_values = np.array(ch1_waveform)[:, cell_idx]  # select requested cell
    slope, intercept, _, _, _ = scipy.stats.linregress(voltage_data, adc_values)    
    return slope, intercept

def single_plot_adc_vs_voltage(voltage_data, ch1_waveform, cell_idx, fit_params):
    """Plots ADC vs Voltage for a chosen cell using precomputed fit parameters."""
    plt.figure()  # Crea una nuova figura

    adc_values = np.array(ch1_waveform)[:, cell_idx]  # Corretto anche questo!
    slope, intercept = fit_params[cell_idx]
    fitted_values = slope * voltage_data + intercept

    # Plot
    plt.scatter(voltage_data, adc_values, label=f'Cell {cell_idx} Data', c='black', s=10)
    plt.plot(voltage_data, fitted_values, label=f'Fit: y = {slope:.2f}x + {intercept:.2f}', c='red', linewidth=0.8)
    plt.xlabel('Voltage (V)')
    plt.ylabel('ADC Value')
    plt.title(f'ADC vs Voltage for Cell {cell_idx}')
    plt.legend()
    # plt.show() # for some reason it "gives fastidio" to the pdf file writing. Debugging needed. --> separate plotting function?

        
def plot_all_cells_pdf(num_cells, data_dict, fit_params, args): 
    
    cells_per_page = 24 # 6 rows x 4 columns
    cols = 4
    rows = 6
    num_pages = int(np.ceil(num_cells / cells_per_page)) # ceil approximates to the upper integer of the resulting division

    with PdfPages(f'all_cells_plots_step{args.step}.pdf') as pdf:
        for page in range(num_pages):
            fig, axes = plt.subplots(rows, cols, figsize=(12, 18))
            axes = axes.flatten() # to handle more easily the axes
            for i in range (cells_per_page):
                cell_idx = page * cells_per_page + i
                if cell_idx >= num_cells:
                    break # when done, exit the loop and finish                    
                ax = axes[i]
                adc_values = np.array(data_dict["ch1_waveform"])[:, cell_idx]
                slope, intercept = fit_params[cell_idx]
                fitted_values = slope * data_dict["voltage"] + intercept

                ax.scatter(data_dict["voltage"], adc_values, color='black', s=10, label=f'Cell {cell_idx}')
                ax.plot(data_dict["voltage"], fitted_values, color='red', linewidth=0.8)
                ax.set_xlabel('Voltage (V)')
                ax.set_ylabel('ADC')
                ax.set_title(f'Cell {cell_idx}')
                ax.legend(fontsize=8)
                        
                    # # we hate empty suplots, let's remove them
                    # for j in range(i + 1, len(axes)):
                    #     if axes[j].has_data():
                    #         continue  # if axes has data, skip to the next one
                    #     fig.delaxes(axes[j])
                # finalize and close all this 
            plt.tight_layout()
            pdf.savefig(fig)
            plt.close()

           