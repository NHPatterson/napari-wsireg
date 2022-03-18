# Things to do

## first priority, initial release, working version
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
- [ ] Channel selection


## second priority
- [x] Queueing system
  - [x] Queue GUI
  - [x] Smart thread worker

- [ ] Monitoring
  - [ ] See plots


## third priority
- [ ] GUI for serial 3D experiments
