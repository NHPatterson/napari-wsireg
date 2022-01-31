from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import napari
import numpy as np
from napari.qt.threading import thread_worker
from napari.utils import progress
from napari_plugin_engine import napari_hook_implementation
from qtpy.QtCore import QEvent, Qt
from qtpy.QtWidgets import (
    QErrorMessage,
    QFileDialog,
    QHBoxLayout,
    QListWidget,
    QMenu,
    QWidget,
)
from wsireg.parameter_maps.preprocessing import ImagePreproParams
from wsireg.parameter_maps.reg_model import RegModel
from wsireg.reg_shapes import RegShapes
from wsireg.wsireg2d import WsiReg2D

from napari_wsireg.data import (
    FILE_ERROR_MESSAGE,
    TIFFFILE_EXTS,
    CziWsiRegImage,
    TiffFileWsiRegImage,
    WsiRegImage,
)
from napari_wsireg.data.utils.image import guess_rgb
from napari_wsireg.data.utils.transform import centered_flip, centered_transform
from napari_wsireg.gui.dialogs.add_merge import AddMerge
from napari_wsireg.gui.dialogs.add_modality import AddModality
from napari_wsireg.gui.setup_gui import SetupTab
from napari_wsireg.gui.setup_sub.modality import create_modality_item
from napari_wsireg.gui.utils.colors import ATTACHMENTS_COL, IMAGES_COL, SHAPES_COL
from napari_wsireg.gui.utils.file import open_file_dialog


class WsiReg2DMain(QWidget):
    def __init__(self, napari_viewer: napari.Viewer):
        super().__init__()

        self.viewer = napari_viewer

        self.reg_graph = WsiReg2D(None, None)

        self.image_mods: List[str] = []
        self.attachment_mods: List[str] = []
        self.shape_mods: List[str] = []

        self.image_data: Dict[str, WsiRegImage] = dict()
        self.layer_data: Dict[str, Any] = dict()
        self.image_spacings: Dict[str, float] = dict()
        self.image_to_attach: Dict[str, List[str]] = dict()

        main_layout = QHBoxLayout()
        self.setLayout(main_layout)
        self.setup = SetupTab()

        self.add_mod_btn = self.setup.mod_ctrl.add_mod_btn
        self.add_ach_btn = self.setup.mod_ctrl.add_ach_btn
        self.add_shp_btn = self.setup.mod_ctrl.add_shp_btn
        self.del_mod_btn = self.setup.mod_ctrl.del_mod_btn
        self.edit_mod_btn = self.setup.mod_ctrl.edt_mod_btn

        self.mod_list = self.setup.mod_ctrl.mod_list
        self.mod_list.installEventFilter(self)

        self.current_mod_in_prepro = self.setup.prepro_ctrl.mod_in_prepro
        self.prepro_main_ctrl = self.setup.prepro_ctrl

        self.path_ctrl = self.setup.path_ctrl
        self.reg_models_box = self.setup.path_ctrl.reg_models
        self.add_reg_model = self.setup.path_ctrl.add_reg_model
        self.current_reg_models = self.setup.path_ctrl.current_reg_models

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

        self.layout().addWidget(self.setup)
        self.layout().setAlignment(self.setup, Qt.AlignTop)
        main_layout.addStretch(True)

        self.add_mod_btn.clicked.connect(lambda: self.add_data("image"))
        self.add_ach_btn.clicked.connect(lambda: self.add_data("attachment"))
        self.add_shp_btn.clicked.connect(lambda: self.add_data("shape"))

        self.del_mod_btn.clicked.connect(self.delete_modality)

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

        # project management connections
        self.output_dir_select.clicked.connect(self.set_project_output_dir)

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
            file_paths = open_file_dialog(
                self,
                single=False,
                wd="",
                name="Open image(s) for registration",
                file_types="All Files (*);;Tiff files (*.tiff,*.tif)",
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
                else:
                    self._add_shape_data(file_path, no_dialog)

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

    def _add_image_data(self, file_path: Union[str, Path], no_dialog: bool = False):
        image_data = self._get_image_data(file_path)

        if image_data:
            added_mod = AddModality(file_path, parent=self, image_data=image_data)
            if not no_dialog:
                added_mod.setWindowTitle("Enter registration image information...")
                added_mod.setWindowModality(Qt.ApplicationModal)
                added_mod.exec_()
            else:
                rstr = self._generate_random_name()
                added_mod.tag.setText(rstr)
                added_mod.completed = True

            text_color = IMAGES_COL

            if added_mod.completed:
                mod_tag = str(added_mod.tag.text())
                mod_spacing = float(added_mod.spacing.text())
                mod_path = Path(file_path).name
                list_name = f"{mod_tag} : {mod_path} : {mod_spacing} (μm)"
                mod_item = create_modality_item(list_name, text_color)
                self.mod_list.addItem(mod_item)
                preprocessing = added_mod.prepro_cntrl._export_data()
                self.reg_graph.add_modality(
                    mod_tag, file_path, mod_spacing, preprocessing=preprocessing
                )
                self.image_mods.append(mod_tag)
                self.image_to_attach.update({mod_tag: []})

                self.path_ctrl.source_select.addItem(mod_tag)
                self.image_data.update({mod_tag: image_data})
                self.image_spacings.update({mod_tag: mod_spacing})

                self._run_add_image(mod_tag, image_data, use_thumbnail=False)

                self._update_path_possibilties()

    def _run_add_image(
        self,
        mod_tag: str,
        image_data: Union[TiffFileWsiRegImage, CziWsiRegImage],
        use_thumbnail: bool = False,
    ):
        pbr = progress(total=0)
        pbr.set_description(f"reading {mod_tag} image")

        micro_reader_worker = self._prepare_image_data(
            mod_tag, image_data, use_thumbnail=use_thumbnail
        )
        micro_reader_worker.start()
        micro_reader_worker.returned.connect(self._add_image_to_viewer)
        micro_reader_worker.finished.connect(
            lambda: pbr.set_description(f"finished reading {mod_tag} image")
        )
        micro_reader_worker.finished.connect(pbr.close)

    @thread_worker
    def _prepare_image_data(
        self,
        mod_tag: str,
        image_data: Union[TiffFileWsiRegImage, CziWsiRegImage],
        use_thumbnail: bool = False,
    ):
        image_data.prepare_image_data()
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
        self, file_path: Union[str, Path], no_dialog: bool = False
    ):
        image_data = self._get_image_data(file_path)

        if image_data:
            try:
                added_mod = AddModality(
                    file_path,
                    parent=self,
                    attachment=True,
                    attachment_tags=self.image_mods,
                    image_spacings=self.image_spacings,
                )
                if not no_dialog:
                    added_mod.setWindowTitle("Enter attachment image information...")
                    added_mod.setWindowModality(Qt.ApplicationModal)
                    added_mod.exec_()
                else:
                    rstr = self._generate_random_name()
                    added_mod.tag.setText(rstr)
                    added_mod.completed = True

                text_color = ATTACHMENTS_COL

            except UnboundLocalError:
                return

        if added_mod.completed:
            mod_tag = str(added_mod.tag.text())
            mod_spacing = float(added_mod.spacing.text())
            mod_path = Path(file_path).name
            list_name = f"{mod_tag} : {mod_path} : {mod_spacing} (μm)"
            mod_item = create_modality_item(list_name, text_color)
            self.mod_list.addItem(mod_item)
            attachment_modality = added_mod.attachment_combo.currentText()
            self.reg_graph.add_attachment_images(
                attachment_modality, mod_tag, file_path, mod_spacing
            )
            self.image_data.update({mod_tag: image_data})
            self.image_spacings.update({mod_tag: mod_spacing})
            self._run_add_image(mod_tag, image_data, use_thumbnail=True)
            self.attachment_mods.append(mod_tag)
            self.image_to_attach[attachment_modality].append(mod_tag)

    def _add_shape_data(self, file_path: Union[str, Path], no_dialog: bool = False):

        shape_data = RegShapes(file_path)

        added_mod = AddModality(
            file_path,
            parent=self,
            attachment=True,
            attachment_tags=self.image_mods,
            image_spacings=self.image_spacings,
        )
        if not no_dialog:
            added_mod.setWindowTitle("Enter attachment shape information...")
            added_mod.setWindowModality(Qt.ApplicationModal)
            added_mod.exec_()
        else:
            rstr = self._generate_random_name()
            added_mod.tag.setText(rstr)
            added_mod.completed = True

        text_color = SHAPES_COL

        if added_mod.completed:
            mod_tag = str(added_mod.tag.text())
            mod_spacing = float(added_mod.spacing.text())
            mod_path = Path(file_path).name
            list_name = f"{mod_tag} : {mod_path} : {mod_spacing} (μm)"
            mod_item = create_modality_item(list_name, text_color)
            self.mod_list.addItem(mod_item)
            attachment_modality = added_mod.attachment_combo.currentText()
            self.reg_graph.add_attachment_shapes(
                attachment_modality, mod_tag, file_path
            )
            self.shape_mods.append(mod_tag)
            self.image_to_attach[attachment_modality].append(mod_tag)
            self._add_shapes_to_viewer(mod_tag, shape_data, mod_spacing)

    def _add_shapes_to_viewer(
        self, mod_tag: str, shape_data: RegShapes, mod_spacing: float
    ):
        shape_arrays = [s["array"][:, [1, 0]] for s in shape_data.shape_data]

        shape_props = {"name": shape_data.shape_names}

        shape_text = {
            "text": "{name}",
            "color": "white",
            "anchor": "center",
            "size": 12,
        }

        self.layer_data.update(
            {
                mod_tag: self.viewer.add_shapes(
                    shape_arrays,
                    scale=(mod_spacing, mod_spacing),
                    properties=shape_props,
                    text=shape_text,
                    shape_type="polygon",
                )
            }
        )

    def _get_current_mod_item(self):
        mod_item = self.mod_list.currentItem()
        mod_text = mod_item.text()
        mod_tag, mod_path, mod_spacing = mod_text.split(" : ")
        return mod_tag, mod_path, mod_spacing

    def _get_all_selected_mod_tags(self):
        mod_items = self.mod_list.selectedItems()
        mod_texts = [item.text() for item in mod_items]
        return [m.split(" : ")[0] for m in mod_texts]

    def _edit_data(self):
        if self.mod_list.currentItem().text()[:7] == "Merge -":
            return

        mod_tag, mod_path, mod_spacing = self._get_current_mod_item()

        if mod_tag in self.image_mods:
            preprocessing = self.reg_graph.modalities[mod_tag]["preprocessing"]

        if mod_tag in self.attachment_mods or mod_tag in self.shape_mods:
            attachment = True
        else:
            attachment = False

        edited_mod = AddModality(
            file_path=mod_path,
            spacing=float(mod_spacing.split(" (")[0]),
            tag=mod_tag,
            parent=self,
            mode="edit",
            attachment=attachment,
            attachment_tags=self.image_mods,
            preprocessing=preprocessing,
        )
        edited_mod.setWindowTitle("Edit image preprocessing information...")
        edited_mod.setWindowModality(Qt.ApplicationModal)
        edited_mod.exec_()

        if not attachment:
            preprocessing = edited_mod.prepro_cntrl._export_data()
            self.reg_graph.modalities[mod_tag]["preprocessing"] = ImagePreproParams(
                **preprocessing
            )
            self._update_preprocessing()

    def _switch_preprocessing_modality(self):
        mod_tag, _, _ = self._get_current_mod_item()

        if mod_tag in self.image_mods:
            self.current_mod_in_prepro.setText(mod_tag)
            prepro_params = deepcopy(
                self.reg_graph.modalities[mod_tag]["preprocessing"]
            )
            self.prepro_main_ctrl._import_data(prepro_params)
            self._update_preprocessing()
        else:
            self.current_mod_in_prepro.setText("[no preprocessing data type]")

        self.path_ctrl.source_select.setCurrentText(mod_tag)

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
            emsg.showMessage(f"Target modality must be set")
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
            emsg.showMessage(f"Registration models must be added")
            return

        self.reg_graph.add_reg_path(
            source_mod, target_mod, thru_modality=thru_mod, reg_params=reg_models
        )

    def delete_modality(self):
        mod_tag, _, _ = self._get_current_mod_item()

        self.mod_list.takeItem(self.mod_list.currentRow())

        if mod_tag in self.image_mods:
            self.reg_graph.modalities[mod_tag] = None
            self.image_mods.pop(self.image_mods.index(mod_tag))
            current_items = [
                self.path_ctrl.source_select.itemText(i)
                for i in range(self.path_ctrl.source_select.count())
            ]
            rm_idx = current_items.index(mod_tag)
            self.path_ctrl.source_select.removeItem(rm_idx)
            self._update_path_possibilties()
            self.reg_graph.modality_names.pop(
                self.reg_graph.modality_names.index(mod_tag)
            )
            self.reg_graph.n_modalities -= 1

        if mod_tag in self.attachment_mods:
            self.reg_graph.modalities[mod_tag] = None
            self.reg_graph.attachment_images[mod_tag] = None
            self.attachment_mods.pop(self.attachment_mods.index(mod_tag))
            self.reg_graph.modality_names.pop(
                self.reg_graph.modality_names.index(mod_tag)
            )
            self.reg_graph.n_modalities -= 1

        if mod_tag in self.shape_mods:
            self.reg_graph.shape_sets[mod_tag] = None
            self.shape_mods.pop(self.shape_mods.index(mod_tag))
            self.reg_graph.shape_set_names.pop(
                self.reg_graph.shape_set_names.index(mod_tag)
            )

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
            preprocessing = deepcopy(self.prepro_main_ctrl._export_data())
            self.reg_graph.modalities[mod_tag]["preprocessing"] = ImagePreproParams(
                **preprocessing
            )

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
                mod_tags = self._get_all_selected_mod_tags()
                all_mergable_mods = deepcopy(self.image_mods) + deepcopy(
                    self.attachment_mods
                )
                all_mergable = all(item in all_mergable_mods for item in mod_tags)
                if all_mergable:
                    merge_str = ", ".join(mod_tags)
                    add_merge = AddMerge(merge_str, parent=self)
                    add_merge.setWindowTitle("Enter modality merge information...")
                    add_merge.setWindowModality(Qt.ApplicationModal)
                    add_merge.exec_()
                    if add_merge.completed:
                        merge_tag = f'Merge - {add_merge.merge_tag.text()} - {" : ".join(mod_tags)}'
                        self.mod_list.addItem(merge_tag)
                else:
                    emsg = QErrorMessage(self)
                    emsg.showMessage(
                        "One of the selected modalities is a shape set and not mergable"
                    )
            return True
        return super().eventFilter(source, event)

    def _rotate_modality(self):
        current_mod = self.current_mod_in_prepro.text()
        if current_mod not in ["[no preprocessing data type]", "[none selected]"]:
            associated_mods = self.image_to_attach[current_mod]

            rot_angle = float(self.prepro_main_ctrl.rot_cc.text())
            flip = self.prepro_main_ctrl.flip.currentText()

            layer = self.layer_data[current_mod]
            if isinstance(layer.data, list):
                layer_shape = layer.data[0].shape
            else:
                layer_shape = layer.data.shape

            layer_spacing = layer.scale

            if guess_rgb(layer_shape):
                layer_shape = np.asarray(layer_shape)[:2]
            else:
                layer_shape = np.asarray(layer_shape)[1:]

            rot_transform = centered_transform(layer_shape, layer_spacing, rot_angle)

            if flip == "None":
                transform = rot_transform
            else:
                flip_transform = centered_flip(layer_shape, layer_spacing, flip)
                transform = flip_transform @ rot_transform

            layer.affine = transform

            for mod in associated_mods:
                layer = self.layer_data[mod]
                layer.affine = transform

            self._update_preprocessing()

    def _flip_modality(self):
        current_mod = self.current_mod_in_prepro.text()
        if current_mod not in ["[no preprocessing data type]", "[none selected]"]:
            associated_mods = self.image_to_attach[current_mod]
            associated_mods.append(current_mod)

            direction = self.prepro_main_ctrl.flip.currentText()
            rot_angle = float(self.prepro_main_ctrl.rot_cc.text())

            layer = self.layer_data[current_mod]
            if isinstance(layer.data, list):
                layer_shape = layer.data[0].shape

            else:
                layer_shape = layer.data.shape

            layer_spacing = layer.scale

            if guess_rgb(layer_shape):
                layer_shape = np.asarray(layer_shape)[:2]
            else:
                layer_shape = np.asarray(layer_shape)[1:]

            if direction != "None":
                flip_transform = centered_flip(layer_shape, layer_spacing, direction)
            else:
                flip_transform = np.eye(3)

            if rot_angle == 0:
                transform = flip_transform
            else:
                rot_transform = centered_transform(
                    layer_shape, layer_spacing, rot_angle
                )
                transform = flip_transform @ rot_transform

            layer.affine = transform

            self._update_preprocessing()

            for mod in associated_mods:
                layer = self.layer_data[mod]
                layer.affine = transform


@napari_hook_implementation
def napari_experimental_provide_dock_widget():
    # you can return either a single widget, or a sequence of widgets
    return [WsiReg2DMain]
