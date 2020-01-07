# PupilXimea
Pupil Labs plugin to record from Ximea Camera during Recording

## Dependencies


### Python Packages
Python Package Dependiencies outside the stock Pupil Capture Install are:

Xiapi - Available from ximea.com

Yaml - used to read in and out camera settings

#### With Package Managed Pupil Capture:
I installed these by manually copying them to /opt/pupil_capture - You may be able to put them in the ~/pupil_capture_settings/packages/ folder also, but this has not been tested.

#### With Source Pupil Capture
Install these with your package manager of choice in the python install used by pupil capture  

### Camera Settings .yaml file  
This code uses .yaml files to load known settings to the Ximea camaras.
Copy the cy.yaml file included in this codebase
