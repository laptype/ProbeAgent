import pickle
import ast
import astor
import os
import re
import json
import sys
from os.path import join as pjoin
from string import Template


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
                 is_save_test_code = False,
                 template_path = 'template.py'
                 ):

        self.save_graph_png_path = save_graph_png_path
        create_dir_if_not_exists(save_graph_png_path)
        self.save_graph_path = save_graph_path
        # TODO: pycallgraph2 不支持py36以下的版本
        self.output_graph_path = str(pjoin(self.save_graph_path, 'callGraph.pkl'))
        self.output_graph_all_path = str(pjoin(self.save_graph_path, 'CallGraphAll.pkl'))
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

        with open(template_path, 'r', encoding='utf-8') as template_file:
            template_code = template_file.read()

        self.template = Template(template_code)

        self.decorator_name = 'debug_function_scope'
        self.decorator_arg = str(pjoin(self.save_graph_path, 'variable.jsonl'))

    #     ['matplotlib.*', 'sklearn.*', 'astropy.*', 'django.*', 'flask.*', 'xarray.*', 'pylint.*', 'pytest.*', '_pytest.*', 'sphinx.*', 'sympy.*']

    def method_filter(self, name: str) -> bool:
        for method in self.method_filter_list:
            if method == name:
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

    def unparse(self, node):
        return astor.to_source(node)

    def _process_func(self, node):
        # 添加装饰器，带有参数
        decorator = ast.Call(
            func=ast.Name(id=self.decorator_name, ctx=ast.Load()),
            args=[ast.Constant(value=self.decorator_arg)],
            keywords=[]
        )
        node.decorator_list.insert(0, decorator)

        output_path_single = str(pjoin(self.save_graph_png_path, f'{node.name}.pkl'))

        global_code = self.template.substitute(
            pycallgraph_name=self.pycallgraph_name,
            output_graph_path_single=output_path_single,
            output_graph_path=self.output_graph_path,
            output_graph_all_path=self.output_graph_all_path,
            output_traceback_path=self.output_traceback_path,
            output_test_path=self.output_test_path,
            node_name=node.name,
            max_depth=self.max_depth,
            include_list=self.include_list
        )
        template_tree = ast.parse(global_code)
        # Find the try statement in the template
        for stmt in ast.walk(template_tree):
            if isinstance(stmt, ast.Try):
                if len(stmt.body) == 1 and isinstance(stmt.body[0], ast.Pass):
                    stmt.body = node.body
        node.body = template_tree.body
        return ast.NodeTransformer.generic_visit(self, node)

    def _save_test_code(self, node):
        if self.test_code is not None:
            self.test_code[node.name] = unparse(node)

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
                            is_save_test_code=False,
                            template_path='template.py'):
    if outfile_path is None:
        outfile_path = file_path
    with open(file_path, "r", encoding='utf-8') as source_file:
        source_code = source_file.read()

    # 将 import 语句添加到源代码的开头
    source_code = 'from .debug_function import debug_function_scope\n' + source_code

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
                                       is_save_test_code=is_save_test_code,
                                       template_path=template_path)
    new_tree = transformer.visit(tree)

    # 重新格式化 AST 为源代码
    new_code = astor.to_source(new_tree)

    with open(outfile_path, "w", encoding='utf-8') as source_file:
        source_file.write(new_code)

    return transformer

if __name__ == '__main__':
    # 调用函数，输入你的文件路径
    # add_pycallgraph_to_file('test_artist.py')
    """
        python core/context/call_graph/AddPyCallGraphFail.py
    """
    file_path = '../tmp_test.py'
    outfile_path = 'tmp_test_2.py'
    method_filter_list = ['test_bad_db_index_value']
    add_pycallgraph_to_file(file_path,
                            save_graph_path='opt',
                            save_graph_png_path='opt',
                            max_depth=25,
                            outfile_path=outfile_path,
                            task_id='astropy__astropy-14995',
                            method_filter_list=method_filter_list,
                            pycallgraph_name='pycallgraph2')

