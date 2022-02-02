import networkx as nx

COLOR_MAP = [
    "#a6cee3",
    "#1f78b4",
    "#b2df8a",
    "#33a02c",
    "#fb9a99",
    "#e31a1c",
    "#fdbf6f",
    "#ff7f00",
    "#cab2d6",
    "#6a3d9a",
    "#ffff99",
    "#b15928",
]


def create_graph_plot(reg_graph, ax):
    g = nx.DiGraph()

    for idx, modality in enumerate(reg_graph.modality_names):
        idx + 0.05
        if idx > 11:
            color = COLOR_MAP[idx - 11]
        else:
            color = COLOR_MAP[idx]

        g.add_node(modality, color=color, cstyle=f"arc3,rad=-{(idx+1)*0.08+0.05}")

    for src, tgts in reg_graph.reg_paths.items():
        g.add_edge(src, tgts[0])

    pos = nx.kamada_kawai_layout(g)
    pos = {p: v * 20 for p, v in pos.items()}
    nx.draw_networkx_nodes(
        g,
        pos,
        label=g.nodes,
        node_color=[g.nodes[n]["color"] for n in g.nodes],
        node_size=100,
        alpha=1,
    )

    for src, tgts in reg_graph.reg_paths.items():

        src_color = g.nodes[src]["color"]
        cstyle = g.nodes[src]["cstyle"]

        ax.annotate(
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
                ax.annotate(
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
                    ),
                )
    nx.draw_networkx_labels(g, pos)

    return
