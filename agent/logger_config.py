import logging
import os
from datetime import datetime


def setup_agent_logger(log_name="AgentSys"):
    # 创建 logs 文件夹
    if not os.path.exists("logs"):
        os.makedirs("logs")

    logger = logging.getLogger(log_name)
    logger.setLevel(logging.DEBUG)

    # 1. 定义格式：时间 - 级别 - 消息
    formatter = logging.Formatter(
        '%(asctime)s - [%(levelname)s] - %(message)s',
        datefmt='%H:%M:%S'
    )

    # 2. 文件处理器：记录所有详细信息
    file_name = f"logs/agent_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(file_name, encoding='utf-8')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)

    # 3. 控制台处理器：只显示重要信息
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)

    # 避免重复添加 Handler
    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger


# 初始化
logger = setup_agent_logger()