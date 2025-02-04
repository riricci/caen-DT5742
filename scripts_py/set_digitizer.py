from CAENpy.CAENDigitizer import CAEN_DT5742_Digitizer
from CAENpy.CAENDigitizer import decode_event_waveforms_to_python_friendly_stuff
import pandas
import numpy
import time
import plotly.express as px


def configure_digitizer(digitizer: CAEN_DT5742_Digitizer, freq=5000, BLT=1, DC_offset=0):
    digitizer.set_sampling_frequency(MHz=freq) # possible values: 5000, 2500, 1000, 750
    digitizer.set_record_length(1024) # possible values: 1024, 512, 256, 136
    digitizer.set_max_num_events_BLT(BLT) # number of events taken in the same window
    digitizer.set_acquisition_mode('sw_controlled') 
    digitizer.set_ext_trigger_input_mode('acquisition only') # to be studied
    digitizer.write_register(0x811C, 0x000D0001)  # Enable busy signal on GPO.
    digitizer.set_fast_trigger_mode(enabled=False) # enables fast trigger on TR0 channel
    digitizer.set_fast_trigger_digitizing(enabled=True) # enables fast trigger digitizing. If False, nothing works
    digitizer.enable_channels(group_1=True, group_2=True) # group 1: from 0 to 7, group 2: from 8 to 15
    digitizer.set_fast_trigger_threshold(20934) # to be studied
    # DRS4_CORRECTION to be implemented here
    for ch in [0, 1]:
        digitizer.set_channel_DC_offset(channel=ch, V=DC_offset) # DC offset for CH0 and CH1
    digitizer.set_fast_trigger_DC_offset(32768) # just adjusting the offset of the TRO channel
    digitizer.set_post_trigger_size(0) # percentage (0-100, only int) of the record length to be visualized after the trigger.
    for ch in [0, 1]:
        digitizer.set_trigger_polarity(channel=ch, edge='rising')
    
    
def convert_dictionaries_to_data_frame(waveforms: dict):
    data = []
    for n_event, event_waveforms in enumerate(waveforms):
        for n_channel, waveform_data in event_waveforms.items():
            if n_channel not in ['CH0','CH1', 'trigger_group_1']:  # consider only CH0 e TR0
                continue
            df = pandas.DataFrame(waveform_data)
            df['n_event'] = n_event
            df['n_channel'] = n_channel
            df.set_index(['n_event', 'n_channel'], inplace=True)
            data.append(df)
    return pandas.concat(data) if data else pandas.DataFrame()

def get_corrected_waveforms(digitizer: CAEN_DT5742_Digitizer, get_time=True, get_ADCu_instead_of_volts=False, DRS4_correction = True) -> list:
    try:
        # Allocate memory for the event and buffer
        digitizer._allocateEvent()
        digitizer._mallocBuffer()
        # Let's do crazy things
        if digitizer.get_acquisition_status()['acquiring now'] == False:
            raise RuntimeError(f'The digitizer is already acquiring, cannot start a new acquisition.')
        if DRS4_correction == True:
            digitizer._LoadDRS4CorrectionData(MHz=digitizer.get_sampling_frequency())
        digitizer._DRS4_correction(enable=DRS4_correction) #guardare da dove viene nella classe
        # digitizer._start_acquisition()
        digitizer.get_acquisition_status() # This makes it work better. Don't know why.
        
        # Read the data from the digitizer
        digitizer._ReadData()
        n_events = digitizer._GetNumEvents()
        events = []
        # Process each event
        for n_event in range(n_events):
            digitizer._GetEventInfo(n_event)
            digitizer._DecodeEvent()
            event = digitizer.eventObject.contents
            event_waveforms = decode_event_waveforms_to_python_friendly_stuff(
                event,
                ADC_peak_to_peak_dynamic_range_volts=1 if not get_ADCu_instead_of_volts else None,
                time_axis_parameters=dict(
                    sampling_frequency=digitizer.get_sampling_frequency() * 1e6,
                    post_trigger_size=digitizer.get_post_trigger_size(),
                    fast_trigger_mode=digitizer.get_fast_trigger_mode(),
                ) if get_time else None,
            )
            events.append(event_waveforms)

        return events
    except Exception as e:
        print(f"Error while acquiring waveforms: {e}")
        return []
    finally:
        # Free allocated memory after acquisition
        digitizer._freeEvent()
        digitizer._freeBuffer()
    
def start_continuous_software_trigger(digitizer: CAEN_DT5742_Digitizer):
    """
    Configura il digitizer per il trigger software continuo e avvia l'acquisizione.
    
    :param digitizer: Istanza del digitizer (CAEN_DT5742_Digitizer).
    """
    if not isinstance(digitizer, CAEN_DT5742_Digitizer):
        raise TypeError("L'oggetto passato non è un'istanza valida del digitizer.")

    # Disabilita il trigger esterno (TRIG IN)
    digitizer.set_ext_trigger_input_mode('disabled')

    # Disabilita il Fast Trigger
    digitizer.set_fast_trigger_mode(False)
    print("Fast Trigger disabilitato.")

    # Avvia l'acquisizione software
    digitizer._start_acquisition()
    
    print("Acquisizione avviata con trigger software continuo.")
    
    import numpy as np
import matplotlib.pyplot as plt

