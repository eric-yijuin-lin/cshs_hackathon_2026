import json
import math
from pathlib import Path
import networkx as nx

class RoadTracer:
    def __init__(self):
        self.source_json = {}
        self.dir_table = {}
        self.graph = nx.Graph()

        self.load_source()
        self.init_weighted_graph()

    def load_source(self) -> None:
        module_dir = Path(__file__).resolve().parent
        source_file = module_dir / "sample_graph.json"
        with open(source_file, 'r', encoding="UTF-8") as f:
            self.source_json = json.load(f)

        # 網站下載的座標系，以圖中心為原點，向右 x 是正、向下 y 是正
        # 因此在這邊做 y 值的轉換
        for node in self.source_json["nodes"]:
            node["y"] = node["y"] * -1

    def init_weighted_graph(self) -> None:
        nodes = self.source_json["nodes"]
        edges = self.source_json["edges"]

        for n in nodes:
            self.graph.add_node(
                n["label"],
                pos = (int(n["x"]), int(n["y"])),
            )

        for e in edges:
            n1 = self.get_node_label(e["source"])
            n2 = self.get_node_label(e["target"])
            w = int(e["label"]) # 目前用 edge 的 label 代表權重
            self.graph.add_edge(n1, n2, weight = w)

    def get_node_label(self, node_id: str) -> str:
        node = next(
            (n for n in self.source_json["nodes"] 
            if n["id"] == node_id),
            None)
        if not node:
            raise ValueError(f"找不到 id = {node_id} 的節點")
        return node["label"]

    def get_trace_data(self, start: str, end: str) -> dict:
        path = nx.dijkstra_path(self.graph, source=start, target=end)

        trace_data = []
        for i in range(len(path) - 1):
            label_1 = path[i]
            label_2 = path[i + 1]
            weight = self.graph.get_edge_data(label_1, label_2)["weight"]
            direction = self.get_direction_degree(label_1, label_2)
            trace_data.append({
                "start": label_1,
                "end": label_2,
                "weight": weight,
                "direction": round(direction, 2)
            })

        return trace_data

    def get_direction_degree(self, label_1: str, label_2: str) -> float:
        node_1 = self.graph.nodes[label_1]
        node_2 = self.graph.nodes[label_2]
        x1, y1 = node_1["pos"][0], node_1["pos"][1]
        x2, y2 = node_2["pos"][0], node_2["pos"][1]
        dx = x2 - x1
        dy = y2 - y1
        degree = math.degrees(math.atan2(dy, dx))
        return degree

    def show_graph_info(self) -> None:
        nodes = list(self.graph.nodes(data=True))
        edges = list(self.graph.edges(data=True))
        print("節點資訊：")
        for node in sorted(nodes):
            print(node)
        print("邊線資訊：")
        for edge in sorted(edges):
            print(edge)

    def show_path_cost(self, start: str, end: str) -> None:
        shortest_path = nx.dijkstra_path(self.graph, source=start, target=end)
        distance = nx.dijkstra_path_length(self.graph, source=start, target=end)
        print(f"最短路徑: {shortest_path}")
        print(f"{start} 到 {end} 路徑成本 = {distance}")
