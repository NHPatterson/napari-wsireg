import shutil
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from tempfile import TemporaryDirectory

import napari
import numpy as np
from napari.qt.threading import thread_worker
from napari.utils import progress
from napari_plugin_engine import napari_hook_implementation
from napari.layers import Image, Shapes, Labels, Points
from qtpy.QtCore import QEvent, Qt, QThreadPool
from qtpy.QtWidgets import (
    QErrorMessage,
    QMessageBox,
    QFileDialog,
    QVBoxLayout,
    QListWidget,
    QMenu,
    QWidget,
    QScrollArea,
)
from wsireg.parameter_maps.preprocessing import ImagePreproParams
from wsireg.parameter_maps.reg_model import RegModel
from wsireg.reg_shapes import RegShapes
from wsireg.wsireg2d import WsiReg2D
from wsireg.wsireg2d import main as wsireg2d_main
from wsireg.utils.im_utils import ARRAYLIKE_CLASSES
from napari_wsireg.data import (
    FILE_ERROR_MESSAGE,
    TIFFFILE_EXTS,
    CziWsiRegImage,
    TiffFileWsiRegImage,
    WsiRegImage,
)
from napari_wsireg.gui.utils.file import open_file_dialog
from napari_wsireg.data.utils.image import guess_rgb, write_image_from_napari
from napari_wsireg.data.utils.shapes import napari_shapes_to_qp_geojson
from napari_wsireg.data.utils.transform import centered_flip, centered_transform
from napari_wsireg.gui.dialogs.add_merge import AddMerge
from napari_wsireg.gui.dialogs.add_modality import AddModality
from napari_wsireg.gui.setup_gui import SetupTab
from napari_wsireg.gui.setup_sub.modality import create_modality_item
from napari_wsireg.gui.queue import reg_queue_item, generate_queue_tag


class WsiReg2DMain(QWidget):
    def __init__(self, napari_viewer: napari.Viewer):
        super().__init__()

        self.viewer = napari_viewer

        self._temp_dir = TemporaryDirectory()
        self._threadpool = QThreadPool()
        self._threadpool.setMaxThreadCount(1)
        self._pbar: Optional[progress] = None
        self._n_graphs_registered: int = 0

        self.reg_graph: WsiReg2D = WsiReg2D(None, None)
        self.graph_queue: List[Tuple[WsiReg2D, Dict[str, bool]]] = []

        self.image_mods: List[str] = []
        self.attachment_mods: List[str] = []
        self.shape_mods: List[str] = []
        self.merge_mods: Dict[str, List[str]] = dict()
        self.mask_mods: Dict[str, str] = dict()

        self.image_data: Dict[str, WsiRegImage] = dict()
        self.layer_data: Dict[str, Any] = dict()
        self.image_spacings: Dict[str, float] = dict()
        self.attachment_keys: Dict[str, List[str]] = dict()

        main_layout = QVBoxLayout()
        main_layout.setAlignment(Qt.AlignTop)
        self.setLayout(main_layout)
        self.setup = SetupTab()

        self.add_mod_btn = self.setup.mod_ctrl.add_mod_btn
        self.add_ach_btn = self.setup.mod_ctrl.add_ach_btn
        self.add_shp_btn = self.setup.mod_ctrl.add_shp_btn
        self.add_msk_btn = self.setup.mod_ctrl.add_msk_btn

        self.add_mod_nap_btn = self.setup.mod_ctrl.add_mod_nap_btn
        self.add_ach_nap_btn = self.setup.mod_ctrl.add_ach_nap_btn
        self.add_shp_nap_btn = self.setup.mod_ctrl.add_shp_nap_btn
        self.add_msk_nap_btn = self.setup.mod_ctrl.add_msk_nap_btn

        self.del_mod_btn = self.setup.mod_ctrl.del_mod_btn
        self.clr_mod_btn = self.setup.mod_ctrl.clr_mod_btn
        self.edit_mod_btn = self.setup.mod_ctrl.edt_mod_btn

        self.mod_list = self.setup.mod_ctrl.mod_list
        self.mod_list.installEventFilter(self)

        self.current_mod_in_prepro = self.setup.prepro_ctrl.mod_in_prepro
        self.prepro_main_ctrl = self.setup.prepro_ctrl

        self.path_ctrl = self.setup.path_ctrl
        self.reg_models_box = self.setup.path_ctrl.reg_models
        self.add_reg_model = self.setup.path_ctrl.add_reg_model
        self.current_reg_models = self.setup.path_ctrl.current_reg_models

        self.graph_view = self.setup.graph_view

        model_names = [m.name for m in RegModel]
        model_names.append("from file")
        model_names.append("[reset]")

        for m in model_names:
            self.reg_models_box.addItem(m)

        self.run_reg_btn = self.setup.proj_ctrl.run_reg
        self.add_to_queue_btn = self.setup.proj_ctrl.add_to_queue
        self.write_config_btn = self.setup.proj_ctrl.write_config

        self.project_name_entry = self.setup.proj_ctrl.project_name_entry
        self.output_dir_select = self.setup.proj_ctrl.output_dir_select
        self.output_dir_entry = self.setup.proj_ctrl.output_dir_entry

        self.queue_list = self.setup.queue_ctrl.queue_list
        self.up_queue_btn = self.setup.queue_ctrl.queue_move_up_btn
        self.down_queue_btn = self.setup.queue_ctrl.queue_move_up_btn
        self.del_queue_btn = self.setup.queue_ctrl.queue_delete_btn
        self.progress_label = self.setup.queue_ctrl.current_running
        self.run_queue_btn = self.setup.queue_ctrl.run_queue_btn

        scroll = QScrollArea()
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.setup)
        self.layout().addWidget(scroll)

        # self.layout().setAlignment(scroll, Qt.AlignTop)
        # main_layout.addStretch(True)

        self.add_mod_btn.clicked.connect(lambda: self.add_data("image"))
        self.add_ach_btn.clicked.connect(lambda: self.add_data("attachment"))
        self.add_shp_btn.clicked.connect(lambda: self.add_data("shape"))
        self.add_msk_btn.clicked.connect(lambda: self.add_data("mask"))

        self.add_mod_nap_btn.clicked.connect(lambda: self.add_nap_data("image"))
        self.add_ach_nap_btn.clicked.connect(lambda: self.add_nap_data("attachment"))
        self.add_shp_nap_btn.clicked.connect(lambda: self.add_nap_data("shape"))
        self.add_msk_nap_btn.clicked.connect(lambda: self.add_nap_data("mask"))

        self.del_mod_btn.clicked.connect(self.delete_modality)
        self.clr_mod_btn.clicked.connect(lambda: self._clear_graph("clear"))
        self.edit_mod_btn.clicked.connect(self._edit_data)

        self.mod_list.itemDoubleClicked.connect(self._edit_data)
        self.mod_list.clicked.connect(self._switch_preprocessing_modality)

        # preprocessing connections
        self.prepro_main_ctrl.max_int_proj.stateChanged.connect(
            self._update_preprocessing
        )
        self.prepro_main_ctrl.as_uint8.stateChanged.connect(self._update_preprocessing)
        self.prepro_main_ctrl.contrast_enhance.stateChanged.connect(
            self._update_preprocessing
        )
        self.prepro_main_ctrl.invert_intensity.stateChanged.connect(
            self._update_preprocessing
        )
        self.prepro_main_ctrl.crop_to_mask_bbox.stateChanged.connect(
            self._update_preprocessing
        )
        self.prepro_main_ctrl.use_mask.stateChanged.connect(self._update_preprocessing)

        self.prepro_main_ctrl.rot_cc.valueChanged.connect(self._update_preprocessing)
        self.prepro_main_ctrl.downsampling.valueChanged.connect(
            self._update_preprocessing
        )

        self.prepro_main_ctrl.flip.currentTextChanged.connect(
            self._update_preprocessing
        )

        self.prepro_main_ctrl.channel_list.itemChanged.connect(
            self._update_preprocessing
        )

        # extra controls for coordination
        self.prepro_main_ctrl.rot_cc.valueChanged.connect(self._rotate_modality)

        self.prepro_main_ctrl.flip.currentTextChanged.connect(self._flip_modality)

        # reg path connections
        self.path_ctrl.source_select.currentTextChanged.connect(self._reset_reg_model)
        self.path_ctrl.source_select.currentTextChanged.connect(
            self._update_path_possibilties
        )
        self.path_ctrl.thru_select.activated.connect(self._update_paths_on_through)
        self.path_ctrl.target_select.activated.connect(self._update_paths_on_target)

        self.add_reg_model.clicked.connect(self._add_reg_model_to_path)

        self.path_ctrl.add_reg_path.clicked.connect(self.add_reg_path_to_graph)
        self.path_ctrl.clear_all_paths.clicked.connect(self.clear_all_reg_paths)

        self.graph_view.refresh_graph.clicked.connect(self._update_reg_plot)

        # project management connections
        self.output_dir_select.clicked.connect(self.set_project_output_dir)
        self.write_config_btn.clicked.connect(self.save_graph_config)
        self.run_reg_btn.clicked.connect(self.run_registration_direct)
        self.add_to_queue_btn.clicked.connect(self.add_current_graph_to_queue)

        # queue managment
        # self.up_queue_btn.clicked.connect(lambda: self.move_queue_item("up"))
        # self.down_queue_btn.clicked.connect(lambda: self.move_queue_item("down"))
        self.del_queue_btn.clicked.connect(self.delete_queue_items)
        self.run_queue_btn.clicked.connect(self.run_registration_queue)

    def add_data(
        self,
        data_type: str,
        file_paths_in: Optional[Union[str, List[str]]] = None,
        no_dialog: bool = False,
    ) -> None:
        """
        Collect image modality path
        """
        if not file_paths_in:
            if data_type in ["shape", "attachment"] and len(self.image_mods) == 0:
                emsg = QErrorMessage(self)
                emsg.showMessage(
                    f"No image modalities are loaded for attachment of {data_type} data"
                )
                file_paths = None
            else:
                file_paths = open_file_dialog(
                    self,
                    single=False,
                    wd="",
                    data_type=data_type,
                )
        # if statement checks that open file dialog returned something
        else:
            file_paths = file_paths_in

        if file_paths:
            if not isinstance(file_paths, list):
                file_paths = [file_paths]

            for file_path in file_paths:
                if data_type == "image":
                    self._add_image_data(file_path, no_dialog)

                elif data_type == "attachment":
                    self._add_attachment_data(file_path, no_dialog)
                elif data_type == "shape":
                    self._add_shape_data(file_path, no_dialog)
                else:
                    self._add_mask_data(file_path, no_dialog)

                self._update_reg_plot()

    def _check_data_type(
        self, data_type: str, layer: Union[Image, Shapes, Labels, Points]
    ) -> bool:
        if (
            data_type in ["image", "attachment"]
            and isinstance(layer, (Image, Labels)) is False
        ):
            emsg = QErrorMessage(self)
            emsg.showMessage(
                "Current selected <i>napari</i> layer can't be added as an image or attachment"
                " image because it is not an image layer, but a"
                f" {str(type(layer)).split('.')[-1].replace('>','')} type"
            )
            return False
        if data_type in ["shape"] and isinstance(layer, (Shapes, Points)) is False:
            emsg = QErrorMessage(self)
            emsg.showMessage(
                "Current selected <i>napari</i> layer can't be added as an attachment shape "
                " because it is not a Shape or Point layer, but a"
                f" {str(type(layer)).split('.')[-1].replace('>','')} type"
            )
            return False
        if data_type in ["mask"] and isinstance(layer, Shapes) is False:
            emsg = QErrorMessage(self)
            emsg.showMessage(
                "Current selected <i>napari</i> layer can't be added as a mask "
                " because it is not a Shape"
                f" {str(type(layer)).split('.')[-1].replace('>','')} type. "
                "Right now, only shape layer polygons and rectangles can be added as"
                " masks from napari layers."
            )
            return False
        return True

    def add_nap_data(
        self,
        data_type: str,
    ) -> None:
        """
        Collect image modality path
        """

        curr_selection = self.viewer.layers.selection
        if len(curr_selection) > 1:
            emsg = QErrorMessage(self)
            emsg.showMessage("Only one layer from napari may be added at a time")
            return
        elif len(curr_selection) == 0:
            return

        selection = next(iter(curr_selection))

        addable_layer = self._check_data_type(data_type, selection)
        source_path = (
            selection.source.path if selection.source.path else "in-memory layer"
        )

        if addable_layer:
            if data_type in ["image"] and isinstance(selection, (Image, Labels)):
                self._add_image_data(
                    source_path,
                    no_dialog=False,
                    from_file=False,
                    selected_layer=selection,
                )
            if data_type in ["attachment"] and isinstance(selection, (Image, Labels)):
                self._add_attachment_data(
                    source_path,
                    no_dialog=False,
                    from_file=False,
                    selected_layer=selection,
                )
            if data_type in ["shape"] and isinstance(selection, (Shapes, Points)):
                self._add_shape_data(
                    source_path,
                    no_dialog=False,
                    from_file=False,
                    selected_layer=selection,
                )

            if data_type in ["mask"] and isinstance(selection, Shapes):
                self._add_mask_data(
                    source_path,
                    no_dialog=False,
                    from_file=False,
                    selected_layer=selection,
                )

            self._update_reg_plot()

    def _generate_random_name(self) -> str:
        import random
        import string

        letters = string.ascii_lowercase
        rstr = "".join(random.choice(letters) for i in range(5))
        return rstr

    def _get_image_data(
        self, file_path: Union[str, Path]
    ) -> Optional[Union[CziWsiRegImage, TiffFileWsiRegImage]]:

        if Path(file_path).suffix.lower() in TIFFFILE_EXTS:
            return TiffFileWsiRegImage(file_path)
        elif Path(file_path).suffix.lower() == ".czi":
            return CziWsiRegImage(file_path)
        else:
            emsg_d = QErrorMessage(self)
            err_msg = FILE_ERROR_MESSAGE.substitute(
                file_path=Path(file_path).name,
                ext=Path(file_path).suffix.lower(),
                tiff_ext=",".join(TIFFFILE_EXTS),
            )
            emsg_d.showMessage(err_msg)

            return None

    def _add_image_data(
        self,
        file_path: Union[str, Path],
        no_dialog: bool = False,
        from_file: bool = True,
        selected_layer: Optional[Union[Image, Labels]] = None,
    ):
        if from_file:
            image_data = self._get_image_data(file_path)
            if image_data:
                image_data_loaded = True
        else:
            image_data = None
            image_data_loaded = True

        if image_data_loaded:
            all_entities = self._get_all_entity_tags()
            added_mod = AddModality(
                file_path, parent=self, image_data=image_data, all_entities=all_entities
            )
            if not no_dialog:
                added_mod.setWindowTitle("Enter registration image information...")
                added_mod.setWindowModality(Qt.ApplicationModal)
                added_mod.exec_()
            else:
                rstr = self._generate_random_name()
                added_mod.tag.setText(rstr)
                added_mod.completed = True

            if added_mod.completed:
                mod_tag = str(added_mod.tag.text())
                mod_spacing = float(added_mod.spacing.text())
                mod_path = Path(file_path).name
                display_name = f"{mod_tag} : {mod_path} : {mod_spacing} (μm)"
                mod_item = create_modality_item(
                    mod_tag, mod_path, mod_spacing, "IMAGE", display_name
                )
                self.mod_list.addItem(mod_item)
                preprocessing, channel_names = added_mod.prepro_cntrl._export_data()

                self.image_mods.append(mod_tag)

                self.path_ctrl.source_select.addItem(mod_tag)
                self.image_data.update({mod_tag: image_data})
                self.image_spacings.update({mod_tag: mod_spacing})
                self.attachment_keys.update({mod_tag: []})

                if from_file:
                    self._run_add_image(
                        mod_tag,
                        image_data,
                        use_thumbnail=added_mod.use_thumbnail.isChecked(),
                    )
                    self.reg_graph.add_modality(
                        mod_tag,
                        file_path,
                        mod_spacing,
                        preprocessing=preprocessing,
                        channel_names=channel_names,
                    )
                else:
                    selected_layer.name = mod_tag
                    selected_layer.scale = [float(mod_spacing), float(mod_spacing)]
                    self.layer_data.update({mod_tag: selected_layer})
                    if file_path != "in-memory layer":
                        in_data = file_path
                    elif selected_layer.multiscale:
                        in_data = selected_layer.data[0]
                    else:
                        in_data = selected_layer.data

                    self.reg_graph.add_modality(
                        mod_tag,
                        in_data,
                        mod_spacing,
                        preprocessing=preprocessing,
                    )

                self._update_path_possibilties()

    def _get_all_entity_tags(self):
        all_entities = []
        all_entities.extend(self.image_mods)
        all_entities.extend(self.attachment_mods)
        all_entities.extend(self.shape_mods)
        all_entities.extend(list(self.merge_mods.keys()))
        all_entities.extend(list(self.mask_mods.keys()))
        return all_entities

    def _run_add_image(
        self,
        mod_tag: str,
        image_data: Union[TiffFileWsiRegImage, CziWsiRegImage],
        use_thumbnail: bool = False,
        attachment_mod: Optional[str] = None,
    ):
        self._pbar = progress(total=0)
        self._pbar.set_description(f"reading {mod_tag} image")

        micro_reader_worker = self._prepare_image_data(
            mod_tag,
            image_data,
            use_thumbnail=use_thumbnail,
            attachment_mod=attachment_mod,
        )
        micro_reader_worker.start()
        micro_reader_worker.returned.connect(self._add_image_to_viewer)
        micro_reader_worker.finished.connect(
            lambda: self._pbar.set_description(f"finished reading {mod_tag} image")
        )
        micro_reader_worker.finished.connect(self._pbar.close)

    @thread_worker
    def _prepare_image_data(
        self,
        mod_tag: str,
        image_data: Union[TiffFileWsiRegImage, CziWsiRegImage],
        use_thumbnail: bool = False,
        attachment_mod: Optional[str] = None,
    ):
        if attachment_mod:
            image_data._pixel_spacing = (
                self.image_spacings[attachment_mod],
                self.image_spacings[attachment_mod],
            )
        if isinstance(image_data, TiffFileWsiRegImage) or not use_thumbnail:
            image_data.prepare_image_data()
        elif isinstance(image_data, CziWsiRegImage) and use_thumbnail:
            image_data._get_thumbnail()

        return mod_tag, image_data, use_thumbnail

    def _add_image_to_viewer(
        self, data: Tuple[str, Union[TiffFileWsiRegImage, CziWsiRegImage], bool]
    ):
        mod_tag, image_data, use_thumbnail = data
        channel_names = [f"{mod_tag}-{c}" for c in image_data.channel_names]
        if image_data.is_rgb:
            channel_names = mod_tag
        if use_thumbnail:
            thumbnail_im = image_data.thumbnail.compute()
            self.layer_data.update(
                {
                    mod_tag: self.viewer.add_image(
                        thumbnail_im,
                        channel_axis=None
                        if image_data.is_rgb
                        else image_data.channel_axis,
                        name=channel_names,
                        scale=image_data.thumbnail_spacing,
                        rgb=image_data.is_rgb,
                    )
                }
            )
        else:
            self.layer_data.update(
                {
                    mod_tag: self.viewer.add_image(
                        image_data.dask_pyr,
                        channel_axis=None
                        if image_data.is_rgb
                        else image_data.channel_axis,
                        name=channel_names,
                        scale=image_data.pixel_spacing,
                        rgb=image_data.is_rgb,
                    )
                }
            )

    def _add_attachment_data(
        self,
        file_path: Union[str, Path],
        no_dialog: bool = False,
        from_file: bool = True,
        selected_layer: Optional[Union[Image, Labels]] = None,
    ):
        if len(self.attachment_keys.keys()) == 0:
            emsg = QErrorMessage(self)
            emsg.showMessage(
                "No modalities have been defined for attachment\n"
                "Please add images for registration prior to attaching"
            )
            return
        if from_file:
            image_data = self._get_image_data(file_path)
            if image_data:
                image_data_loaded = True
        else:
            image_data = None
            image_data_loaded = True

        all_entities = self._get_all_entity_tags()

        if image_data_loaded:
            try:
                added_mod = AddModality(
                    file_path,
                    parent=self,
                    attachment=True,
                    attachment_tags=self.image_mods,
                    image_spacings=self.image_spacings,
                    all_entities=all_entities,
                )
                if not no_dialog:
                    added_mod.setWindowTitle("Enter attachment image information...")
                    added_mod.setWindowModality(Qt.ApplicationModal)
                    added_mod.exec_()
                else:
                    rstr = self._generate_random_name()
                    added_mod.tag.setText(rstr)
                    added_mod.completed = True

            except UnboundLocalError:
                return

        if added_mod.completed:
            mod_tag = str(added_mod.tag.text())
            mod_spacing = float(added_mod.spacing.text())
            mod_path = Path(file_path).name
            attachment_modality = added_mod.attachment_combo.currentText()
            display_name = f"{mod_tag} : {mod_path} : {mod_spacing} (μm)"
            mod_item = create_modality_item(
                mod_tag,
                mod_path,
                mod_spacing,
                "ATTACHMENT_IMAGE",
                display_name,
                attachment_modality=attachment_modality,
            )
            self.mod_list.addItem(mod_item)
            self.image_data.update({mod_tag: image_data})
            self.image_spacings.update({mod_tag: mod_spacing})
            if from_file:
                self._run_add_image(
                    mod_tag,
                    image_data,
                    use_thumbnail=added_mod.use_thumbnail.isChecked(),
                    attachment_mod=attachment_modality,
                )
                self.reg_graph.add_attachment_images(
                    attachment_modality, mod_tag, file_path, mod_spacing
                )
            else:
                selected_layer.name = mod_tag
                self.layer_data.update({mod_tag: selected_layer})
                if file_path != "in-memory layer":
                    in_data = file_path
                elif selected_layer.multiscale:
                    in_data = selected_layer.data[0]
                else:
                    in_data = selected_layer.data

                self.reg_graph.add_attachment_images(
                    attachment_modality, mod_tag, in_data, mod_spacing
                )

            self._update_preprocessing()
            self.attachment_mods.append(mod_tag)
            self.attachment_keys[attachment_modality].append(mod_tag)

    def _determine_attachment_level(
        self,
        layer: Union[Image, Labels, Shapes, Points],
        attachment_modality: str,
        is_shapes: bool = False,
    ):
        """Infer the spacing of an attachment layer based on the data
        Added layers aren't necessarily attached so the they may not be in their proper
        pixel spacing"""
        current_layer_spacing = layer.scale
        # attached_scale = self.layer_data[attachment_modality].scale
        attached_base_scale = self.image_data[attachment_modality].pixel_spacing

        # if np.array_equal(attached_scale, attached_base_scale):
        #     current_spacing = attached_base_scale[0]
        # else:
        #     current_spacing = self.image_data[attachment_modality].thumbnail_spacing[0]

        if is_shapes:
            new_shapes = []
            for shape in layer.data:
                new_shapes.append(
                    shape / (attached_base_scale[0] / current_layer_spacing[0])
                )
            layer.data = new_shapes
        layer.scale = attached_base_scale

    def _add_shape_data(
        self,
        file_path: Union[str, Path],
        no_dialog: bool = False,
        from_file: bool = True,
        selected_layer: Optional[Union[Image, Labels]] = None,
    ):
        if len(self.attachment_keys.keys()) == 0:
            emsg = QErrorMessage(self)
            emsg.showMessage(
                "No modalities have been defined for attachment\n"
                "Please add images for registration prior to attaching"
            )
            return

        if from_file:
            shape_data = RegShapes(file_path)

        all_entites = self._get_all_entity_tags()

        added_mod = AddModality(
            file_path,
            parent=self,
            attachment=True,
            attachment_tags=self.image_mods,
            image_spacings=self.image_spacings,
            all_entities=all_entites,
        )
        if not no_dialog:
            added_mod.setWindowTitle("Enter attachment shape information...")
            added_mod.setWindowModality(Qt.ApplicationModal)
            added_mod.exec_()
        else:
            rstr = self._generate_random_name()
            added_mod.tag.setText(rstr)
            added_mod.completed = True

        if added_mod.completed:
            mod_tag = str(added_mod.tag.text())
            mod_spacing = float(added_mod.spacing.text())
            mod_path = Path(file_path).name
            attachment_modality = added_mod.attachment_combo.currentText()
            display_name = f"{mod_tag} : {mod_path} : {mod_spacing} (μm)"
            mod_item = create_modality_item(
                mod_tag,
                mod_path,
                mod_spacing,
                "SHAPE",
                display_name,
                attachment_modality=attachment_modality,
            )
            self.mod_list.addItem(mod_item)
            self.shape_mods.append(mod_tag)
            self.attachment_keys[attachment_modality].append(mod_tag)
            if from_file:
                self._add_shapes_to_viewer(mod_tag, shape_data, mod_spacing)
                self.reg_graph.add_attachment_shapes(
                    attachment_modality, mod_tag, file_path
                )
            else:
                self._determine_attachment_level(
                    selected_layer, attachment_modality, is_shapes=True
                )
                selected_layer.name = mod_tag
                self.layer_data.update({mod_tag: selected_layer})
                self.reg_graph.add_attachment_shapes(
                    attachment_modality, mod_tag, file_path
                )

    def _add_mask_data(
        self,
        file_path: Union[str, Path],
        no_dialog: bool = False,
        from_file: bool = True,
        selected_layer: Optional[Union[Image, Labels]] = None,
    ):
        if len(self.attachment_keys.keys()) == 0:
            emsg = QErrorMessage(self)
            emsg.showMessage(
                "No modalities have been defined for attachment\n"
                "Please add images for registration prior to attaching"
            )
            return

        is_shapes = False
        all_entities = self._get_all_entity_tags()
        if from_file:
            if Path(file_path).suffix.lower() in [".geojson", ".json"]:
                mask_data = RegShapes(file_path)
                is_shapes = True
            else:
                mask_data = self._get_image_data(file_path)

        added_mod = AddModality(
            file_path,
            parent=self,
            attachment=True,
            attachment_tags=self.image_mods,
            image_spacings=self.image_spacings,
            all_entities=all_entities,
        )
        if not no_dialog:
            added_mod.setWindowTitle("Enter image mask info...")
            added_mod.setWindowModality(Qt.ApplicationModal)
            added_mod.exec_()
        else:
            rstr = self._generate_random_name()
            added_mod.tag.setText(rstr)
            added_mod.completed = True

        if added_mod.completed:
            mod_tag = str(added_mod.tag.text())
            mod_spacing = float(added_mod.spacing.text())
            mod_path = Path(file_path).name
            attachment_modality = added_mod.attachment_combo.currentText()
            display_name = f"{mod_tag} : {mod_path} : {mod_spacing} (μm)"
            mod_item = create_modality_item(
                mod_tag,
                mod_path,
                mod_spacing,
                "MASK",
                display_name,
                attachment_modality=attachment_modality,
            )
            self.mod_list.addItem(mod_item)
            self.attachment_keys[attachment_modality].append(mod_tag)
            if from_file:
                if is_shapes:
                    self._add_shapes_to_viewer(mod_tag, mask_data, mod_spacing)
                else:
                    mask_data._pixel_spacing = (mod_spacing, mod_spacing)
                    self._run_add_image(
                        mod_tag,
                        mask_data,
                        use_thumbnail=False,
                    )
                self.reg_graph.modalities[attachment_modality]["mask"] = file_path
            else:
                self._determine_attachment_level(
                    selected_layer, attachment_modality, is_shapes=True
                )
                selected_layer.name = mod_tag
                self.layer_data.update({mod_tag: selected_layer})
                temp_dir = self._temp_dir.name
                output_fp = (
                    Path(temp_dir) / f"{attachment_modality}-mask-tempdir.geojson"
                )
                output_fp = napari_shapes_to_qp_geojson(
                    self.layer_data[mod_tag], str(output_fp)
                )
                self.reg_graph.modalities[attachment_modality]["mask"] = output_fp
        self.mask_mods.update({mod_tag: attachment_modality})

    def _add_shapes_to_viewer(
        self, mod_tag: str, shape_data: RegShapes, mod_spacing: float
    ):
        shape_arrays, shape_props, shape_text = self._get_shape_data_from_reg_shapes(
            shape_data
        )

        self.layer_data.update(
            {
                mod_tag: self.viewer.add_shapes(
                    shape_arrays,
                    scale=(mod_spacing, mod_spacing),
                    properties=shape_props,
                    text=shape_text,
                    shape_type="polygon",
                    name=mod_tag,
                )
            }
        )

    def _get_shape_data_from_reg_shapes(
        self, shape_data: RegShapes
    ) -> Tuple[List[np.ndarray], Dict[str, List[str]], Dict[str, Union[str, int]]]:
        shape_arrays = [s["array"][:, [1, 0]] for s in shape_data.shape_data]
        shape_props = {"name": shape_data.shape_names}
        shape_text = {
            "text": "{name}",
            "color": "white",
            "anchor": "center",
            "size": 12,
        }
        return shape_arrays, shape_props, shape_text

    def _get_current_mod_item(self):
        mod_item = self.mod_list.currentItem()
        return (
            mod_item.mod_tag,
            mod_item.mod_path,
            mod_item.mod_spacing,
            mod_item.mod_type,
        )

    def _get_all_selected_mod_tags(self) -> List[Tuple[str, Any]]:
        mod_items = self.mod_list.selectedItems()
        mod_data = [(m.mod_tag, m.mod_type) for m in mod_items]
        return mod_data

    def _edit_data(self):
        mod_items = self.mod_list.selectedItems()
        if len(mod_items) == 1:
            mod_tag, mod_path, mod_spacing, mod_type = self._get_current_mod_item()
            if mod_type.name == "MERGE":
                return
            if mod_type.name == "IMAGE":
                preprocessing = self.reg_graph.modalities[mod_tag]["preprocessing"]
            if mod_type.name in ["SHAPE", "ATTACHMENT_IMAGE"]:
                attachment = True
            else:
                attachment = False
            all_entities = self._get_all_entity_tags()
            edited_mod = AddModality(
                file_path=mod_path,
                spacing=mod_spacing,
                tag=mod_tag,
                parent=self,
                mode="edit",
                attachment=attachment,
                attachment_tags=self.image_mods,
                preprocessing=preprocessing,
                all_entities=all_entities,
            )
            edited_mod.setWindowTitle("Edit image preprocessing information...")
            edited_mod.setWindowModality(Qt.ApplicationModal)
            edited_mod.exec_()

            if not attachment:
                preprocessing, channel_names = edited_mod.prepro_cntrl._export_data()
                self.reg_graph.modalities[mod_tag]["preprocessing"] = ImagePreproParams(
                    **preprocessing
                )
                self._update_preprocessing()

    def _switch_preprocessing_modality(self):
        mod_tag, _, _, mod_type = self._get_current_mod_item()

        if mod_type.name == "IMAGE":
            self.current_mod_in_prepro.setText(mod_tag)
            prepro_params = deepcopy(
                self.reg_graph.modalities[mod_tag]["preprocessing"]
            )
            channel_names = deepcopy(
                self.reg_graph.modalities[mod_tag]["channel_names"]
            )
            self.prepro_main_ctrl._import_data(prepro_params, channel_names)
            self._update_preprocessing()
        else:
            self.current_mod_in_prepro.setText("[no preprocessing data type]")

        self.path_ctrl.source_select.setCurrentText(mod_tag)
        self._rotate_modality()
        self._flip_modality()

    def _reset_reg_model(self):
        self.current_reg_models.setText("[None added]")
        self.reg_models_box.setCurrentText("rigid")

    def _add_reg_model_to_path(self):
        rm = self.reg_models_box.currentText()

        if rm == "[reset]":
            self.current_reg_models.setText("[None added]")
            return

        if rm == "from file":
            rm = "from_file"

        current_models = self.current_reg_models.text()
        if current_models == "[None added]":
            model_str = rm
            self.current_reg_models.setText(model_str)
            return

        current_models = current_models.split("►")
        current_models.append(rm)
        model_str = "►".join(current_models)

        self.current_reg_models.setText(model_str)

    def add_reg_path_to_graph(self):
        source_mod = self.path_ctrl.source_select.currentText()

        if self.path_ctrl.thru_select.currentText() in ["", "None"]:
            thru_mod = None
        else:
            thru_mod = self.path_ctrl.thru_select.currentText()

        target_mod = self.path_ctrl.target_select.currentText()

        if target_mod in ["None", ""]:
            emsg = QErrorMessage(self)
            emsg.showMessage("Target modality must be set")
            return

        if source_mod == target_mod:
            emsg = QErrorMessage(self)
            emsg.showMessage(
                f"Source modality ({source_mod}) and "
                f"target modality ({target_mod}) cannot be the same"
            )
            return

        if thru_mod == target_mod:
            emsg = QErrorMessage(self)
            emsg.showMessage(
                f"through modality ({thru_mod}) and "
                f"target modality ({target_mod}) cannot be the same"
            )
            return

        current_models = self.current_reg_models.text()
        reg_models = current_models.split("►")

        if len(reg_models) < 1:
            emsg = QErrorMessage(self)
            emsg.showMessage("Registration models must be added")
            return

        self.reg_graph.add_reg_path(
            source_mod, target_mod, thru_modality=thru_mod, reg_params=reg_models
        )
        self._update_reg_plot()

    def clear_all_reg_paths(self) -> None:
        # quick check for accidental press
        ok_to_clear = QMessageBox(self)
        continue_clear = ok_to_clear.question(
            self,
            "Clear all reg paths?",
            "Are you sure you want to clear all registration paths?",
        )
        if continue_clear != QMessageBox.Yes:
            return

        for modality in self.reg_graph.modality_names:
            self.reg_graph._remove_reg_paths(modality)

        self._update_reg_plot()

    def _clear_attachment_keys(self, attachment_key: str) -> None:
        for k, v in self.attachment_keys.items():
            if attachment_key in v:
                v.pop(v.index(attachment_key))

    def delete_modality(self, warn: bool = True):
        mod_data = self._get_all_selected_mod_tags()
        all_associated_mods = []

        for mod_tag, mod_type in mod_data:
            if mod_type.name not in ["MERGE", "MASK"]:
                self.reg_graph.remove_modality(mod_tag)
                self.current_mod_in_prepro.setText("[none selected]")
                self._update_preprocessing()

                if mod_type.name == "IMAGE":
                    self.image_mods.pop(self.image_mods.index(mod_tag))
                    current_items = [
                        self.path_ctrl.source_select.itemText(i)
                        for i in range(self.path_ctrl.source_select.count())
                    ]
                    rm_idx = current_items.index(mod_tag)
                    self.path_ctrl.source_select.removeItem(rm_idx)
                    self._update_path_possibilties()
                    associated_mods = deepcopy(self.attachment_keys[mod_tag])
                    all_associated_mods.extend(associated_mods)

                if mod_tag in self.shape_mods or mod_tag in self.attachment_mods:
                    if mod_type.name == "ATTACHMENT_IMAGE":
                        self.attachment_mods.pop(self.attachment_mods.index(mod_tag))
                        self._clear_attachment_keys(mod_tag)

                    if mod_type.name == "SHAPE":
                        try:
                            self.shape_mods.pop(self.shape_mods.index(mod_tag))
                        except ValueError:
                            pass
                        self._clear_attachment_keys(mod_tag)
                try:
                    self._pop_napari_layer_data(mod_tag)
                except (ValueError, KeyError):
                    pass

            elif mod_type.name == "MASK":
                if mod_tag in self.mask_mods.keys():
                    self._pop_napari_layer_data(mod_tag)
                    attachment_modality = self.mask_mods[mod_tag]
                    try:
                        self.reg_graph.modalities[attachment_modality]["mask"] = None
                    except KeyError:
                        pass

            elif mod_type.name == "MERGE":
                if mod_tag in self.merge_mods:
                    self.merge_mods.pop(mod_tag)
                    self.reg_graph.remove_merge_modality(mod_tag)

            to_rm = []
            for merge_name, merge_mods in self.merge_mods.items():
                if mod_tag in merge_mods:
                    to_rm.append(merge_name)
                    if warn:
                        msg = QMessageBox(self)
                        msg.setIcon(QMessageBox.Warning)
                        msg.setText("Merge modality removed")
                        msg.setInformativeText(
                            f"{mod_tag} was assoicated with a merge modality with tag {merge_name} and"
                            f" {merge_name} was removed from the merge modalities"
                        )
                        msg.setWindowTitle(
                            f"{merge_name} - removed with associated data {mod_tag}"
                        )
                        msg.setWindowModality(Qt.NonModal)
                        msg.exec_()
                    mod_tags = [
                        self.mod_list.item(ii).mod_tag
                        for ii in range(self.mod_list.count())
                    ]
                    merge_idx = mod_tags.index(merge_name)
                    self.mod_list.takeItem(merge_idx)

            [self.merge_mods.pop(rm) for rm in to_rm]

            for assoc_mod in all_associated_mods:
                if assoc_mod not in list(self.mask_mods.keys()):
                    self.reg_graph.remove_modality(assoc_mod)
                all_mod_tags = [
                    self.mod_list.item(ii).mod_tag
                    for ii in range(self.mod_list.count())
                ]
                try:
                    rm_idx = all_mod_tags.index(assoc_mod)
                except ValueError:
                    continue
                self.mod_list.takeItem(rm_idx)
                try:
                    self._pop_napari_layer_data(assoc_mod)
                except KeyError:
                    continue

                if assoc_mod in self.attachment_mods:
                    self.attachment_mods.pop(self.attachment_mods.index(assoc_mod))
                elif assoc_mod in self.mask_mods:
                    self.mask_mods.pop(assoc_mod)
                elif assoc_mod in self.shape_mods:
                    self.shape_mods.pop(self.shape_mods.index(assoc_mod))

            if len(all_associated_mods) > 0:
                if warn:
                    msg = QMessageBox(self)
                    msg.setIcon(QMessageBox.Warning)
                    msg.setText("Associated modality has been removed")
                    msg.setInformativeText(
                        f"<b>{mod_tag}</b> had assoicated data with tag(s) <b>{', '.join(all_associated_mods)}</b> and"
                        f" <b>{', '.join(all_associated_mods)}</b> was(were) removed\n"
                        f"<i>N.B.</i>: wsireg attachment modalities cannot be specified unattached"
                    )
                    msg.setWindowModality(Qt.NonModal)
                    msg.setWindowTitle(f"{mod_tag} - associated data removal warning")
                    msg.exec_()

            for item in self.mod_list.selectedItems():
                self.mod_list.takeItem(self.mod_list.indexFromItem(item).row())

            self._update_reg_plot()

    def _pop_napari_layer_data(self, mod_tag: str) -> None:
        ld = self.layer_data.pop(mod_tag)
        if isinstance(ld, list):
            for layer in ld:
                self.viewer.layers.pop(self.viewer.layers.index(layer.name))
        else:
            self.viewer.layers.pop(self.viewer.layers.index(ld.name))

    def set_project_output_dir(self, file_path: Optional[Union[str, Path]]) -> None:
        if not file_path:
            output_dir = QFileDialog.getExistingDirectory(
                self, "Select output directory"
            )
            if output_dir:
                self.output_dir_entry.setText(Path(output_dir).as_posix())
                self.output_dir_entry.setToolTip(Path(output_dir).as_posix())

    def _update_preprocessing(self):
        mod_tag = self.current_mod_in_prepro.text()
        if mod_tag not in ["[no preprocessing data type]", "[none selected]"]:
            preprocessing, channel_names = deepcopy(
                self.prepro_main_ctrl._export_data()
            )
            self.reg_graph.modalities[mod_tag]["preprocessing"] = ImagePreproParams(
                **preprocessing
            )
            self.reg_graph.modalities[mod_tag]["channel_names"] = channel_names

    def _find_poss_path_thru_target(
        self, current_mods: List[str], source_mod: str
    ) -> List[str]:
        targetable_modalities = deepcopy(current_mods)
        try:
            targetable_modalities.pop(current_mods.index(source_mod))
        except ValueError:
            pass

        return targetable_modalities

    def _find_poss_path_on_change(
        self, current_mods: List[str], source_mod: str, other_mod: str
    ) -> List[str]:
        targetable_modalities = deepcopy(current_mods)
        try:
            targetable_modalities.pop(current_mods.index(source_mod))
        except ValueError:
            pass
        try:
            targetable_modalities.pop(targetable_modalities.index(other_mod))
        except ValueError:
            pass

        return targetable_modalities

    def _update_path_possibilties(self):
        current_mods = deepcopy(self.image_mods)
        if len(self.image_mods) == 0:
            self.path_ctrl.source_select.clear()
            self.path_ctrl.thru_select.clear()
            self.path_ctrl.target_select.clear()

        if len(self.image_mods) > 1:
            self.path_ctrl.thru_select.clear()
            self.path_ctrl.target_select.clear()

            target_pos = self._find_poss_path_thru_target(
                current_mods, self.path_ctrl.source_select.currentText()
            )

            for tmod in target_pos:
                self.path_ctrl.target_select.addItem(tmod)

            if len(self.image_mods) > 2:
                self.path_ctrl.thru_select.addItem("None")
                for tmod in target_pos:
                    self.path_ctrl.thru_select.addItem(tmod)

    def _update_paths_on_through(self):
        current_mods = deepcopy(self.image_mods)

        current_target = self.path_ctrl.target_select.currentText()
        current_thru = self.path_ctrl.thru_select.currentText()

        self.path_ctrl.target_select.clear()

        if self.path_ctrl.thru_select.currentText() not in ["None", ""]:

            targetable_modalities = self._find_poss_path_on_change(
                current_mods,
                self.path_ctrl.source_select.currentText(),
                self.path_ctrl.thru_select.currentText(),
            )
        else:
            targetable_modalities = self._find_poss_path_thru_target(
                current_mods, self.path_ctrl.source_select.currentText()
            )

        for tmod in targetable_modalities:
            self.path_ctrl.target_select.addItem(tmod)

        if current_thru != current_target:
            self.path_ctrl.target_select.setCurrentText(current_target)

    def _update_paths_on_target(self):
        if len(self.image_mods) > 2:
            current_mods = deepcopy(self.image_mods)
            current_target = self.path_ctrl.target_select.currentText()
            current_thru = self.path_ctrl.thru_select.currentText()

            self.path_ctrl.thru_select.clear()

            targetable_modalities = self._find_poss_path_on_change(
                current_mods,
                self.path_ctrl.source_select.currentText(),
                self.path_ctrl.target_select.currentText(),
            )
            targetable_modalities = ["None"] + targetable_modalities

            for tmod in targetable_modalities:
                self.path_ctrl.thru_select.addItem(tmod)

            if current_thru != current_target:
                self.path_ctrl.thru_select.setCurrentText(current_thru)

    def eventFilter(self, source: QListWidget, event: QEvent) -> bool:
        if event.type() == QEvent.ContextMenu and source is self.mod_list:
            menu = QMenu()
            menu.addAction("Merge modalities in file after transformation")

            if menu.exec_(event.globalPos()):
                mod_data = self._get_all_selected_mod_tags()
                mod_tags = [m[0] for m in mod_data]
                mod_types = [m[1].name for m in mod_data]

                all_mergable = all(
                    tuple([mt in ["IMAGE", "ATTACHMENT_IMAGE"] for mt in mod_types])
                )

                if all_mergable:
                    merge_str = ", ".join(mod_tags)
                    add_merge = AddMerge(merge_str, parent=self)
                    add_merge.setWindowTitle("Enter modality merge information...")
                    add_merge.setWindowModality(Qt.ApplicationModal)
                    add_merge.exec_()
                    merge_tag = add_merge.merge_tag.text()
                    if add_merge.completed:
                        display_name = f"Merge -{merge_tag}" f'- {" : ".join(mod_tags)}'
                        mod_item = create_modality_item(
                            merge_tag, "", 1.0, "MERGE", display_name
                        )
                        self.mod_list.addItem(mod_item)
                        self.merge_mods.update({merge_tag: mod_tags})
                        self.reg_graph.add_merge_modalities(merge_tag, mod_tags)
                else:
                    emsg = QErrorMessage(self)
                    emsg.showMessage(
                        "One of the selected modalities is a shape set and not mergable"
                    )
            return True
        return super().eventFilter(source, event)

    def _get_layer_spatial_info(self, layer):
        is_mc = isinstance(layer, list)
        is_multiscale = layer[0].multiscale if is_mc else layer.multiscale

        if is_mc and is_multiscale:
            layer_shape = layer[0].data[0].shape
        elif is_mc and not is_multiscale:
            layer_shape = layer[0].data.shape
        elif not is_mc and is_multiscale:
            layer_shape = layer.data[0].shape
        elif not is_mc and not is_multiscale:
            layer_shape = layer.data.shape

        layer_spacing = layer[0].scale if is_mc else layer.scale

        if guess_rgb(layer_shape):
            layer_shape_yx = np.asarray(layer_shape)[:2]
        else:
            layer_shape_yx = np.asarray(layer_shape)[1:]

        return layer_shape_yx, layer_spacing

    def _transform_layerlist(
        self, layer_data: Union[List[Any], Any], transform: np.ndarray
    ):
        if isinstance(layer_data, list):
            for layer in layer_data:
                layer.affine = transform
        else:
            layer_data.affine = transform

    def _rotate_modality(self):
        current_mod = self.current_mod_in_prepro.text()

        if current_mod not in ["[no preprocessing data type]", "[none selected]"]:
            associated_mods = deepcopy(self.attachment_keys[current_mod])

            rot_angle = float(self.prepro_main_ctrl.rot_cc.text())
            flip = self.prepro_main_ctrl.flip.currentText()

            layer_shape_yx, layer_spacing = self._get_layer_spatial_info(
                self.layer_data[current_mod]
            )

            rot_transform = centered_transform(layer_shape_yx, layer_spacing, rot_angle)

            if flip == "None":
                transform = rot_transform
            else:
                flip_transform = centered_flip(layer_shape_yx, layer_spacing, flip)
                transform = flip_transform @ rot_transform

            self._transform_layerlist(self.layer_data[current_mod], transform)

            for mod in associated_mods:
                layer = self.layer_data[mod]
                self._transform_layerlist(layer, transform)

            self._update_preprocessing()

    def _flip_modality(self):
        current_mod = self.current_mod_in_prepro.text()

        if current_mod not in ["[no preprocessing data type]", "[none selected]"]:
            associated_mods = deepcopy(self.attachment_keys[current_mod])
            associated_mods.append(current_mod)

            direction = self.prepro_main_ctrl.flip.currentText()
            rot_angle = float(self.prepro_main_ctrl.rot_cc.text())

            layer_shape_yx, layer_spacing = self._get_layer_spatial_info(
                self.layer_data[current_mod]
            )

            if direction != "None":
                flip_transform = centered_flip(layer_shape_yx, layer_spacing, direction)
            else:
                flip_transform = np.eye(3)

            if rot_angle == 0:
                transform = flip_transform
            else:
                rot_transform = centered_transform(
                    layer_shape_yx, layer_spacing, rot_angle
                )
                transform = flip_transform @ rot_transform

            self._transform_layerlist(self.layer_data[current_mod], transform)

            for mod in associated_mods:
                layer = self.layer_data[mod]
                self._transform_layerlist(layer, transform)

            self._update_preprocessing()

    def _update_reg_plot(self):
        self.graph_view.plot(self.reg_graph)

    def _check_proj_info(self):
        if len(self.reg_graph.modalities.keys()) == 0:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Critical)
            msg.setText("Please add images to run registration graph")
            msg.setInformativeText(
                "Images must be added and paths between images defined to run"
                " the registration graph."
            )
            msg.setWindowTitle("Please add images")
            msg.setWindowModality(Qt.NonModal)
            msg.exec_()
            return False
        elif len(self.reg_graph.reg_paths.keys()) == 0:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Critical)
            msg.setText("Please define registration paths to run registration graph")
            msg.setInformativeText(
                "Without defined registration paths, there is no connection between images "
                "in the registration graph, and no images to register to one another."
            )
            msg.setWindowTitle("Please define registration paths")
            msg.setWindowModality(Qt.NonModal)
            msg.exec_()
            return False
        elif self.output_dir_entry.text() == "":
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Critical)
            msg.setText("Please set an output directory to run a registration graph")
            msg.setInformativeText(
                "An output directory must be set in order for preprocessing images"
                ", transformations, and transformed images and shapes to be"
                "saved to disk after registration completes"
            )
            msg.setWindowTitle("Please set output directory")
            msg.setWindowModality(Qt.NonModal)
            msg.exec_()
            return False
        elif self.project_name_entry.text() == "":
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Critical)
            msg.setText("Please set a project name to run registration graph")
            msg.setInformativeText(
                "The project name is the identified for the graph. "
                "If it is set to 'reg-proj', 'reg-proj' will prepend"
                "all output images and files"
            )
            msg.setWindowTitle("Please set project name")
            msg.setWindowModality(Qt.NonModal)
            msg.exec_()
            return False
        else:
            return True

    def _get_proj_opts(self):
        write_images = self.setup.proj_ctrl.write_images_check.isChecked()
        to_original_size = self.setup.proj_ctrl.orig_size_check.isChecked()
        transform_non_reg = self.setup.proj_ctrl.non_reg_image_check.isChecked()
        write_merge_and_indiv_check = (
            self.setup.proj_ctrl.write_merge_and_indiv_check.isChecked()
        )

        remove_merged = False if write_merge_and_indiv_check else True

        return {
            "write_images": write_images,
            "to_original_size": to_original_size,
            "transform_non_reg": transform_non_reg,
            "remove_merged": remove_merged,
        }

    def _add_registered_data_from_executed_graph(
        self, reg_graph_output: Tuple[List[str], WsiReg2D]
    ) -> None:
        output_data, reg_graph = reg_graph_output
        for output in output_data:
            name = Path(output).name
            if Path(output).suffix == ".geojson":
                for k, v in reg_graph._transformed_shapes_spacings.items():
                    if k in name:
                        shape_spacing = v
                shape_data = RegShapes(output)
                (
                    shape_arrays,
                    shape_props,
                    shape_text,
                ) = self._get_shape_data_from_reg_shapes(shape_data)

                self.viewer.add_shapes(
                    shape_arrays,
                    properties=shape_props,
                    text=shape_text,
                    shape_type="polygon",
                    name=name,
                    scale=shape_spacing,
                )
            else:
                image_data = TiffFileWsiRegImage(output)
                image_data.prepare_image_data()
                channel_names = [f"{name}-{c}" for c in image_data.channel_names]

                self.viewer.add_image(
                    image_data.dask_pyr,
                    channel_axis=None if image_data.is_rgb else image_data.channel_axis,
                    name=channel_names if not image_data.is_rgb else name,
                    scale=image_data.pixel_spacing,
                    rgb=image_data.is_rgb,
                )

    def _check_modalities_for_napari_layers(self) -> None:
        for shape_name, shape_data in self.reg_graph.shape_sets.items():
            if shape_data["shape_files"] == "in-memory layer":
                output_fp = str(
                    self.reg_graph.output_dir
                    / f"{self.reg_graph.project_name}-{shape_name}-from-napari-layer.geojson"
                )
                output_shapes_fp = napari_shapes_to_qp_geojson(
                    self.layer_data[shape_name], output_fp
                )
                shape_data["shape_files"] = output_shapes_fp

        for image_name, image_data in self.reg_graph.modalities.items():
            if (
                isinstance(image_data["image_filepath"], ARRAYLIKE_CLASSES)
                or image_data["image_filepath"] == "in-memory layer"
            ):
                output_fp = str(
                    self.reg_graph.output_dir
                    / f"{self.reg_graph.project_name}-{image_name}-from-napari-layer.tiff"
                )
                output_image_fp = write_image_from_napari(
                    self.layer_data[image_name].data, output_fp
                )
                image_data["image_filepath"] = output_image_fp
            if isinstance(image_data["mask"], str):
                if (
                    Path(image_data["mask"]).suffix.lower() == ".geojson"
                    and "-mask-tempdir.geojson" in image_data["mask"]
                ):
                    output_fp = str(
                        self.reg_graph.output_dir
                        / f"{self.reg_graph.project_name}-{image_name}-mask-from-napari-layer.geojson"
                    )
                    shutil.copy(image_data["mask"], output_fp)
                    image_data["mask"] = output_fp

    def run_registration_direct(self):
        if self._threadpool.activeThreadCount() > 0:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Critical)
            msg.setText("Graph added to queue")
            msg.setInformativeText(
                "In order to minimize total memory and compute consumption typical "
                "of WSI registration, "
                "only one graph at a time can be executed. "
                "This graph as been added to the queue."
            )
            msg.setWindowTitle("Only 1 registration graph can be executed at a time")
            msg.setWindowModality(Qt.NonModal)
            msg.exec_()
            self.add_current_graph_to_queue()
            return

        if self._check_proj_info():
            self.reg_graph.setup_project_output(
                self.project_name_entry.text(), output_dir=self.output_dir_entry.text()
            )
            self._check_modalities_for_napari_layers()
            cache_images = self.setup.proj_ctrl.cache_images_check.isChecked()
            self.reg_graph.cache_images = cache_images
            reg_opts = self._get_proj_opts()

            self._pbar = progress(total=0)
            self._pbar.set_description(
                f"Registering graph {self.reg_graph.project_name}"
            )
            graph_runner_worker = self._run_registration(
                deepcopy(self.reg_graph), reg_opts
            )
            graph_runner_worker.started.connect(lambda: self._clear_graph("run"))
            graph_runner_worker.returned.connect(
                self._add_registered_data_from_executed_graph
            )
            graph_runner_worker.finished.connect(
                lambda: self._pbar.set_description(
                    f"finished registered {self.reg_graph.project_name}"
                )
            )
            graph_runner_worker.finished.connect(self._pbar.close)
            self._threadpool.start(graph_runner_worker)

    @thread_worker
    def _run_registration(
        self, reg_graph: WsiReg2D, reg_opts: dict
    ) -> Tuple[List[str], WsiReg2D]:
        output_data = wsireg2d_main(reg_graph, **reg_opts)
        return output_data, reg_graph

    def _add_graph_item_to_queue(self, reg_graph: WsiReg2D, reg_opts: dict) -> None:
        queue_item = reg_queue_item(reg_graph, reg_opts)
        self.queue_list.addItem(queue_item)

    def _check_queue_for_identical_item(self, reg_graph: WsiReg2D) -> bool:
        queue_tags = [
            self.queue_list.item(r).queue_tag for r in range(self.queue_list.count())
        ]
        new_q_tag = generate_queue_tag(reg_graph)
        if new_q_tag in queue_tags:
            emsg = QErrorMessage(self)
            emsg.showMessage("The modality added to queue is identical to another.")
            return False
        else:
            return True

    def delete_queue_items(self):
        queue_items = self.queue_list.selectedItems()
        for item in queue_items:
            self.queue_list.takeItem(self.queue_list.row(item))

    def add_current_graph_to_queue(self):
        if self._check_proj_info():
            self.reg_graph.setup_project_output(
                self.project_name_entry.text(), output_dir=self.output_dir_entry.text()
            )
            self._check_modalities_for_napari_layers()
            cache_images = self.setup.proj_ctrl.cache_images_check.isChecked()
            self.reg_graph.cache_images = cache_images
            reg_opts = self._get_proj_opts()
            if self._check_queue_for_identical_item(self.reg_graph):
                self._add_graph_item_to_queue(
                    deepcopy(self.reg_graph), deepcopy(reg_opts)
                )
                self._clear_graph("queue")

    def _set_running_queue_label(self, running_data):
        self.progress_label.setText(running_data)

    def _update_n_graphs_registered(self):
        self._n_graphs_registered += 1

    def _check_close_pbar(self):
        if self._n_graphs_registered == self._pbar.total:
            self._pbar.close()

    def _send_graph_to_execution(self, queue_item):
        graph_runner_worker = self._run_registration(
            queue_item.reg_graph, queue_item.reg_options
        )
        graph_runner_worker.started.connect(
            lambda: self._set_running_queue_label(queue_item.reg_graph.project_name)
        )
        graph_runner_worker.started.connect(
            lambda: self._pbar.set_description(
                f"Registering graph {queue_item.reg_graph.project_name}"
            )
        )
        graph_runner_worker.returned.connect(
            self._add_registered_data_from_executed_graph
        )

        graph_runner_worker.finished.connect(queue_item._set_finished)
        graph_runner_worker.finished.connect(
            lambda: self._pbar.set_description(
                f"finished registered {queue_item.reg_graph.project_name}"
            )
        )
        graph_runner_worker.finished.connect(lambda: self._pbar.update(1))
        graph_runner_worker.finished.connect(self._update_n_graphs_registered)
        graph_runner_worker.finished.connect(self._check_close_pbar)
        self._threadpool.start(graph_runner_worker)

    def run_registration_queue(self):
        if self._threadpool.activeThreadCount() > 0:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Critical)
            msg.setText("A previous queue is in execution")
            msg.setInformativeText(
                "Please wait for the previous queue to finish before starting a execution."
            )
            msg.setWindowTitle("Queue already running")
            msg.setWindowModality(Qt.NonModal)
            msg.exec_()
            return
        if self.queue_list.count() > 0:

            to_send = []
            for item_idx in range(self.queue_list.count()):
                queue_item = self.queue_list.item(item_idx)
                if not queue_item.finished:
                    to_send.append(queue_item)
            self._pbar = progress(total=len(to_send))
            for queue_item in to_send:
                self._send_graph_to_execution(queue_item)
            self._n_graphs_registered = 0
        else:
            emsg = QErrorMessage(self)
            emsg.showMessage("There are no items in the queue to run.")

    def save_graph_config(self):
        if self._check_proj_info():
            project_name = self.project_name_entry.text()
            output_dir = self.output_dir_entry.text()

            output_file_name_suggestion = str(
                Path(output_dir) / f"{project_name}-wsireg-config.yaml"
            )

            self.reg_graph.setup_project_output(project_name, output_dir=output_dir)
            cache_images = self.setup.proj_ctrl.cache_images_check.isChecked()
            self.reg_graph.cache_images = cache_images
            # reg_opts = self._get_proj_opts()

            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Save wsireg graph config",
                output_file_name_suggestion,
                "YAML config (*.yaml)",
            )

            if filename:
                self.reg_graph.save_config(output_file_path=filename, registered=False)

    def _clear_graph(self, event: str = "clear"):
        # quick check for accidental press
        if event == "clear":
            ok_to_clear = QMessageBox(self)
            continue_clear = ok_to_clear.question(
                self,
                "Clear graph?",
                "Are you sure you want to clear the registration graph?",
            )
            if continue_clear != QMessageBox.Yes:
                return

        self.mod_list.selectAll()
        self.delete_modality(warn=False)

        self.reg_graph: WsiReg2D = WsiReg2D(None, None)
        self.graph_queue: List[Tuple[WsiReg2D, Dict[str, bool]]] = []

        self.image_mods: List[str] = []
        self.attachment_mods: List[str] = []
        self.shape_mods: List[str] = []
        self.merge_mods: Dict[str, List[str]] = dict()
        self.mask_mods: Dict[str, str] = dict()

        self.image_data: Dict[str, WsiRegImage] = dict()
        self.layer_data: Dict[str, Any] = dict()
        self.image_spacings: Dict[str, float] = dict()
        self.attachment_keys: Dict[str, List[str]] = dict()
        self.project_name_entry.setText("")

    def closeEvent(self, _) -> None:
        self._temp_dir.cleanup()


@napari_hook_implementation
def napari_experimental_provide_dock_widget():
    # you can return either a single widget, or a sequence of widgets
    return [WsiReg2DMain]
