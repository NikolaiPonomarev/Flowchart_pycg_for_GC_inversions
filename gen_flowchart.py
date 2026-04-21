import sys
sys.modules["pycg"] = __import__("PyCG")
from PyCG.pycg import CallGraphGenerator
import glob
from PyCG import utils
import networkx as nx
import matplotlib.pyplot as plt
import os
from collections import defaultdict

output_file = "graph.png"
root_dir = "/scratch/local/enkf_oco2_inv_af"
files = glob.glob(root_dir + "/*.py", recursive=True)

cg = CallGraphGenerator(
        entry_points=files,
        package="enkf_oco2_inv_af",
        max_iter=3,
        operation=None
    )

valid_files = []
invalid_files = []

for f in files:
    try:
        compile(open(f, "r").read(), f, "exec")
        valid_files.append(f)
    except SyntaxError as e:
        invalid_files.append((f, str(e)))

print("invalid files:", len(invalid_files))


cg = CallGraphGenerator(
    entry_points=valid_files,
    package="enkf_oco2_inv_af",
    max_iter=3,
    operation=utils.constants.CALL_GRAPH_OP
)

cg.analyze()
# graph = cg.output()

edges = cg.output_edges()
valid_files_set = {
    os.path.splitext(os.path.basename(f))[0]
    for f in valid_files
}

def get_file(node):
    if "<builtin>" in node:
        return None

    clean = node.split("enkf_oco2_inv_af.")[-1]
    return clean.split(".")[0]

file_edges = set()

for caller, callee in edges:
    f1 = get_file(caller)
    f2 = get_file(callee)

    # keep only real project files
    if not f1 or not f2:
        continue

    if f1 not in valid_files_set or f2 not in valid_files_set:
        continue

    if f1 != f2:
        file_edges.add((f1, f2))


# --- build reverse graph distance from entry --
G = nx.DiGraph()
G.add_edges_from(file_edges)


ENTRY = "run_job_oco2"

def compute_levels(G, root):
    levels = {root: 0}
    queue = [root]

    while queue:
        node = queue.pop(0)
        for nbr in G.successors(node):
            if nbr not in levels:
                levels[nbr] = levels[node] + 1
                queue.append(nbr)

    return levels


levels = compute_levels(G, ENTRY)

def layered_layout(levels):
    layers = defaultdict(list)

    for node, lvl in levels.items():
        layers[lvl].append(node)

    pos = {}

    for lvl in sorted(layers.keys()):
        nodes = layers[lvl]

        # spread nodes evenly in x-axis
        n = len(nodes)

        for i, node in enumerate(sorted(nodes)):
            x = i - (n - 1) / 2   # center the layer
            y = -lvl              # top-down flow
            pos[node] = (x, y)

    return pos


pos = layered_layout(levels)

G_plot = G.subgraph(pos.keys()).copy()
plt.figure(figsize=(12, 8))
ax = plt.gca()
ax.set_facecolor("white")

node_sizes = []
for n in G_plot.nodes():
    base = 1800
    scale = len(n) * 55
    node_sizes.append(base + scale)

# --- nodes ---
nx.draw_networkx_nodes(
    G_plot,
    pos,
    node_size=node_sizes,
    node_color="#E8F1FF",
    edgecolors="#2B4C7E",
    linewidths=1.3,
    alpha=0.95
)

# --- edges ---
nx.draw_networkx_edges(
    G_plot,
    pos,
    arrows=True,
    arrowstyle='-|>',
    arrowsize=14,
    width=1.0,
    edge_color="#666666",
    alpha=0.45,
    connectionstyle="arc3,rad=0.10"
)

# --- labels ---
nx.draw_networkx_labels(
    G_plot,
    pos,
    font_size=7,
    font_family="sans-serif",
    font_color="#1A1A1A"
)

plt.title("Inversion pipeline chart", fontsize=11, fontweight="bold")
plt.axis("off")
plt.tight_layout()
plt.savefig(output_file, dpi=300, bbox_inches="tight")
print(f"Call graph saved to {output_file}")