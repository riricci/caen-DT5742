# CAEN digitizer Installation Guide
Installation guide for CAEN digitizer DT5742B.



## USB driver installation
- **Requirements**:
  - *UEFI Secure boot* has to be disabled (can be done from system bios)
  - `dkms` (version 2.19 or greater)
  - `glibc` (version 2.19 or greater)
  - `libusb-1.0` (version 1.0.19 or greater)
  
1. **Install Dependencies**:
    ```bash
    sudo apt update
    sudo apt install dkms build-essential linux-headers-$(uname -r) kmod
    sudo apt install libusb-1.0-0-dev
    ```
	
	CAEN USB Driver installation:

    ```bash
	cd /dependencies/CAENUSBdrvB-v1.6.0/
	sudo ./install.sh
    ```

	CAENVME library installation (needed also if not using VME communication)
	```bash
	cd /dependencies/CAENVMELib-v4.0.2/
	sudo ./install.sh
    ```
		verify the installation with this command: 
		


3. **Copy library Files and add library path**:
   - Navigate to the `lib` directory:
     ```bash
     cd CAENVMELib-x.y.z/lib
     ```
   - Copy the library file:
     ```bash
     sudo install ./x64/libCAENVME.so.v4.0.2 /usr/lib/
     ```
   - Create a symbolic link:
     ```bash
     sudo ln -sf /usr/lib/libCAENVME.so.v4.0.2 /usr/lib/libCAENVME.so
     ```

4. **Add Library Path**:
   - Add `/usr/lib` to `ldconfig`:
     ```bash
     echo "/usr/lib" | sudo tee -a /etc/ld.so.conf.d/caen-libraries.conf
     sudo ldconfig
     ```

5. **Install Header Files**:
   - Copy header files to `/usr/include/`:
     ```bash
     sudo install -m 644 ../include/* /usr/include/
     ```

6. **Verify Installation**:
   - Check if the library is recognized:
     ```bash
     ldconfig -p | grep CAENVME
     ```
     
     
     

## Installation Instructions
1. **Download and Extract**:
   - Obtain the library from the official [CAEN website](https://www.caen.it) and extract it.

2. **Install Dependencies**:
   - Install `libusb-1.0`:
     ```bash
     sudo apt install libusb-1.0-0-dev
     ```

3. **Copy Library Files**:
   - Navigate to the `lib` directory:
     ```bash
     cd CAENVMELib-x.y.z/lib
     ```
   - Copy the library file:
     ```bash
     sudo install ./x64/libCAENVME.so.v4.0.2 /usr/lib/
     ```
   - Create a symbolic link:
     ```bash
     sudo ln -sf /usr/lib/libCAENVME.so.v4.0.2 /usr/lib/libCAENVME.so
     ```

4. **Add Library Path**:
   - Add `/usr/lib` to `ldconfig`:
     ```bash
     echo "/usr/lib" | sudo tee -a /etc/ld.so.conf.d/caen-libraries.conf
     sudo ldconfig
     ```

5. **Install Header Files**:
   - Copy header files to `/usr/include/`:
     ```bash
     sudo install -m 644 ../include/* /usr/include/
     ```

6. **Verify Installation**:
   - Check if the library is recognized:
     ```bash
     ldconfig -p | grep CAENVME
     ```

## Support
For technical support, visit [CAEN Support Portal](https://www.caen.it/mycaen/support/) (login required).

---

Replace `x.y.z` with the appropriate version of the library.

