# Things to do

## Priority Level 1
- [x] Remove layers from viewer on layer deletion
- [x] Pop merge modalities on modality removal (with warning)
- [x] Vis options on import (thumbnail)
- [x] Graph main options (write ims, to original size (i.e., leave output images cropped))
- [x] Save valid wsireg graph config
- [x] Run a registration!
- [x] wsireg, accept np array as mask
- [x] wsireg, accept geojson as mask
- [x] napari shape layer to wsireg
  - [x] cache layer data in output directory as geojson
- [x] in-memory-np-array image to wsireg
  - [x] Implement saving the image with metadata
- [x] Channel selection
- [x] Clear all info on adding graph to queue, graph completion or "Clear" button


## Priority Level 2
- [ ] Queueing system
  - [x] Queue GUI
  - [x] Smart thread worker
  - [ ] Access queue graphs (i.e., round trip from data model to GUI)

- [ ] Monitoring
  - [x] Store plots in np arrays after execution (`wsireg` update)
  - [ ] Visualize plots from executed graph


## Priority Level 3
- [ ] GUI for serial 3D experiments
- [ ] Interface to use shape data to evaluate registration quality
  - [ ] GUI to load in registered shape data
  - [ ] Compute DICE / Jaccard etc
