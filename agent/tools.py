import json
import os
import inspect
from typing import get_type_hints

from utils import safe_read_file
class ToolRegistry:
    def __init__(self):
        self.tools_metadata = []
        self.functions = {}
    def register(self, func):
        name = func.__name__
        doc =func.__doc__ or "无描述"

        sig = inspect.signature(func)
        type_hints = get_type_hints(func)
        type_map = {
            str: "string",
            int: "integer",
            float: "number",
            bool: "boolean",
            list: "array",
            dict: "object"
        }
        properties = {}
        required_params = []
        for param_name, param in sig.parameters.items():
            arg_type = type_hints.get(param_name,str)
            json_type = type_map.get(arg_type, "string")
            properties[param_name] = {
                'type' : json_type,
                'description' : f'参数{param}({json_type})'
            }
            if param.default == inspect.Parameter.empty:
                required_params.append(param_name)
        tool_definition = {
            'type' : "function",
            'function' : {
                'name': name,
                'description': doc.strip() ,
                'parameters' : {
                    'type' : 'object',
                    'properties' : properties,
                    'required' : required_params
                }
            }
        }
        self.tools_metadata.append(tool_definition)
        self.functions[name] = func
        return func
    def handle(self, tool_call):
        func_name = tool_call.function.name
        args = json.loads(tool_call.function.arguments)
        print(f"🛠️  执行工具: {func_name} | 参数: {args}")
        if func_name in self.functions:
            return self.functions[func_name](**args)
        return "错误：工具未定义"

registry = ToolRegistry()
@registry.register
def read_local_draft(file_path: str):
    """读取本地文案文件。参数 file_path 是相对于项目根目录的路径。"""
    from utils import safe_read_file
    result = safe_read_file(file_path)
    return result + f"{file_path if bool(result) else ""}"

@registry.register
def list_files(directory: str ):
    """列出指定目录下的文件。"""
    import os
    try:
        return str(os.listdir(directory))
    except Exception as e:
        return str(e)

@registry.register
def get_current_time():
    """获取当前的系统时间，用于判断文案的时效性。"""
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
