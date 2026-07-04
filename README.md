# Qwen-Agent-Sentinel

> 基于 Qwen-3.5 的自主文案审计 Agent —— ReAct 推理 × 四层记忆 × 混合 RAG 检索

[![Python](https://img.shields.io/badge/python-3.9+-blue)](https://www.python.org/)
[![Model](https://img.shields.io/badge/LLM-Qwen--3.5--35B-orange)](https://modelscope.cn/models/qwen/Qwen-3.5-35B-A3B)
[![Tests](https://img.shields.io/badge/tests-55%20passed-green)](#)
[![License](https://img.shields.io/badge/license-MIT-lightgrey)](LICENSE)

---

## 简介

一个具备**全脑记忆**的自主审计 Agent。它根据预设的 SOP 和合规标准，自动遍历本地目录，通过 **ReAct 推理循环**发现并审计文档中的违规点。

不同于简单的 Prompt 或标准 RAG，本项目重点解决 Agent 在复杂任务中容易产生的**"记忆迷航"**和**"逻辑断层"**问题。

---

## 核心架构

### 1. 四层统一记忆 (Unified Memory)

| 记忆层 | 存储 | 作用 |
|---|---|---|
| Episodic（情景） | SQLite | 保存任务执行流，确保推理链路可追溯 |
| Semantic（语义） | SQLite + ChromaDB | 固化行业合规规则与禁词库，RAG 自动注入 |
| Procedural（程序） | SQLite | SOP 强约束，引导标准流程（扫描→读取→对比） |
| Sensory（感知） | SQLite | 实时捕获工具返回的环境快照 |

**记忆压缩**：超过阈值自动调用 Qwen 做阶段摘要，防止长任务上下文溢出。

### 2. 混合检索引擎 (Hybrid RAG)

- **向量检索**：ChromaDB + ONNX 本地嵌入模型（`all-MiniLM-L6-v2`），离线运行
- **关键词检索**：BM25 精准匹配违禁词、编号等硬性规则
- **自动注入**：每次推理前根据用户问题检索 Top-K 规则，写入语义记忆
- **对话内检索**：Agent 可在推理循环中主动调用 `search_knowledge_base` 工具

### 3. 防御性工程实践

- **文件指纹 (Fingerprinting)**：读取时记录 MD5 快照，环境变动实时感知
- **Fencing Token**：工具调用时效性校验，防止基于过期上下文执行指令
- **.agentignore 沙箱**：类 Git 模式匹配，控制 Agent 文件访问边界
- **输入清洗**：路径遍历拦截 + 编码容错（UTF-8/GBK）+ 乱码检测

### 4. 可观测性日志

分级记录 Thought（思考）→ Action（行动）→ Observation（观察），支持生产环境推理溯源。

---

## 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/zcmss/Copywriting_review.git
cd Copywriting_review
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境

复制 `.env.example` 为 `.env`，填入 API Key：

```bash
cp .env.example .env
```

编辑 `.env`：

```env
LLM_API_KEY=your_api_key_here
LLM_BASE_URL=https://api-inference.modelscope.cn/v1
MODEL_NAME=Qwen/Qwen3.5-35B-A3B
```

### 4. 灌入种子规则

```bash
python -m agent.seed_knowledge
```

输出：

```
Before: 0 entries
After:  6 entries
Seed data loaded.
```

### 5. 运行审计

将待审计文档放入 `agent/inputs/`，执行：

```bash
python -m agent.agent_core
```

### 6. 运行测试

```bash
pytest tests -v
```

---

## 运行示例

```text
17:05:01 - [INFO] - === 智能审计任务启动 | ID: session_1717000000 ===
17:05:02 - [INFO] - [Brain] RAG 注入语义记忆...
17:05:03 - [INFO] - Agent 思考: 我需要先列出目录下的所有文档。
17:05:04 - [WARNING] - [Action] 执行工具: list_files | 参数: {"directory": "agent/inputs"}
17:05:05 - [INFO] - Agent 思考: 发现 audit_v1.txt，准备读取详情。
17:05:06 - [WARNING] - [Action] 执行工具: read_file_tool | 参数: {"file_path": "agent/inputs/audit_v1.txt"}
17:05:07 - [INFO] - Agent 思考: 检测到违禁词"绝绝子""yyds"，违反语义规则第1条。
...
[Final Result]: audit_v1.txt 包含违禁词"绝绝子""yyds"，违反 forbidden-words 规则。
```

---

## 目录结构

```text
.
├── agent/
│   ├── inputs/             # 待审计文档
│   ├── logs/               # 运行日志（本地）
│   ├── chroma_db/          # ChromaDB 持久化向量库
│   ├── chroma_models/      # ONNX 嵌入模型文件
│   ├── agent_core.py       # ReAct 自主推理引擎
│   ├── api_client.py       # Qwen API 封装
│   ├── memory.py           # 四层记忆模型 (SQLite)
│   ├── knowledge_base.py   # 混合检索引擎 (ChromaDB + BM25)
│   ├── seed_knowledge.py   # 种子规则灌入脚本
│   ├── tools.py            # 工具注册中心
│   ├── utils.py            # 安全读写 & 输入清洗
│   └── logger_config.py    # 日志系统配置
├── tests/                  # pytest 测试套件（55 cases）
├── .agentignore            # Agent 文件访问沙箱规则
├── .env.example            # 环境变量模板
├── .gitignore
├── README.md
└── requirements.txt
```

---

## 技术栈

| 层级 | 技术 |
|---|---|
| LLM | Qwen-3.5-35B (ModelScope API) |
| 推理框架 | ReAct Loop (Thought → Action → Observation) |
| 记忆存储 | SQLite（四层表结构） |
| 向量检索 | ChromaDB + ONNX `all-MiniLM-L6-v2` 本地嵌入 |
| 关键词检索 | BM25 (rank_bm25) |
| 测试 | pytest（55 测试，覆盖记忆/工具/RAG/安全） |

---

## Roadmap

- [x] 集成 ChromaDB 实现语义检索
- [x] BM25 混合检索（向量 + 关键词联合召回）
- [x] ONNX 本地嵌入，零 API 依赖
- [x] pytest 测试套件
- [x] 工具动态注册（`registry.add` / `list_tools`）
- [ ] 多模态文档审计（图片内文字识别）
- [ ] 人机协同 (Human-in-the-loop) 动态干预
- [ ] FastAPI + Docker 服务化部署
