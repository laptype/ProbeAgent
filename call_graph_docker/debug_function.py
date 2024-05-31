import sys
import json
import os

def save_local_vars(local_vars, full_func_path, input_args, return_value, jsonl_file):
    record = {
        "args": {k: str(type(v)) for k, v in input_args.items()},
        "locals": {}
    }

    for var_name, var_value in local_vars.items():
        try:
            value_str = str(var_value)[:100]
        except Exception as e:
            value_str = f"Unserializable value: {e}"
        record["locals"][var_name] = {
            "type": str(type(var_value)),
            "value": value_str
        }

    record["return"] = {
        "type": str(type(return_value)),
        "value": str(return_value)[:100]
    }

    with open(jsonl_file, "a", encoding='utf-8') as file:
        json_record = {full_func_path: record}
        file.write(json.dumps(json_record) + "\n")


def trace_function_calls(frame, event, arg, jsonl_file):
    if event == 'call':
        code = frame.f_code
        func_name = code.co_name
        class_name = None

        # 获取所属类名（如果有）
        if 'self' in frame.f_locals:
            class_name = frame.f_locals['self'].__class__.__name__

        # 获取文件路径
        file_path = code.co_filename
        # 转换文件路径为模块路径
        module_path = os.path.relpath(file_path, start=os.getcwd()).replace(os.sep, ".")
        file_name = os.path.splitext(module_path)[0]

        full_func_path = f"{file_name}.{class_name}.{func_name}" if class_name else f"{file_name}.{func_name}"

        def trace_local_vars(frame, event, arg):
            if event == 'return':
                local_vars = frame.f_locals.copy()
                # 获取输入参数
                input_args = {**frame.f_locals}
                # 获取返回值
                return_value = arg
                save_local_vars(local_vars, full_func_path, input_args, return_value, jsonl_file)
            return trace_local_vars

        return trace_local_vars
    return trace_function_calls

def debug_function_scope(json_path='debug_info.jsonl'):
    def decorator(func):
        def wrapper(*args, **kwargs):
            jsonl_file = json_path

            # 清空或创建 JSONL 文件
            if not os.path.exists(jsonl_file):
                open(jsonl_file, "w", encoding='utf-8').close()
            # 启动全局跟踪
            sys.settrace(lambda frame, event, arg: trace_function_calls(frame, event, arg, jsonl_file))
            result = func(*args, **kwargs)
            sys.settrace(None)  # 取消跟踪

            return result

        return wrapper
    return decorator