    -----------------------------------------------------------------------------

                   --- CAEN SpA - Computing Systems Division ---

    -----------------------------------------------------------------------------

    CAENComm Library

    Installation and Use Instructions

    -----------------------------------------------------------------------------


 The complete documentation can be found in the User's Manual on CAEN's web
 site at: https://www.caen.it.


 Content
 -------

 Readme.txt       : This file.
 ReleaseNotes.txt : Release Notes of the last software release.
 lib              : Directory containing the library binary file
                    and an install script.
 include          : Directory containing the relevant header files.


 System Requirements
 -------------------

 - CAENVMELib library (version 3.3 or greater).
 - Linux glibc (version 2.19 or greater)


 Installation notes
 ------------------

  - Login as root

  - Copy the needed files on your work directory

To install the dynamic library:

  - Go to the library directory

  - Execute: 
      sh install               to install the 32bit version of the library 
      sh install_x64           to install the 64bit version of the library 
      sh install_arm64         to install the arm 64bit version of the library 

 The installation copies and installs the library in /usr/lib.


  Support
 ------

 For technical support, go to https://www.caen.it/mycaen/support/ (login and
 MyCAEN+ account required).

 If you don't have an account or want to update your old one, find the instructions
 at https://www.caen.it/support-services/getting-started-with-mycaen-portal/.
