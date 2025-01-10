# CAEN digitizer Installation Guide
Installation guide for CAEN digitizer DT5742B for Linux systems. The repository already includes all the necessary drivers and files.
It is possible to install all at once (i.e. installation steps from 2 to 5) by typing: 

```
source ./install.sh
```
the script will ask for sudo privileges.

1. **Requirements**:
  - *UEFI Secure boot* has to be disabled (can be done from system bios)
  - `dkms` (version 2.19 or greater)
  - `glibc` (version 2.19 or greater)
  - `libusb-1.0` (version 1.0.19 or greater)
  - `gnuplot` (to run WaveDump software by dump)
  
2. **Install Dependencies**:
    ```
    sudo apt update
    sudo apt install dkms build-essential linux-headers-$(uname -r) kmod
    sudo apt install libusb-1.0-0-dev
    ```
	
	CAEN USB Driver installation. From caen-dt:
    ```
	cd dependencies/CAENUSBdrvB-v1.6.0/
	sudo ./install.sh
    ```

	- CAENVME library installation (needed also if not using VME communication). From caen-dt:
    ```
    cd dependencies/CAENVMELib-v4.0.2/lib/
    sudo sudo sh install_x64 # or _x32 _arm64 depending on your system.
    ```
	    Now you should see the libraries in /usr/lib. You can check the installation by typing: 
        ```
	    	ls /usr/lib | grep libCAENVME
        ldconfig -p | grep CAENVME
        ```

        
  - CAENComm library installation. From caen-dt:
    ```
    cd dependencies/CAENVMELib-v4.0.2/lib/
    sudo sudo sh install_x64 # or _x32 _arm64 depending on your system.
    ```
	    Now you should see the libraries in /usr/lib. You can check the installation by typing: 
        ```
		    ls /usr/lib | grep libCAENComm.so
        ldconfig -p | grep libCAENComm.so
        ```

3. **Digitizer installation**:
  
  - CAENDigitizer library installation. From caen-dt:
    ```
    cd digitizerDT5742/lib/
    sudo sudo sh install_x64 # or _x32 _arm64 depending on your system.
    ```
	    Now you should see the libraries in /usr/lib. You can check the installation by typing: 
        ```
		  ls /usr/lib | grep CAENDigitizer.so
      ldconfig -p | grep CAENDigitizer.so
        ```


5. **CAENpy repository installation**:
    
    From caen-dt:
    ```
    pip install git+https://github.com/SengerM/CAENpy
    ```
    Now also the CAENpy library is ready to be used. In the repository some examples and informations about basic use of the digitizer are already present. 

     
     
