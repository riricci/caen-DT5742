from CAENpy.CAENDigitizer import CAEN_DT5742_Digitizer
from digitizer_example_1 import configure_digitizer, convert_dicitonaries_to_data_frame

def extract_baseline_from_channel(digitizer, channel=0):
    """
    Extract the baseline (DC offset) of a specific channel.
    
    Arguments:
    ----------
    digitizer : CAEN_DT5742_Digitizer
        Instance of the digitizer.
    channel : int
        Channel number to extract the baseline from (default is 0).
    
    Returns:
    --------
    int
        The DC offset value of the specified channel.
    """
    try:
        baseline = digitizer.get_channel_DC_offset(channel)
        print(f"The baseline (DC offset) for channel {channel} is: {baseline}")
        return baseline
    except Exception as e:
        print(f"Error extracting baseline for channel {channel}: {e}")
#         return None


if __name__ == "__main__":
    # Connect to digitizer
    digitizer = CAEN_DT5742_Digitizer(LinkNum=0)
    print("Connected with:", digitizer.idn)
    
    # Configure digitizer
    configure_digitizer(digitizer)
    
    # Extract baseline for CH0
    channel = 0
    baseline = extract_baseline_from_channel(digitizer, channel=channel)
    
    if baseline is not None:
        print(f"Baseline for CH{channel}: {baseline}")
    else:
        print(f"Failed to extract baseline for CH{channel}.")

    digitizer.set_channel_DC_offset(channel, 0)  # Set the DC offset to 0 for CH0
    baseline = extract_baseline_from_channel(digitizer, channel=channel)
    # Close connection
    digitizer.close()
    print("Digitizer connection closed.")
