import os
import json
import pickle
import traceback
import networkx as nx
from ${pycallgraph_name} import PyCallGraph
from ${pycallgraph_name}.output import Output
from ${pycallgraph_name}.config import Config

output_graph_path_single = r"${output_graph_path_single}"
output_graph_path = r"${output_graph_path}"
output_graph_all_path = r"${output_graph_all_path}"
output_traceback_path = r"${output_traceback_path}"
output_test_path = r"${output_test_path}"
node_name = r"${node_name}"
max_depth = ${max_depth}

class CustomGraphOutput(Output):
    def __init__(self, output_file):
        self.output_file = output_file
        self.graph = nx.DiGraph()

    def done(self):
        processor = self.processor
        for edge in processor.edges():
            self.graph.add_edge(edge.src_func, edge.dst_func)
        if not os.path.exists(self.output_file):
            with open(self.output_file, 'wb') as f:
                pickle.dump(self.graph, f)

config = Config(max_depth=max_depth)
config.include_stdlib = True
config.verbose = True

graphviz = CustomGraphOutput(output_graph_path_single)
is_pass = 'Pass'
with PyCallGraph(output=graphviz, config=config):
    try:
        pass
    except Exception as e:
        # merge graph ---------------------------------------
        if not os.path.exists(output_graph_path):
            graph = nx.DiGraph()
        else:
            with open(output_graph_path, 'rb') as f:
                graph = pickle.load(f)
        processor = graphviz.processor
        for edge in processor.edges():
            graph.add_edge(edge.src_func, edge.dst_func)
        # traceback ------------------------------------
        tb = traceback.extract_tb(e.__traceback__)
        function_names_dict = []
        for frame in tb:
            tmp_dict = {
                'name': frame.name,
                'filename': frame.filename,
                'line': frame.line,
                'lineno': frame.lineno,
                'locals': frame.locals
            }
            function_names_dict.append(str(tmp_dict))
        function_names = [frame.name for frame in tb]

        with open(output_traceback_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        data[node_name] = function_names_dict

        with open(output_traceback_path, 'w', encoding='utf-8') as file:
            json.dump(data, file, indent=4)

        for node in graph.nodes:
            for func_name in function_names:
                if func_name in node:
                    graph.nodes[node]['is_interrupted'] = True
                else:
                    graph.nodes[node]['is_interrupted'] = False
        with open(output_graph_path, 'wb') as f:
            pickle.dump(graph, f)
        is_pass = 'Fail to Pass'
        raise

    finally:
        # merge graph ---------------------------------------
        if not os.path.exists(output_graph_all_path):
            allGraph = nx.DiGraph()
        else:
            with open(output_graph_all_path, 'rb') as f:
                allGraph = pickle.load(f)
        processor = graphviz.processor

        for edge in processor.edges():
            allGraph.add_edge(edge.src_func, edge.dst_func)

        with open(output_graph_all_path, 'wb') as f:
            pickle.dump(allGraph, f)

        with open(output_test_path, 'a') as f:
            f.write(f'[{is_pass}]: {node_name}\\n')
