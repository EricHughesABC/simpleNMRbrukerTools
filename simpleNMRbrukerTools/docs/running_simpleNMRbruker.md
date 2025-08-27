## Instructions to run simpleNMR in Topspin

### Introduction

When simpleNMRbrukerTools has been installed successfully, the flowbar menu interface will show the simpleNMR menu and the single menu item underneath as displayed in Figure 1.

![simpleNMR installed in Topspin](images/simpleNMRinstalledFlowbar.png "simpleNMR installed in Topspin")

***Figure 1*** simpleNMR installed in Topspin

### Prerequisites for Successfully Running simpleNMR

First, open a directory that contains a set of 1 and 2-D experiments of the molecule under investigation.

Ensure that a mol file of the molcule is saved in the toplevel directory such that it is displayed by Topspin. Figure 2 shows Topspin open at a set of 1 and 2-D data with the molecule displayed in the movelcule viewer window. In the main window the HSQC experiment has been opened.

![Open data set](images/topsinMoleculeHSQC.png "Open HSQC dataset with molecule")

***Figure 2*** Topspin showing open data set and the molecule under investigation.

### Peak picking data and Integration

Peak pick the data in the set of experiments as precisely as possible. Make sure that all the spectra that will be used in the analysis are correctly referenced and the referencing  is consistent with each other.

Typically, the following spectra are used in the analysis

  - HSQC (peaks and integrals) Required
  - HMBC
  - COSY
  - 1D Carbon

A HSQC data set is required and it should be multiplicity-edited, otherwise a DEPT-135 dataset should also be included.
The HSQC data set should be peak picked and the integrals should also be taken. This is to ensure that the correct sign of the data is recorded correctly. All other 2-D data just need to be peak picked if they are to be used in the analysis.
1-D proton data and 1-D pureshift data are best left out of the analysis in complicated systems, but can be used to help with centering the peak-picking of the 2-D data-sets.
The analysis can be run without the 1-D carbon spectrum, but if one has a consistent carbon then it is best to include it in the analysis.

Please note, at the moment there iare less checks on the data before it is submitted for analysis compared to the more advanced MNOVA version of simpleNMR, therefore please pay extra attention to the number of peaks being picked in the different datasets, especially the 1-D carbon and HSQC and manually check that they are consistent with molecule that is being assigned.

### Starting the simpleNMR analysis

#### Choosing the Data Folder

With the NMR datasets peak picked and integrated and Topspin open and pointing to the current dataset by having one data set open, click on the simpleNMR menu button to start  the analysis.

The program is quite slow the first time it is ran, so be patient. Eventually a directory dialog will open pointing to the current Topspin data set.


![simpleNMR Directory Dialog](images/DirectoryDialog.png "simpleNMR Directory Dialog")

***Figure 3*** simpleNMR Directory Dialog opened automatically at the current directory of the data sets.

Click OK if the directory displayed is correct or set the correct directory by opening a   file explorer dialog by clicking the folder icon.

#### Choosing the NMR Experiments for the simpleNMR analysis

The user is given the opportunity to choose which experiments will be used in the simpleNMR analysis. Only experiments that have been peak picked will be displayed in the dialog. Figure 4 shows the dialog with all the experiments with peaks in the dataset of experiments. The Figure also shows the user in the midst of setting the proton data to SKIP so that it will not be included in the analysis.

![Choosing the experiments for the analysis](images/ChooseExperiment.png "Choosing the experiments for the analysis")

***Figure 4*** Dialog box showing experiments that have been peak picked that can be used in the simpleNMR analysis. The 1-D proton spectrum is being set to SKIP by the user so that this experiment will not be part of the data that is used by the simpleNMR analysis.

#### Running the simpleNMR analysis

When the NMR experiments have been chosen the data is sent to the simpleNMR server for analysis. It can take a long time (30-45 seconds) before the analysis is completed. During this time there is no feedback to the user that the analysis is being performed. Please be patient.

Upon successful completion of the analysis the results will be displayed in the browser as an interactive webpage as shown in Figure 5.

![simpleNMR results](images/simpleNMRresults.png "simpleNMR results displayed in HTML web page" )

***Figure 5*** SimpleNMR results displayed in a html webpage that is interactive



