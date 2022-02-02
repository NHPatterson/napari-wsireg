from qtpy.QtWidgets import QVBoxLayout, QWidget, QPushButton, QFormLayout, QComboBox
import networkx as nx
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib
from matplotlib.patches import ArrowStyle
from wsireg.wsireg2d import WsiReg2D

COLOR_MAP = [
    "#a6cee3",
    "#1f78b4",
    "#33a02c",
    "#b2df8a",
    "#fb9a99",
    "#fdbf6f",
    "#e31a1c",
    "#ff7f00",
    "#cab2d6",
    "#6a3d9a",
    "#ffff99",
    "#b15928",
]

matplotlib.use("Qt5Agg")


# Adapted from https://github.com/BiAPoL/napari-clusters-plotter/blob/main/napari_clusters_plotter/_plotter.py # noqa: E501
# then Adapted from https://github.com/haesleinhuepf/napari-workflow-inspector/blob/main/src/napari_workflow_inspector/_dock_widget.py # noqa: E501
class MplCanvas(FigureCanvas):
    def __init__(self, parent=None, width=3, height=2.25):
        self.fig = Figure(figsize=(width, height))
        # changing color of axis background to napari main window color
        self.fig.patch.set_facecolor("#262930")
        self.fig.tight_layout(pad=0)
        self.axes = self.fig.add_subplot(111)

        super(MplCanvas, self).__init__(self.fig)


class RegGraphViewer(QWidget):
    def __init__(self, parent=None):
        super().__init__()

        main_layout = QVBoxLayout()
        self.refresh_graph = QPushButton("Refresh graph layout")
        main_layout.setSpacing(5)

        self.graph_plot = MplCanvas()
        self.graph_plot.axes.clear()
        self.graph_plot.axes.axis("off")
        self.graph_plot.axes.use_sticky_edges = True
        self.graph_plot.axes.set_title(None)
        self.graph_plot.axes.set_xlabel(None)
        self.graph_plot.axes.set_ylabel(None)
        # self.graph_plot.axes.margins()

        self.setLayout(main_layout)
        form = QFormLayout()
        self.layout_box = QComboBox()
        self.layout_box.addItem("Shell layout")
        self.layout_box.addItem("Spring layout")
        self.layout_box.addItem("Random layout")
        self.layout_box.addItem("Planar layout")
        self.layout_box.addItem("KK layout")
        self.layout_box.addItem("Circular layout")
        self.layout_box.addItem("Spectral layout")
        self.layout_box.addItem("Spiral layout")

        form.addRow(self.layout_box, self.refresh_graph)

        self.layout().addWidget(self.graph_plot)
        self.layout().addLayout(form)

    def plot(self, plot_data: WsiReg2D):
        self.graph_plot.axes.clear()
        self.graph_plot.axes.axis("off")
        self.graph_plot.axes.use_sticky_edges = True
        self.graph_plot.axes.set_title(None)
        self.graph_plot.axes.set_xlabel(None)
        self.graph_plot.axes.set_ylabel(None)
        self.graph_plot.axes.margins(x=0.2, y=0.2)
        self.graph_plot.fig.tight_layout()
        g = nx.DiGraph()
        g_layout = nx.DiGraph()

        for idx, modality in enumerate(plot_data.modality_names):
            rad = (idx + 1) * 0.08 + 0.05
            if idx > 11:
                color = COLOR_MAP[idx - 11]
            else:
                color = COLOR_MAP[idx]

            g.add_node(modality, color=color, cstyle=f"arc3,rad=-{rad}")
            g_layout.add_node(modality, color=color, cstyle=f"arc3,rad=-{rad}")

        for attachment_name, attachment_mod in plot_data.attachment_images.items():
            g.add_node(attachment_name, color="green")
            g_layout.add_edge(attachment_name, attachment_mod)

        for shape_set_name, shape_info in plot_data.shape_sets.items():
            g.add_node(shape_set_name, color="red")
            g_layout.add_edge(shape_set_name, shape_info["attachment_modality"])

        for src, tgts in plot_data.reg_paths.items():
            g.add_edge(src, tgts[0])
            g_layout.add_edge(src, tgts[0])
            for idx, cont_src in enumerate(tgts[:-1]):
                current, target = cont_src, tgts[idx + 1]
                g_layout.add_edge(current, target)

        if self.layout_box.currentText() == "Random layout":
            pos = nx.random_layout(g_layout)
        elif self.layout_box.currentText() == "KK layout":
            pos = nx.kamada_kawai_layout(g_layout)
        elif self.layout_box.currentText() == "Planar layout":
            pos = nx.planar_layout(g_layout)
        elif self.layout_box.currentText() == "Spring layout":
            pos = nx.spring_layout(g_layout)
        elif self.layout_box.currentText() == "Spectral layout":
            pos = nx.spectral_layout(g_layout)
        elif self.layout_box.currentText() == "Shell layout":
            pos = nx.shell_layout(g_layout)
        elif self.layout_box.currentText() == "Circular layout":
            pos = nx.circular_layout(g_layout)
        elif self.layout_box.currentText() == "Spiral layout":
            pos = nx.spiral_layout(g_layout)

        # pos = {p: v * 20 for p, v in pos.items()}
        nx.draw_networkx_nodes(
            g,
            pos,
            label=g.nodes,
            node_color=[g.nodes[n]["color"] for n in g.nodes],
            node_size=100,
            alpha=0.75,
            ax=self.graph_plot.axes,
        )

        for attachment_name, attachment_mod in plot_data.attachment_images.items():
            self.graph_plot.axes.annotate(
                "",
                xy=pos[attachment_name],
                xycoords="data",
                xytext=pos[attachment_mod],
                textcoords="data",
                arrowprops=dict(
                    arrowstyle=ArrowStyle.BracketA(widthA=0.5),
                    color="white",
                    shrinkA=5,
                    shrinkB=5,
                    patchA=None,
                    patchB=None,
                    mutation_scale=10,
                    linewidth=1.5,
                ),
            )

        for shape_set_name, shape_info in plot_data.shape_sets.items():
            self.graph_plot.axes.annotate(
                "",
                xy=pos[shape_set_name],
                xycoords="data",
                xytext=pos[shape_info["attachment_modality"]],
                textcoords="data",
                arrowprops=dict(
                    arrowstyle=ArrowStyle.BracketA(widthA=0.5),
                    color="white",
                    shrinkA=5,
                    shrinkB=5,
                    patchA=None,
                    patchB=None,
                    mutation_scale=10,
                    linewidth=1.5,
                ),
            )

        for src, tgts in plot_data.reg_paths.items():

            src_color = g.nodes[src]["color"]
            cstyle = g.nodes[src]["cstyle"]

            self.graph_plot.axes.annotate(
                "",
                xy=pos[src],
                xycoords="data",
                xytext=pos[tgts[0]],
                textcoords="data",
                arrowprops=dict(
                    arrowstyle="<-",
                    color=src_color,
                    shrinkA=5,
                    shrinkB=5,
                    patchA=None,
                    patchB=None,
                    mutation_scale=10,
                    connectionstyle=cstyle,
                    linewidth=1.5,
                ),
            )
            path_targets = nx.algorithms.shortest_path(g, src, tgts[-1])[1:]

            if len(path_targets) > 1:
                for idx, cont_src in enumerate(path_targets[:-1]):
                    current, target = cont_src, path_targets[idx + 1]
                    print(current, target)
                    self.graph_plot.axes.annotate(
                        "",
                        xy=pos[current],
                        xycoords="data",
                        xytext=pos[target],
                        textcoords="data",
                        arrowprops=dict(
                            arrowstyle="<-",
                            color=src_color,
                            shrinkA=5,
                            shrinkB=5,
                            patchA=None,
                            patchB=None,
                            mutation_aspect=2,
                            connectionstyle=cstyle,
                            linewidth=1,
                            linestyle="dotted",
                        ),
                    )

        def nudge(pos, x_shift, y_shift):
            return {n: (x + x_shift, y + y_shift) for n, (x, y) in pos.items()}

        if len(pos.keys()) > 2:
            pos_labels = nudge(pos, 0, -0.075)
        else:
            pos_labels = pos

        nx.draw_networkx_labels(
            g,
            pos_labels,
            ax=self.graph_plot.axes,
            font_color="white",
            font_size=9.5,
        )

        self.graph_plot.draw()
