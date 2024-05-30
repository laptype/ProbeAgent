import pickle
import ast
import astor
import os
import re
import json
import sys
from os.path import join as pjoin

map_include_list = {
    'astropy':      ['astropy.*'],
    'matplotlib':   ['matplotlib.*', 'mpl_toolkits.*'],
    'mwaskom':      ['seaborn.*'],
    'pallets':      ['flask.*'],
    'psf':          ['requests.*'],
    'pydata':       ['xarray.*'],
    'pylint-dev':   ['pylint.*'],
    'pytest-dev':   ['pytest.*', '_pytest.*'],
    'scikit-learn': ['sklearn.*'],
    'sphinx-doc':   ['sphinx.*'],
    'sympy':    ['sympy.*'],
    'django':   ['django.*', 'xml.*']
}

python_version = sys.version_info
if python_version >= (3, 9):
    # Use ast.unparse for Python 3.9+
    def unparse(node):
        return ast.unparse(node)
else:
    def unparse(node):
        return astor.to_source(node)


def get_method_filter(test_cmd, fail_to_pass_list: list, task_id: str = ""):

    if "django" in task_id:
        return [m.split(' ')[0] for m in fail_to_pass_list]

    if test_cmd.startswith("pytest") or test_cmd.startswith('tox'):
        # astropy__astropy-12907 [输入参数]
        pattern = re.compile(r'\[.*?\]')
        method_list = []
        for m in fail_to_pass_list:
            method = m.split('::')[-1]
            method = re.sub(pattern, '', method)
            method_list.append(method)
        return method_list

    elif 'bin/test' in test_cmd:
        return fail_to_pass_list
    else:
        raise RuntimeError("get_method_filter: error")

def create_dir_if_not_exists(dir_path: str):
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)

def get_include_list(task_id: str):
    return map_include_list[task_id.split('__')[0]]

def get_first_three_items(input_dict):
    first_three_keys = list(input_dict.keys())[:3]
    return {key: input_dict[key] for key in first_three_keys}

class AddPyCallGraphToFunc(ast.NodeTransformer):
    def __init__(self,
                 save_graph_path='/opt',
                 save_graph_png_path='/opt',
                 max_depth=5,
                 include_list = ['sklearn.*'],
                 pycallgraph_name = 'pycallgraph2',
                 method_filter_list = [],
                 is_save_test_code = False
                 ):
        self.save_graph_png_path = save_graph_png_path
        create_dir_if_not_exists(save_graph_png_path)
        self.save_graph_path = save_graph_path
        # TODO: pycallgraph2 不支持py36以下的版本
        self.output_graph_path = str(pjoin(self.save_graph_path, 'callGraph.pkl'))
        self.output_test_path = str(pjoin(self.save_graph_path, 'fail_test.txt'))
        self.output_traceback_path = str(pjoin(self.save_graph_path, 'traceback.json'))
        self.max_depth=max_depth
        self.include_list = include_list
        self.pycallgraph_name = pycallgraph_name
        if not os.path.exists(self.output_test_path):
            with open(self.output_test_path, 'w') as f:
                f.write('')
        if not os.path.exists(self.output_traceback_path):
            with open(self.output_traceback_path, 'w', encoding='utf-8') as file:
                json.dump({}, file, indent=4)
        self.method_filter_list = method_filter_list
        self.test_code = {} if is_save_test_code else None

    #     ['matplotlib.*', 'sklearn.*', 'astropy.*', 'django.*', 'flask.*', 'xarray.*', 'pylint.*', 'pytest.*', '_pytest.*', 'sphinx.*', 'sympy.*']

    def method_filter(self, name: str) -> bool:
        for method in self.method_filter_list:
            if method in name:
                return True
        return False

    def visit_FunctionDef(self, node):
        if self.method_filter(node.name):
            self._save_test_code(node)
            return self._process_func(node)
        else:
            # 普通的 return 处理
            return ast.NodeTransformer.generic_visit(self, node)

    def visit_AsyncFunctionDef(self, node):
        if self.method_filter(node.name):
            self._save_test_code(node)
            return self._process_func(node)
        else:
            # 普通的 return 处理
            return ast.NodeTransformer.generic_visit(self, node)

    def _save_test_code(self, node):
        if self.test_code is not None:
            self.test_code[node.name] = unparse(node)

    def _process_func(self, node):
        output_path = str(pjoin(self.save_graph_png_path, f'{node.name}.png'))
        # output_path = '/dev/null'
        output_graph_path = str(pjoin(self.save_graph_png_path, f'{node.name}.pkl'))
        global_code = f"""
import os
import json
import pickle
import traceback
import networkx as nx
from {self.pycallgraph_name} import PyCallGraph
from {self.pycallgraph_name}.output import Output
from {self.pycallgraph_name}.config import Config
from {self.pycallgraph_name}.globbing_filter import GlobbingFilter

class CustomGraphOutput(Output):
    def __init__(self, output_file):
        self.output_file = output_file
        self.graph = nx.DiGraph()

    def done(self):
        processor = self.processor
        for edge in processor.edges():
            self.graph.add_edge(edge.src_func, edge.dst_func)
        with open(self.output_file, 'wb') as f:
            pickle.dump(self.graph, f)

# 设置pycallgraph的配置
config = Config(max_depth={self.max_depth})
#config.trace_filter = GlobbingFilter(include={str(self.include_list)})
config.include_stdlib = True
config.verbose = True
# 创建我们的自定义输出对象
# graphviz = GraphvizOutput(output_file='{output_path}')
graphviz = CustomGraphOutput('{output_graph_path}')
is_pass = 'Pass'
"""
        line1 = ast.parse(global_code).body
        line2 = ast.parse("with PyCallGraph(output=graphviz, config=config): pass").body[0]
        # line2 = ast.parse(f"if True: pass").body[0]
        graph_code = ast.parse(
            f"""
# merge graph ---------------------------------------
if not os.path.exists('{self.output_graph_path}'):
    graph = nx.DiGraph()
else:
    with open('{self.output_graph_path}', 'rb') as f:
        graph = pickle.load(f)
processor = graphviz.processor
for edge in processor.edges():
    graph.add_edge(edge.src_func, edge.dst_func)
# 获取 traceback ------------------------------------
tb = traceback.extract_tb(e.__traceback__)
# 提取所有函数名字
function_names_dict = []
for frame in tb:
    tmp_dict = {{}}
    tmp_dict['name'] = frame.name
    tmp_dict['filename'] = frame.filename
    tmp_dict['line'] = frame.line
    tmp_dict['lineno'] = frame.lineno
    tmp_dict['locals'] = frame.locals
    function_names_dict.append(str(tmp_dict))
function_names = [frame.name for frame in tb]
# 读取已有的JSON文件
with open('{self.output_traceback_path}', 'r', encoding='utf-8') as file:
    data = json.load(file)
data['{node.name}'] = function_names_dict
# 将更新后的数据写回到JSON文件
with open('{self.output_traceback_path}', 'w', encoding='utf-8') as file:
    json.dump(data, file, indent=4)
# 设置节点属性：是否是中断函数 --------------------------
for node in graph.nodes:
    for func_name in function_names:
        if func_name in node:
            graph.nodes[node]['is_interrupted'] = True
        else:
            graph.nodes[node]['is_interrupted'] = False
with open('{self.output_graph_path}', 'wb') as f:
    pickle.dump(graph, f)
is_pass = 'Fail to Pass'
raise
            """
        ).body

        # 创建 try-except-finally 结构
        try_body = node.body if node.body and not isinstance(node.body[0], ast.Pass) else [ast.Pass()]
        # except_code = [ast.Pass()]
        except_code = graph_code
        finally_code = [ast.Pass()]
        try_except = ast.Try(
            body=try_body,  # 原始函数体作为try的内容
            handlers=[ast.ExceptHandler(type=ast.Name(id='Exception', ctx=ast.Load()), name="e", body=except_code)],
            orelse=[],
            finalbody=[]  # 这里留空，稍后添加finally
        )

        # 将 finally 代码添加到 try-except 结构中
        finally_code = (
            f"""
with open('{self.output_test_path}', 'a') as f:
    f.write(f'[{{is_pass}}]: {node.name}\\n')
            """
        )
        finally_code = ast.parse(finally_code).body
        try_except.finalbody = finally_code
        # 将 try-except 结构封装进 with 语句中
        line2.body = [try_except]
        node.body = line1+[line2]
        # 普通的 return 处理
        return ast.NodeTransformer.generic_visit(self, node)

    def save_graph_png(self):
        import matplotlib.pyplot as plt
        output_path = str(pjoin(self.save_graph_png_path, f'call_graph.png'))

        with open(self.output_graph_path, 'rb') as f:
            graph = pickle.load(f)

        node_colors = [
            'red' if graph.nodes[node].get('is_interrupted', False) else 'blue'
            for node in graph.nodes()
        ]
        pos = nx.spring_layout(graph)
        plt.figure(figsize=(10, 10))
        nx.draw(graph, pos, node_color=node_colors, with_labels=True, node_size=500, font_size=10, font_color='black')
        plt.savefig(output_path)
        plt.close()

    def save_test_code_in_json(self, task_id, task_map_path):
        with open(task_map_path, 'r', encoding='utf-8') as file:
            task_map = json.load(file)
        # 更新或创建'test_code'键
        if 'test_code' in task_map:
            task_map[task_id]['test_code'].update(self.test_code)
        else:
            task_map[task_id]['test_code'] = self.test_code
        task_map[task_id]['test_code'] = get_first_three_items(task_map[task_id]['test_code'])

        with open(task_map_path, 'w', encoding='utf-8') as file:
            json.dump(task_map, file, indent=4, ensure_ascii=False)

def add_pycallgraph_to_file(file_path,
                            outfile_path=None,
                            save_graph_path='/opt',
                            save_graph_png_path='/opt',
                            max_depth=5,
                            task_id='matplotlib__matplotlib-26020',
                            method_filter_list=[],
                            pycallgraph_name='pycallgraph2',
                            is_save_test_code=False):
    if outfile_path is None:
        outfile_path = file_path
    with open(file_path, "r") as source_file:
        source_code = source_file.read()

    # 解析源代码为 AST
    tree = ast.parse(source_code)

    include_list = get_include_list(task_id)
    print(include_list)

    # 使用我们的 AddLinesToFunc 类处理 AST
    transformer = AddPyCallGraphToFunc(save_graph_path=save_graph_path,
                                       save_graph_png_path=save_graph_png_path,
                                       max_depth=max_depth,
                                       include_list=include_list,
                                       pycallgraph_name=pycallgraph_name,
                                       method_filter_list=method_filter_list,
                                       is_save_test_code=is_save_test_code)
    new_tree = transformer.visit(tree)

    # 重新格式化 AST 为源代码
    new_code = astor.to_source(new_tree)

    with open(outfile_path, "w") as source_file:
        source_file.write(new_code)

    return transformer


# class CallGraph():
#     def __init__(self, graph: nx.DiGraph):
#         self.graph = graph
#
#     @staticmethod
#     def load_graph(file_path):
#         # file_path = os.path.join(file_path, 'call_graph.pkl')
#         with open(file_path, 'rb') as f:
#             graph = pickle.load(f)
#         return CallGraph(graph)
#
#     def print_edges(self):
#         # Print all edges in the graph
#         for src, dst in self.graph.edges():
#             print(f"{src} -> {dst}")
#
#     def get_subgraph(self, node_name, radius=1):
#         # Extract the subgraph around a given node within a specified radius
#         if node_name in self.graph:
#             subgraph = nx.ego_graph(
#                 self.graph, node_name, radius=radius, undirected=True
#             )
#             return subgraph
#         else:
#             print(f"No node named {node_name} found in the graph.")
#             return None

if __name__ == '__main__':
    # 调用函数，输入你的文件路径
    # add_pycallgraph_to_file('test_artist.py')
    """
        python core/context/call_graph/AddPyCallGraphFail.py
    """
    file_path = 'test_code/test_ndarithmetic.py'
    outfile_path = 'test_code/test_ndarithmetic_new.py'
    method_filter_list = get_method_filter('pytest --no-header -rA --tb=no -p no:cacheprovider astropy/nddata/mixins/tests/test_ndarithmetic.py',
                                           ["astropy/nddata/mixins/tests/test_ndarithmetic.py::test_nddata_bitmask_arithmetic"],
                                           'astropy__astropy-14995')
    add_pycallgraph_to_file(file_path,
                            outfile_path=outfile_path,
                            task_id='astropy__astropy-14995',
                            method_filter_list=method_filter_list,
                            pycallgraph_name='pycallgraph2')
    # cg = CallGraph.load_graph('graph.pkl')
    # cg.print_edges()
    # cg.visualize(cg.graph)
    # subgraph = cg.get_subgraph(
    #     "matplotlib.artist.AxesImage.format_cursor_data", radius=2
    # )
    # cg.visualize(subgraph)
