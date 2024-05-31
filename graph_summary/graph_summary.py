import os
import json
import pickle
import shutil

class Log():
    def __init__(self, path='out.txt'):
        self.path = path
        with open(path, 'w') as f:
            f.write('')
    def write(self, line):
        with open(self.path, 'a') as f:
            f.write(line+'\n')

def traverse_dir(root_path):
    for entry in os.listdir(root_path):
        print(entry)

def summary_graph(root_path, no_graph_root_path):
    count = [0, 0]
    log = Log('no_graph.txt')
    for task in os.listdir(root_path):
        graph_path = os.path.join(root_path, task, 'callGraph.pkl')
        if os.path.exists(graph_path):
            count[0] += 1
        else:
            log.write(task)
            # 将task文件夹移动到no_call_graph文件夹
            shutil.move(os.path.join(root_path, task), no_graph_root_path)

        count[1] += 1

    print(f'有graph的数量: \t {count[0]} / {count[1]}')


def get_task_graph(root_path, task_id):
    log = Log('out.txt')
    graph_path = os.path.join(root_path, task_id, 'callGraph.pkl')
    # graph_path = r'D:\study\postgraduate\study_project\alibaba_LLM\code\docker\Probe\ProbeCode\output\scikit-learn__scikit-learn-11040_2024-05-21_09-11-36\callGraph.pkl'
    # graph_path = r'D:\study\postgraduate\study_project\alibaba_LLM\code\docker\Probe\ProbeCode\output\django__django-13230_2024-05-21_08-55-54\callGraph.pkl'
    # graph_path = os.path.join(r'D:\study\postgraduate\study_project\alibaba_LLM\code\docker\Probe\ProbeCode\output\matplotlib__matplotlib-23563_2024-05-21_08-33-57\callGraph.pkl')
    with open(graph_path, 'rb') as f:
        graph = pickle.load(f)
    for a, b in graph.edges():
        log.write(f'{a} -> {b}')

def load_graph(root_path, task_id):
    graph_path = os.path.join(root_path, task_id, 'callGraph.pkl')
    if os.path.exists(graph_path):
        with open(graph_path, 'rb') as f:
            graph = pickle.load(f)
            return graph
    else:
        return None

def isInGraph(graph, name):
    for node in graph.nodes():
        if name in node:
            return True
    return False

def summary_buggy_function(root_path, stat_path):
    log = Log('summary_buggy.txt')
    with open(stat_path, 'r', encoding='utf-8') as f:
        stat_data = json.load(f)

    count = [0, 0]

    for task in stat_data:
        count[1] += 1
        gt_modifications = task['gt_modifications']
        graph = load_graph(root_path, task['task_id'])
        if graph is None:
            continue
        flag = True
        for func in gt_modifications:
            py_path = func[0]
            py_name = os.path.basename(py_path).split('.')[0]
            class_name = func[1]
            func_name = func[2]
            name = ''
            # if py_name:
            #     name += py_name
            # if class_name:
            #     name += '.' + class_name
            if func_name:
                name += '.' + func_name

            if not isInGraph(graph, name):
                flag = False

        if flag:
            count[0] += 1
        else:
            log.write(f"{task['task_id']}")
    print(count)



if __name__ == '__main__':
    # root_path = os.path.join(r'D:\study\postgraduate\study_project\alibaba_LLM\code\docker\Probe\ProbeCode\output_bak_0521')
    # stat_path = os.path.join(r'stat_v2.json')
    # summary_graph(root_path)
    # summary_buggy_function(root_path, stat_path)

    root_path = os.path.join(r'/root/alibaba/lanbo/probe_code_docker/call_graph_data')
    stat_path = os.path.join(r'stat_v2.json')
    no_graph_root_path = os.path.join(r'/root/alibaba/lanbo/probe_code_docker/no_call_graph_data')
    summary_graph(root_path, no_graph_root_path)
    # summary_buggy_function(root_path, stat_path)
    # get_task_graph(root_path, 'sympy__sympy-23117')

