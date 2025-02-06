import sys
import numpy as np
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton
import pyqtgraph as pg
from rwave import rwaveclient

host = 'localhost'
port = 30001

class OscilloscopeApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout()
        
        # Graph widget
        self.plotWidget = pg.PlotWidget()
        self.plotWidget.setBackground('black')
        self.plotWidget.showGrid(x=True, y=True)
        self.plotWidget.addLegend()
        
        # Configure axes
        self.plotWidget.setLabel('left', 'Amplitude')
        self.plotWidget.setLabel('bottom', 'Samples')
        
        layout.addWidget(self.plotWidget)
        
        # Button
        self.button = QPushButton('Start Acquisition')
        self.button.clicked.connect(self.startAcquisition)
        layout.addWidget(self.button)
        
        self.setLayout(layout)
        self.setWindowTitle("Oscilloscope Viewer")
    
    def startAcquisition(self):
        self.button.setEnabled(False)
        data = self.acquireData()
        if data:
            self.plotData(data)
        self.button.setEnabled(True)
    
    def acquireData(self):
        with rwaveclient(host, port, verbose=True) as rwc:
            if rwc is None:
                return None
            # Configure acquisition
            rwc.send_cmd('sampling 750')
            rwc.send_cmd('grmask 0x1')
            rwc.send_cmd('chmask 0x0003')
            rwc.send_cmd("start")
            rwc.send_cmd('swtrg 1024')
            rwc.send_cmd('readout')
            rwc.send_cmd('download')
            data = rwc.download()
            rwc.send_cmd('stop')
            
        return data
    
    def plotData(self, data):
        self.plotWidget.clear()
        colors = ['yellow', 'cyan']
        
        # Plot first event only (modify as needed)
        event = data[0]  # Primo evento acquisito
        x = np.arange(len(event[0]))
        
        for ch, color in zip(event.keys(), colors):
            y = event[ch]
            self.plotWidget.plot(x, y, pen=pg.mkPen(color, width=2), name=f'Channel {ch}')

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = OscilloscopeApp()
    window.show()
    sys.exit(app.exec_())
