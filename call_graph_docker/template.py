import os as callGraph_os
import json as callGraph_json
import pickle as callGraph_pickle
import traceback as callGraph_traceback
import networkx as callGraph_nx
from ${pycallgraph_name} import PyCallGraph as callGraph_PyCallGraph
from ${pycallgraph_name}.output import Output as callGraph_Output
from ${pycallgraph_name}.config import Config as callGraph_Config

callGraph_output_graph_path_single = r"${output_graph_path_single}"
callGraph_output_graph_path = r"${output_graph_path}"
callGraph_output_graph_all_path = r"${output_graph_all_path}"
callGraph_output_traceback_path = r"${output_traceback_path}"
callGraph_output_test_path = r"${output_test_path}"
callGraph_output_tracer_path = r"${output_tracer_path}"
callGraph_node_name = r"${node_name}"
callGraph_max_depth = ${max_depth}

class callGraph_CustomGraphOutput(callGraph_Output):
    def __init__(self, output_file):
        self.output_file = output_file
        self.graph = callGraph_nx.DiGraph()

    def done(self):
        processor = self.processor
        for edge in processor.edges():
            self.graph.add_edge(edge.src_func, edge.dst_func)
        if not callGraph_os.path.exists(self.output_file):
            with open(self.output_file, 'wb') as f:
                callGraph_pickle.dump(self.graph, f)

callGraph_config = callGraph_Config(max_depth=callGraph_max_depth)
callGraph_config.include_stdlib = True
callGraph_config.verbose = True

callGraph_graphviz = callGraph_CustomGraphOutput(callGraph_output_graph_path_single)
callGraph_is_pass = 'Pass'
with callGraph_PyCallGraph(output=callGraph_graphviz, config=callGraph_config), FunctionTracer(callGraph_output_tracer_path, test_func_name=callGraph_node_name):
    try:
        pass
    except Exception as callGraph_e:
        # merge graph ---------------------------------------
        if not callGraph_os.path.exists(callGraph_output_graph_path):
            callGraph_graph = callGraph_nx.DiGraph()
        else:
            with open(callGraph_output_graph_path, 'rb') as callGraph_f:
                callGraph_graph = callGraph_pickle.load(callGraph_f)
        callGraph_processor = callGraph_graphviz.processor
        for callGraph_edge in callGraph_processor.edges():
            callGraph_graph.add_edge(callGraph_edge.src_func, callGraph_edge.dst_func)
        # traceback ------------------------------------
        callGraph_tb = callGraph_traceback.extract_tb(callGraph_e.__traceback__)
        callGraph_function_names_dict = []
        for callGraph_frame in callGraph_tb:
            callGraph_tmp_dict = {
                'name': callGraph_frame.name,
                'filename': callGraph_frame.filename,
                'line': callGraph_frame.line,
                'lineno': callGraph_frame.lineno,
                'locals': callGraph_frame.locals
            }
            callGraph_function_names_dict.append(str(callGraph_tmp_dict))
        callGraph_function_names = [callGraph_frame.name for callGraph_frame in callGraph_tb]

        with open(callGraph_output_traceback_path, 'r', encoding='utf-8') as callGraph_file:
            callGraph_data = callGraph_json.load(callGraph_file)
        callGraph_data[callGraph_node_name] = callGraph_function_names_dict

        with open(callGraph_output_traceback_path, 'w', encoding='utf-8') as callGraph_file:
            callGraph_json.dump(callGraph_data, callGraph_file, indent=4)

        for callGraph_node in callGraph_graph.nodes:
            for callGraph_func_name in callGraph_function_names:
                if callGraph_func_name in callGraph_node:
                    callGraph_graph.nodes[callGraph_node]['is_interrupted'] = True
                else:
                    callGraph_graph.nodes[callGraph_node]['is_interrupted'] = False
        with open(callGraph_output_graph_path, 'wb') as callGraph_f:
            callGraph_pickle.dump(callGraph_graph, callGraph_f)
        callGraph_is_pass = 'Fail to Pass'
        raise

    finally:
        # merge graph ---------------------------------------
        if not callGraph_os.path.exists(callGraph_output_graph_all_path):
            callGraph_allGraph = callGraph_nx.DiGraph()
        else:
            with open(callGraph_output_graph_all_path, 'rb') as callGraph_f:
                callGraph_allGraph = callGraph_pickle.load(callGraph_f)
        callGraph_processor = callGraph_graphviz.processor

        for callGraph_edge in callGraph_processor.edges():
            callGraph_allGraph.add_edge(callGraph_edge.src_func, callGraph_edge.dst_func)

        with open(callGraph_output_graph_all_path, 'wb') as callGraph_f:
            callGraph_pickle.dump(callGraph_allGraph, callGraph_f)

        with open(callGraph_output_test_path, 'a') as callGraph_f:
            callGraph_f.write(f'[{callGraph_is_pass}]: {callGraph_node_name}\\n')
