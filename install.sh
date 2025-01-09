#!/bin/bash -e

# installing dependencies
echo "installing CAENUSBdrvB. Progressing..."
cd dependencies/CAENUSBdrvB-v1.6.0/
./install.sh
echo "  CAENUSBdrvB installed successfully!"

echo "installing CAENVMELib. Progressing..."
cd ../../dependencies/CAENVMELib-v4.0.2/lib/
sh install_x64
echo "  CAENVMELib installed successfully!"

echo "installing CAENComm. Progressing..."
cd ../../../dependencies/CAENComm-v1.7.0/lib/
sh install_x64
echo "  CAENComm installed successfully!"

# installing CAEN digitizer libraries
echo "installing CAENComm. Progressing..."
cd ../../../dependencies/CAENComm-v1.7.0/lib/
sh install_x64
echo "  CAENComm installed successfully!"

echo "installing CAENDigitizer library. Progressing..."
cd ../../../digitizerDT5742/CAENDigitizer-v2.17.3/lib/
sh install_x64
echo "  CAENDigitizer library installed successfully!"