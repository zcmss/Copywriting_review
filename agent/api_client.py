import os
from openai import OpenAI
from dotenv import load_dotenv
import time
from tools import registry
AGENT_SYSTEM_PROMPT = """
你是一个具备高度自主权和工程严谨性的审计 Agent。在调用任何工具之前，你必须遵循以下流程：

1. <think>：
   - 分析用户任务的最终目标。
   - 确定当前步骤需要调用的工具（如 read_local_draft）。
   - 检查参数（如 file_path）是否符合安全规范。
   - 预判可能出现的错误（如文件不存在、被 .agentignore 拦截）。
2. 调用工具：根据思考结果，输出正确的工具调用参数。
3. 观察与反思：拿到工具返回后，判断是否达到了预期，如果没有，请修正计划。

请注意：你受到 .agentignore 沙箱限制，无法访问敏感文件。
"""
load_dotenv()
client = OpenAI(
    api_key=os.getenv("LLM_API_KEY"),
    base_url=os.getenv("LLM_BASE_URL")

)
def run_reasoning_step(task_description):
    messages = [
        {'role': "system", 'content': AGENT_SYSTEM_PROMPT},
        {'role': "user", 'content': task_description}
    ]
    for attempt in range(3):
        response = client.chat.completions.create(
            model= 'Qwen/Qwen3.5-35B-A3B',
            messages= messages,
            tools=registry.tools_metadata,
            tool_choice='auto'
        )
        msg = response.choices[0].message
        if not msg.tool_calls:
            # AI 觉得不需要调工具了，直接给结论
            print(f"\n✅ Final Answer: {msg.content}")
            break

            # 处理工具调用
        for tool_call in msg.tool_calls:
            observation = registry.handle(tool_call)
            print(f"📡 工具反馈: {observation}")

            # 将错误结果喂回给 AI
            messages.append(msg)
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": observation  # 比如这里会传回 "⚠️ 文件不存在"
            })

def call_ai_audit(content: str, retries=3):
    prompt = f"请作为小红书资深运营，审计以下文案是否合规，并给出爆款改进建议：\n\n{content}"
    for i in range(retries):
        try:
            response = client.chat.completions.create(
                model = 'Qwen/Qwen3.5-35B-A3B',
                messages = [{
                    'role': 'user',
                    'content': [{
                        'type': 'text',
                        'text': prompt,
                    }]
                }],
                timeout=60
            )
            if not response or not response.choices:
                print(f"❌ API 返回了空结果 (第 {i + 1} 次尝试)")
                continue
            print(response)
            return response.choices[0].message.content
        except Exception as e:
            if i < retries - 1:
                wait_time = (2 ** i)
                print(f"⚠️ API 调用失败，{wait_time}秒后重试... (错误: {e})")
                time.sleep(wait_time)
            else:
                raise e