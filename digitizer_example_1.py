from CAENpy.CAENDigitizer import CAEN_DT5742_Digitizer
import pandas
import numpy
import time
import plotly.express as px

def configure_digitizer(digitizer: CAEN_DT5742_Digitizer):
    digitizer.set_sampling_frequency(MHz=5000)
    digitizer.set_record_length(1024)
    digitizer.set_max_num_events_BLT(1)
    digitizer.set_acquisition_mode('sw_controlled')
    digitizer.set_ext_trigger_input_mode('disabled')
    digitizer.write_register(0x811C, 0x000D0001)  # Enable busy signal on GPO.
    digitizer.set_fast_trigger_mode(enabled=True)
    digitizer.set_fast_trigger_digitizing(enabled=True)
    digitizer.enable_channels(group_1=True, group_2=True)
    digitizer.set_fast_trigger_threshold(22222)
    digitizer.set_fast_trigger_DC_offset(V=0)
    digitizer.set_post_trigger_size(0)
    for ch in [0, 1]:
        digitizer.set_trigger_polarity(channel=ch, edge='rising')

def convert_dicitonaries_to_data_frame(waveforms: dict):
    data = []
    for n_event, event_waveforms in enumerate(waveforms):
        for n_channel, waveform_data in event_waveforms.items():
            if n_channel not in ['CH0', 'trigger_group_1']:  # Filtro per CH0 e TR0 (supponendo TR0 sia trigger_group_1)
                continue
            df = pandas.DataFrame(waveform_data)
            df['n_event'] = n_event
            df['n_channel'] = n_channel
            df.set_index(['n_event', 'n_channel'], inplace=True)
            data.append(df)
    return pandas.concat(data) if data else pandas.DataFrame()

if __name__ == '__main__':
    # Connessione al digitizer
    d = CAEN_DT5742_Digitizer(LinkNum=0)
    print('Connected with:', d.idn)

    # Configura il digitizer
    configure_digitizer(d)
    d.set_max_num_events_BLT(1024)  # Configura la massima capacità del buffer interno.

    # Acquisizione dati
    n_events = 0
    ACQUIRE_AT_LEAST_THIS_NUMBER_OF_EVENTS = 2222
    data_frames = []
    sampling_frequency = 2500  # Frequenza di campionamento in MHz

    with d:  # Abilita il digitizer per l'acquisizione
        print('Digitizer is enabled! Acquiring data...')
        while n_events < ACQUIRE_AT_LEAST_THIS_NUMBER_OF_EVENTS:
            time.sleep(0.05)
            waveforms = d.get_waveforms()  # Acquisisci i dati
            this_readout_n_events = len(waveforms)
            n_events += this_readout_n_events
            data_frame = convert_dicitonaries_to_data_frame(waveforms)

            # Aggiungi il timestamp in base alla finestra di acquisizione
            data_frame['Time (s)'] += (n_events - this_readout_n_events) * 1024 / sampling_frequency
            data_frames.append(data_frame)

            print(f'{n_events} out of {ACQUIRE_AT_LEAST_THIS_NUMBER_OF_EVENTS} were acquired.')

        print(f'A total of {n_events} events were acquired. Stopping digitizer.')

    # Unisci tutti i dati acquisiti in un unico DataFrame
    full_data = pandas.concat(data_frames)

    # Verifica dei dati
    print('Acquired data is:')
    print(full_data)

    # Crea il grafico
    fig = px.line(
        title='CAEN Digitizer Waveforms (CH0 and TR0)',
        data_frame=full_data.reset_index(),
        x='Time (s)',
        y='Amplitude (V)',
        color='n_channel',
        markers=True
    )
    fig.show()

    # Salva i dati su file solo per `CH0` e `TR0`
    if not full_data.empty:
        output_path = 'filtered_waveforms_CH0_TR0.txt'
        full_data.to_csv(output_path, sep='\t')
        print(f'Data for CH0 and TR0 saved to {output_path}')
    else:
        print('No data acquired for CH0 or TR0.')
