import fnmatch
import os
def is_ignored(file_path: str):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    IGNORE_PATH = os.path.join(project_root, ".agentignore")
    ignore_list = []
    if os.path.exists(IGNORE_PATH):
        with open(IGNORE_PATH, "r") as f:
            ignore_list = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    for pattern in ignore_list:
        if fnmatch.fnmatch(file_path, pattern):
            return True
    return False
def safe_read_file(file_path: str) -> str:

    if (is_ignored(file_path)):
        print(f"🚨 安全防御：访问被拒绝！路径 '{file_path}' 命中 .agentignore 规则。")
        return " "
    if not os.path.exists(file_path):
        print(f"⚠️ 文件不存在：{file_path}")
        return ""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"❌ 读取错误：{e}")
        return ""
