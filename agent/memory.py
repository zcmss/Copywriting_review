import sqlite3
import json
from datetime import datetime


class UnifiedAgentMemory:
    def __init__(self, client, db_path="agent_brain.db"):
        self.client = client
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_db()

    def _init_db(self):
        """一次性初始化所有脑区表"""
        # 1. 情景记忆表 (Episodic)
        self.conn.execute('''CREATE TABLE IF NOT EXISTS episodic_memory
            (id INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT, role TEXT, content TEXT, 
             is_compressed INTEGER DEFAULT 0, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')

        # 2. 语义记忆表 (Semantic)
        self.conn.execute('''CREATE TABLE IF NOT EXISTS semantic_memory
            (id INTEGER PRIMARY KEY AUTOINCREMENT, entity TEXT UNIQUE, fact TEXT, 
             update_time DATETIME DEFAULT CURRENT_TIMESTAMP)''')

        # 3. 程序性记忆表 (Procedural)
        self.conn.execute('''CREATE TABLE IF NOT EXISTS procedural_memory
            (id INTEGER PRIMARY KEY AUTOINCREMENT, task_type TEXT UNIQUE, sop_steps TEXT)''')

        # 4. 感知记忆表 (Sensory)
        self.conn.execute('''CREATE TABLE IF NOT EXISTS sensory_memory
            (id INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT, raw_summary TEXT, 
             timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')

        self.conn.commit()

    # --- 统一写入接口 ---
    def save_episodic(self, task_id, role, content):
        self.conn.execute("INSERT INTO episodic_memory (task_id, role, content) VALUES (?, ?, ?)",
                          (task_id, role, content))
        self.conn.commit()

    def save_semantic(self, entity, fact):
        """AI 发现新规则时调用"""
        self.conn.execute("INSERT OR REPLACE INTO semantic_memory (entity, fact) VALUES (?, ?)", (entity, fact))
        self.conn.commit()

    def save_procedural(self, task_type, sop_steps):
        """开发者预设或 AI 总结流程时调用"""
        self.conn.execute("INSERT OR REPLACE INTO procedural_memory (task_type, sop_steps) VALUES (?, ?)",
                          (task_type, sop_steps))
        self.conn.commit()

    def save_sensory(self, task_id, summary):
        """感知工具（如 list_files）返回结果时调用"""
        self.conn.execute("INSERT INTO sensory_memory (task_id, raw_summary) VALUES (?, ?)", (task_id, summary))
        self.conn.commit()

    # --- 核心：记忆提取与全脑压缩逻辑 ---
    def get_full_context(self, task_id, task_type="xhs_audit"):
        # A. 提取活跃情景
        cursor = self.conn.execute(
            "SELECT role, content FROM episodic_memory WHERE task_id = ? AND is_compressed = 0 ORDER BY id ASC",
            (task_id,))
        episodic = [{"role": r, "content": (c if c is not None else "")} for r, c in cursor.fetchall()]

        # B. 提取知识 (安全提取)
        rows = self.conn.execute("SELECT fact FROM semantic_memory").fetchall()
        knowledge = [row[0] for row in rows] if rows else ["暂无特定背景知识"]

        # C. 提取 SOP (安全提取)
        sop_row = self.conn.execute("SELECT sop_steps FROM procedural_memory WHERE task_type = ?",
                                    (task_type,)).fetchone()
        sop_text = sop_row[0] if sop_row else "标准作业程序未定义。"

        # D. 提取感知 (安全提取)
        sensory_row = self.conn.execute(
            "SELECT raw_summary FROM sensory_memory WHERE task_id = ? ORDER BY id DESC LIMIT 1", (task_id,)).fetchone()
        sensory_text = sensory_row[0] if sensory_row else "当前环境未扫描。"

        system_content =f"""
        你是一个具备全脑记忆的审计专家。
        【操作规程 (SOP)】: {sop_text}
        【核心知识 (Semantic)】: {knowledge}
        【当前环境 (Sensory)】: {sensory_text}
        
        重要指令：
        1. 请检查对话历史，如果已经调用过某个工具并得到了结果，严禁重复调用相同参数的工具。
        2. 当你获得文案内容后，必须立即结合【核心知识】进行对比，并给出最终审计结论。
        3. 如果任务已完成，请直接回复结论，不要再输出“需要执行工具”。
        """
        return [{"role": "system", "content": system_content}] + episodic

    def auto_compress(self, task_id, threshold=10):
        """记忆压缩专家"""
        count = self.conn.execute("SELECT COUNT(*) FROM episodic_memory WHERE task_id = ? AND is_compressed = 0",
                                  (task_id,)).fetchone()[0]
        if count >= threshold:
            print(f"🧹 [Brain] 活跃记忆过多 ({count}条)，正在生成阶段性总结...")
            active_msgs = self.get_full_context(task_id)

            # 使用更快的模型或参数进行压缩
            response = self.client.chat.completions.create(
                model="Qwen/Qwen3.5-35B-A3B",
                messages=[{"role": "system",
                           "content": "你是一个记忆精炼专家。请总结这段任务执行过程，保留已达成的结论和重要的文件路径。"},
                          {"role": "user", "content": str(active_msgs)}],
                temperature=0
            )
            summary = response.choices[0].message.content
            try:
                # 归档旧记忆
                self.conn.execute("BEGIN")
                self.conn.execute("UPDATE episodic_memory SET is_compressed = 1 WHERE task_id = ? AND is_compressed = 0",
                                  (task_id,))
                self.save_episodic(task_id, "system", f"【前期任务回顾】：{summary}")
                print("✨ [Brain] 记忆压缩完成。")
            except Exception as e:
                self.conn.rollback()
                print(f"❌ [Memory] 压缩失败: {e}")