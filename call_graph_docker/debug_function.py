import sys
import json
import os

map_include_list = [
    'astropy',
    'matplotlib',
    'mpl_toolkits',
    'seaborn',
    'flask',
    'requests',
    'xarray',
    'pylint',
    'pytest',
    '_pytest',
    'sklearn',
    'sphinx',
    'sympy',
    'django',
    'xml'
]


def check_module(module_name):
    for include in map_include_list:
        if include in module_name:
            return True
    return False

class FunctionTracer:
    def __init__(self, json_file, target_module=None, test_func_name='test_kernel_ridge'):
        self.json_file = json_file
        self.full_func_path = None
        self.target_module = target_module
        self.test_func_name = test_func_name
        self.frames = []
        self.in_with_block = False
        self.records = {}

    def __enter__(self):
        self.in_with_block = True
        sys.settrace(self.trace_function_calls)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.in_with_block = False
        for frame in self.frames:
            self.save_with_scope_vars(frame.f_locals)
        sys.settrace(None)
        self.write_json_file()

    def save_with_scope_vars(self, local_vars):
        if self.test_func_name not in self.records:
            self.records[self.test_func_name] = {}

        for var_name, var_value in local_vars.items():
            var_type = str(type(var_value))
            try:
                if var_name.startswith('callGraph_'):
                    continue
                if 'FunctionTracer' in var_type:
                    continue
                value_str = str(var_value)[:100]
            except Exception as e:
                value_str = f"Unserializable value: {e}"

            self.records[self.test_func_name][var_name] = {
                "type": var_type,
                "value": value_str
            }

    def save_local_vars(self, local_vars):
        if self.target_module and not check_module(self.full_func_path):
            return

        if self.full_func_path not in self.records:
            self.records[self.full_func_path] = {}

        for var_name, var_value in local_vars.items():
            try:
                value_str = str(var_value)[:100]
            except Exception as e:
                value_str = f"Unserializable value: {e}"
            self.records[self.full_func_path][var_name] = {
                "type": str(type(var_value)),
                "value": value_str
            }

    def write_json_file(self):
        with open(self.json_file, "w", encoding='utf-8') as file:
            json.dump(self.records, file, indent=4)

    def trace_function_calls(self, frame, event, arg):
        if event == 'call':
            code = frame.f_code
            func_name = code.co_name
            class_name = None

            if 'self' in frame.f_locals:
                class_name = frame.f_locals['self'].__class__.__name__

            file_path = code.co_filename
            module_path = os.path.relpath(file_path, start=os.getcwd()).replace(os.sep, ".")
            file_name = os.path.splitext(module_path)[0]

            self.full_func_path = f"{file_name}.{class_name}.{func_name}" if class_name else f"{file_name}.{func_name}"
            self.frames.append(frame)

            # Save local vars if in the with block
            if self.in_with_block and frame.f_back.f_code.co_name == self.test_func_name:
                self.save_with_scope_vars(frame.f_back.f_locals)

        elif event in ['return', 'exception']:
            if frame in self.frames:
                self.frames.remove(frame)
                self.save_local_vars(frame.f_locals)

        return self.trace_function_calls