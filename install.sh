#!/bin/bash

# activating environment for Python --> uncomment first two lines if you do not have any environment
# echo "Creating a Python virtual environment..."
# python3 -m venv ../myenv
echo "Activating the virtual environment..."
source ../myenv/bin/activate

# installing dependencies
echo -e "\033[34minstalling CAENUSBdrvB. Progressing...\033[0m"
cd dependencies/CAENUSBdrvB-v1.6.0/
sudo ./install.sh
echo -e "\033[32m  CAENUSBdrvB installed successfully!\033[0m"

echo -e "\033[34minstalling CAENVMELib. Progressing...\033[0m"
cd ../../dependencies/CAENVMELib-v4.0.2/lib/
sudo sh install_x64
echo -e "\033[32m  CAENVMELib installed successfully!\033[0m"

echo -e "\033[34minstalling CAENComm. Progressing...\033[0m"
cd ../../../dependencies/CAENComm-v1.7.0/lib/
sudo sh install_x64
echo -e "\033[32m  CAENComm installed successfully!\033[0m"

pip install plotly flask pandas pyroot uproot


# installing CAEN digitizer libraries
echo -e "\033[34minstalling CAENComm. Progressing...\033[0m"
cd ../../../dependencies/CAENComm-v1.7.0/lib/
sudo sh install_x64
echo -e "\033[32m  CAENComm installed successfully!\033[0m"

echo -e "\033[34minstalling CAENDigitizer library. Progressing...\033[0m"
cd ../../../digitizerDT5742/CAENDigitizer-v2.17.3/lib/
sudo sh install_x64
echo -e "\033[32m  CAENDigitizer library installed successfully!\033[0m"

echo -e "\033[34minstalling CAENDigitizer python library. Progressing...\033[0m"
cd ../../../
pip install git+https://github.com/SengerM/CAENpy
echo -e "\033[32m  CAENpy library installed successfully!\033[0m"