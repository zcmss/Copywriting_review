### 🚀 Qwen-Agent-Sentinel (审计哨兵)

> **基于 Qwen-3.5 的自主化文案审计智能体**

[![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Model](https://img.shields.io/badge/LLM-Qwen--3.5--35B-orange.svg)](https://modelscope.cn/models/qwen/Qwen-3.5-35B-A3B)
[![Architecture](https://img.shields.io/badge/Pattern-ReAct--Loop-green.svg)](#)

#### 🌟 项目简介
本项目实现了一个具备“全脑记忆”的工业级自主智能体 (Autonomous Agent)。它能够根据预设的 SOP 和行业合规标准，自动遍历本地目录，通过 **ReAct 推理循环** 发现并审计文案中的违规点。

不同于传统的简单 Prompt 或标准 RAG，本项目重点解决了 Agent 在复杂任务中容易产生的 **“记忆迷失”** 和 **“逻辑断层”** 问题。

---

#### 🧠 核心架构亮点

1.  **统一记忆架构 (Unified Memory Architecture)**：
    * **Episodic (情景记忆)**：基于 SQLite 存储任务流，确保推理链路可追溯。
    * **Semantic (语义记忆)**：固化行业合规规则与禁词库，降低模型幻觉。
    * **Procedural (程序记忆)**：通过强约束 SOP 引导 Agent 按照标准流程（扫目录->读取->对比）执行。
    * **Sensory (感知记忆)**：实时捕捉工具返回的环境快照。
    
2.  **标签化锚定机制 (Metadata Anchoring)**：
    针对多文件处理场景，在工具返回结果中强制封装元数据标签，解决了 LLM 在长上下文中文件名与内容错位的顽疾。

3.  **可观测性日志系统 (Observability)**：
    分级记录 Agent 的思考轨迹（Thought）、执行动作（Action）与响应耗时，支持生产环境下的推理溯源。



---

#### 🛠️ 快速启动

**1. 克隆仓库**
```bash
git clone https://github.com/你的用户名/Qwen-Agent-Sentinel.git
cd Qwen-Agent-Sentinel
```

**2. 安装依赖**
```bash
pip install -r requirements.txt
```

**3. 配置环境**
复制 `.env.example` 为 `.env`，并填入你的 API Key：
```bash
cp .env.example .env
# 编辑 .env 文件
DASHSCOPE_API_KEY=your_api_key_here
```

**4. 运行审计**
将待审计文案放入 `agent/inputs/` 目录，执行：
```bash
python src/main.py
```

---

#### 📊 运行演示 (Trace Example)

```text
17:05:01 - [INFO] - 🚀 任务启动 | ID: qwen_task_12345
17:05:03 - [INFO] - 🤔 Agent 思考: 我需要先列出目录下的所有文案。
17:05:04 - [WARNING] - 🛠️ [Action] 执行工具: list_files | 参数: {"directory": "inputs"}
17:05:08 - [INFO] - 💭 Qwen 思考: 发现 v1.txt 存在疑似违禁词，准备读取详情。
...
✅ [Final Result]: 审计完成。v1.txt 包含违禁词“绝绝子”，违反语义规程第 3 条。
```

---

#### 📁 目录结构
```text
.
├── agent/                  # 核心智能体模块
│   ├── inputs/             # 待审计文案存放处
│   ├── logs/               # 运行日志（本地）
│   ├── agent_core.py       # ReAct 自主推理引擎
│   ├── api_client.py       # 大模型 API 封装
│   ├── logger_config.py    # 日志系统配置
│   ├── memory.py           # 四层记忆模型逻辑 (SQLite)
│   ├── tools.py            # 工具注册中心 (File Ops)
│   └── utils.py            # 通用工具函数
├── .env                    # 私密 API Key (已忽略)
├── .env.example            # 配置模板
├── .gitignore              # Git 忽略规则
├── README.md               # 项目说明文档
└── requirements.txt        # 依赖清单
```

---

#### 🛣️ Roadmap (未来规划)
- [ ] 集成向量数据库 (ChromaDB) 实现超大规模文档 RAG。
- [ ] 增加人机协同 (Human-in-the-loop) 动态干预界面。
- [ ] 支持多模态文案（图片内文字）识别审计。

