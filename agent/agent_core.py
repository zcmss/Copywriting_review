import time
import json
from api_client import client
from tools import registry
from memory import brain
from logger_config import logger
import sys

# ================= 配置区 =================
MODEL_NAME = "Qwen/Qwen3.5-35B-A3B"
TASK_TYPE = "audit"
MAX_STEPS = 10



# ================= 核心逻辑 =================

def sanitize_observation(data, tool_name, args):
    """
    【防御性编程】清洗脏数据并强制关联标签
    """
    str_data = str(data)

    # 1. 乱码检查
    import re
    if len(str_data) > 30 and re.match(r'^[a-zA-Z0-9]{20,}$', str_data):
        logger.error(f"❌ 检测到工具 {tool_name} 返回乱码数据")
        return f"⚠️ [System Error] 工具 {tool_name} 返回数据编码异常，疑似文件损坏。"

    # 2. 标签化增强 (Anchoring)
    if tool_name == "read_file_tool":
        file_path = args.get("file_path", "未知路径")
        return f"【文件读取报告】\n- 目标文件: {file_path}\n- 原始内容: \n---\n{str_data}\n---"

    return f"【工具 {tool_name} 执行结果】: {str_data}"


def validate_fencing_token(incoming_token: int):
    """
    预留的栅栏令牌校验位
    """
    latest_token = brain.get_latest_token_from_db()

    if incoming_token < latest_token:
        # 说明这个指令是基于“过时的信息”生成的
        logger.error(f"❌ 拒绝执行：检测到过时的指令 (Token {incoming_token} < {latest_token})")
        return False
    return True

def run_agent_loop(user_input, task_id: str ):
    """
    【自主推理引擎】整合日志、记忆与 Qwen 3.5
    """

    brain.save_episodic(task_id, "user", user_input)

    logger.info(f"🚀 === 智能审计任务启动 | ID: {task_id} ===")

    step = 0
    while step < MAX_STEPS:
        step += 1
        logger.info(f"🔍 [Step {step}] 正在构建全脑上下文...")

        # 1. 提取多维记忆 (SOP + Semantic + Sensory + Episodic)
        context = brain.get_full_context(task_id, TASK_TYPE)

        try:
            # 2. 发起 Qwen 推理
            start_time = time.time()
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=context,
                tools=registry.tools_metadata,
                tool_choice="auto",
                temperature=0.2
            )
            duration = time.time() - start_time
            logger.info(f"⏱️ Qwen 推理完成 | 耗时: {duration:.2f}s")

            msg = response.choices[0].message

            # --- 分支 A: 调用工具 ---
            if msg.tool_calls:
                # 记录推理意图到日志和数据库
                thought = msg.content or "正在分析文件状态以进行下一步审计..."
                logger.info(f"💭 Qwen 思考: {thought}")
                brain.save_episodic(task_id, "assistant", thought)

                for tool_call in msg.tool_calls:
                    t_name = tool_call.function.name
                    t_args = json.loads(tool_call.function.arguments)

                    logger.warning(f"🛠️ [Action] 执行工具: {t_name} | 参数: {t_args}")

                    # 执行工具
                    raw_obs = registry.handle(tool_call)

                    # 标签化清洗
                    clean_obs = sanitize_observation(raw_obs, t_name, t_args)

                    # 存入 Observation 记忆
                    brain.save_episodic(task_id, "tool", clean_obs)
                    logger.debug(f"👁️ [Observation] 记忆已更新 (长度: {len(clean_obs)})")

                continue  # 继续下一轮 Reasoning Loop

            # --- 分支 B: 任务终结 ---
            else:
                final_res = msg.content
                logger.info("✅ [Success] Agent 已给出最终审计报告。")
                brain.save_episodic(task_id, "assistant", final_res)
                print(f"\n--- 最终审计报告 ---\n{final_res}\n")
                brain.auto_compress(task_id, threshold=15)
                break

        except Exception as e:
            logger.error(f"💥 循环发生崩溃: {str(e)}", exc_info=True)
            break

    if step >= MAX_STEPS:
        logger.error("🛑 达到推理步数上限 (Max Steps)，任务强行终止。")

    # 3. 记忆自维护
    brain.auto_compress(task_id)
    logger.info(f"💾 任务 {task_id} 记忆已压缩归档。")


def start_interactive_session():
    # 生成一个固定的 Session ID，代表这次对话
    session_id = f"session_{int(time.time())}"
    logger.info(f"✨ 交互式会话已开启 | Session: {session_id}")
    brain.save_procedural("audit", """
    1. 执行 list_files 获取目录下的所有文件名。
    2. 【关键】对于列表中的每一个文件，必须依次调用 read_file_tool 读取内容。
    3. 严禁只读取一个文件就结束。
    4. 在读取完所有文件并对比语义禁词库后，给出汇总审计报告。
    5. 只有当目录下所有文件都处理完毕，才输出最终结论。
    """)
    print("🤖 Agent: 您好！我是您的文案审计助手。您可以输入需求（如：审计 inputs 目录），或者直接跟我聊天。")

    while True:
        time.sleep(0.1)
        sys.stdout.flush()
        user_input = input("\n👤 You: ").strip()

        if user_input.lower() in ['exit', 'quit', '退出']:
            print("🤖 Agent: 再见！")
            break

        # 调用我们之前的推理引擎，但注意：
        # 这里不要在 run_agent_loop 里重置 task_id，要传入 session_id
        run_agent_loop(user_input, task_id=session_id)

# ================= 启动区 =================
if __name__ == "__main__":
    start_interactive_session()