# ExcelHelper Agent

**基于大模型的 Excel 智能数据处理 Agent —— 你说需求，它来操作，操作可记忆、可回放。**

[![Tech](https://img.shields.io/badge/LLM-Deepseek-blue)](https://platform.deepseek.com/)
[![Framework](https://img.shields.io/badge/Framework-LangChain-green)](https://www.langchain.com/)
[![RAG](https://img.shields.io/badge/RAG-Chroma-orange)](https://www.trychroma.com/)
[![UI](https://img.shields.io/badge/UI-Native%20Web-lightgrey)]()
[![License](https://img.shields.io/badge/License-MIT-yellow)]()

---

## 项目定位

这是一个 **LLM Agent 应用**，面向日常工作中高频的 Excel 数据处理场景：

- 每周从后台导出数据，需要做匹配、分组透视、汇总、导出报表
- 操作步骤固定但繁琐：VLOOKUP 匹配多表 → 分组求和 → 算占比 → 加合计 → 调格式
- 每次换了新数据，所有操作要手动重做一遍

**ExcelHelper Agent 的做法**：第一遍你告诉它做什么（自然语言），它自动执行；同时把操作步骤保存下来。下次新数据来了，一句话或一键就重跑，不再需要 AI 再次理解。

## 核心能力

- **自然语言驱动** —— 用说话的方式描述需求，Agent 自动将指令解析为 pandas 操作序列
- **RAG 知识增强** —— 业务规则、字段口径、计算公式写入 Markdown 文档，Agent 执行前自动检索并遵循
- **步骤记忆与回放** —— 每次成功的操作序列可以命名保存，下次换数据直接回放
- **多表关联** —— 支持多文件上传，Agent 感知所有表的列结构，自动推断合并键和关联方式
- **多轮对话** —— 对话历史保留，可以对上一步结果进行调整和修正

## 示例场景

### 场景一：周报汇总

> 你有一份 Circle 使用数据，需要按圈子分组，算总时长、人均时长、参与人数，加合计行。

你只需说：

```
按 circle_name 分组，对 duration_min 求和和平均值，加合计行
```

Agent 自动解析为：读取数据 → 分组聚合 → 添加合计行 → 导出 Excel。保存为 `circle_weekly_report`，以后每周传新数据，直接输入序列名即可。

### 场景二：多表匹配与计算

> 你有三张表：语文成绩表、数学成绩表、英语成绩表，需要按姓名合并，算加权总分（40%+35%+25%）。

你只需说：

```
结合这三个表，按姓名匹配，成绩按 40%+35%+25% 的比例算加权总分
```

Agent 自动识别三张表的列结构，推断需要两次 merge，生成正确的加权公式 `语文*0.4 + 数学*0.35 + 英语*0.25`。

### 场景三：业务规则约束

> 你的业务规定：duration_min < 5 的记录是脏数据，测试用户（user_id 含 test）要排除，周报只统计工作日。

这些规则写入 `knowledge_base/business_rules.md`，Agent 每次执行前都会通过 RAG 检索到相关规则，自动在步骤中加入 `filter` 操作。

## Agent 架构

```
用户输入（自然语言）
      │
      ▼
┌─────────────┐
│  RAG 检索    │ ← knowledge_base/*.md → Chroma 向量库 → 语义检索业务规则
└─────────────┘
      │ 业务上下文
      ▼
┌─────────────┐
│  LangChain   │ ← System Prompt + Few-shot + 对话历史 + 列结构信息
│  编排 LLM    │
└─────────────┘
      │ 步骤 JSON
      ▼
┌─────────────┐
│  用户确认     │ ← 步骤卡片展示，可取消或修改
└─────────────┘
      │ 确认执行
      ▼
┌─────────────┐
│  Pandas 执行  │ → 结果预览 → 导出 Excel
└─────────────┘
      │
      ▼
┌─────────────┐
│  步骤保存     │ → steps/xxx.json → 下次一句话回放
└─────────────┘
```

### Agent 相关技术要点

| 能力 | 实现 |
|------|------|
| **工具调用** | Agent 定义 9 种操作（merge / groupby / pivot_table / filter / sort / add_column / add_total_row / export），LLM 根据用户意图和当前数据列结构，自主选择工具并填参 |
| **RAG 知识增强** | 业务文档 → `HuggingFaceEmbeddings` → Chroma 向量库 → 每次解析前检索 Top-K 相关片段，注入 System Prompt，确保 Agent 遵循业务口径 |
| **多轮对话记忆** | LangChain 对话管理，保留最近 6 条历史，用户可以说"不对，按部门而不是按圈子分"来修正 |
| **Schema 感知** | 每次请求将当前所有已上传文件的列名和数据类型传给 LLM，Agent 基于真实列结构生成操作 |
| **步骤确定性** | 保存的操作序列是纯参数化 JSON，回放时不经过 LLM，100% 确定性执行 |

## 快速开始

### 1. 安装

```bash
git clone https://github.com/yourname/excel-helper.git
cd excel-helper
pip install -r requirements.txt
```

### 2. 配置

```bash
cp .env.example .env
# 编辑 .env：
#   DEEPSEEK_API_KEY=sk-你的key
#   HF_ENDPOINT=https://hf-mirror.com  （国内用户）
```

### 3. 启动

```bash
python server.py
```

浏览器打开 `http://127.0.0.1:8765`

### 4. 使用

1. 侧边栏上传 Excel/CSV 文件
2. 聊天框用自然语言描述需求
3. 查看 Agent 解析的步骤卡片，点执行
4. 右侧查看结果，下载 Excel
5. 命名保存，下次一键回放

## 自定义知识库（可选）

在 `knowledge_base/` 目录下创建 Markdown 文件，写入你的业务规则：

```markdown
# 数据清洗规则
- duration_min < 5 的记录视为脏数据，分析前需排除
- user_id 包含 "test" 的记录为测试账号，正式报表中不包含
```

点侧边栏 **Rebuild KB** 生效。不配知识库也能用——Agent 的通用理解力足以处理大多数场景。

## 技术栈

| 层级 | 技术 |
|------|------|
| LLM | Deepseek Chat（通过 LangChain `ChatOpenAI` 调用） |
| Agent 框架 | LangChain（Prompt 编排、对话记忆管理） |
| RAG | Chroma 向量数据库 + `all-MiniLM-L6-v2` 本地 Embedding |
| 执行引擎 | Pandas + OpenPyXL |
| 后端 | FastAPI |
| 前端 | 原生 HTML/CSS/JS（单页，无框架依赖） |
| 前端文件解析 | SheetJS |

## 项目结构

```
ExcelHelper/
├── server.py              # FastAPI 后端
├── agent.py               # Agent 核心：RAG + Deepseek → 步骤解析
├── executor.py            # 步骤执行引擎
├── recorder.py            # 步骤序列存取
├── prompts.py             # System prompt + few-shot
├── knowledge.py           # RAG 向量库
├── excel_agent.html       # 前端界面
├── requirements.txt
├── .env.example
├── knowledge_base/        # 业务知识文档
└── steps/                 # 保存的步骤序列
```

## License

MIT
