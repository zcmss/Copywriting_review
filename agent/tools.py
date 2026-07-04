import json, os, inspect
from typing import get_type_hints
from agent.logger_config import logger
from agent.memory import brain

class ToolRegistry:
    def __init__(self):
        self.tools_metadata = []
        self.functions = {}

    def register(self, func):
        name = func.__name__
        doc = func.__doc__ or "no description"

        sig = inspect.signature(func)
        type_hints = get_type_hints(func)
        type_map = {
            str: "string", int: "integer", float: "number",
            bool: "boolean", list: "array", dict: "object",
        }
        properties = {}
        required_params = []
        for param_name, param in sig.parameters.items():
            arg_type = type_hints.get(param_name, str)
            json_type = type_map.get(arg_type, "string")
            properties[param_name] = {
                "type": json_type,
                "description": f"parameter {param_name} ({json_type})",
            }
            if param.default == inspect.Parameter.empty:
                required_params.append(param_name)

        tool_definition = {
            "type": "function",
            "function": {
                "name": name,
                "description": doc.strip(),
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required_params,
                },
            },
        }
        self.tools_metadata.append(tool_definition)
        self.functions[name] = func
        return func


    def add(self, func, name=None, description=None):
        """programmatically register a tool function - no decorator needed.

        Usage:
            registry.add(my_func)
            registry.add(my_func, name="custom", description="does X")
        """
        if name:
            func.__name__ = name
        if description:
            func.__doc__ = description
        return self.register(func)

    # ===== 新增：列出已注册工具 =====
    def list_tools(self):
        """return list of (name, description) for all registered tools."""
        result = []
        for meta in self.tools_metadata:
            f = meta["function"]
            result.append((f["name"], f["description"]))
        return result


registry = ToolRegistry()

@registry.register
def read_file_tool(file_path: str):
    """read local document file"""
    from agent.utils import safe_read_file
    try:
        content = safe_read_file(file_path)
        if content:
            import hashlib
            brain.update_file_snapshot(file_path, content)
            logger.debug(f"[Fingerprint]: Captured snapshot for {file_path}")
            return content
        return "file is empty or access denied"
    except Exception as e:
        return f"Error reading file: {str(e)}"

@registry.register
def list_files(directory: str):
    """list files in a directory"""
    import os
    try:
        return str(os.listdir(directory))
    except Exception as e:
        return str(e)

@registry.register
def get_current_time():
    """get current system time for document timeliness checks"""
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
