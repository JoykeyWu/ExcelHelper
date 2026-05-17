# ExcelHelper Agent

用自然语言操作 Excel —— 教一次，下次一键回放。

**Deepseek + LangChain + RAG + Pandas**

## 它能做什么

上传 CSV/Excel 文件，用自然语言描述你想做的操作，AI 自动解析为 pandas 执行步骤。确认执行后，可以把这次操作保存为命名序列。下次换新数据，输入序列名或点 ▶ 即可一键回放——完全不需要再调 LLM，秒出结果。

### 支持的操作

| 操作 | 说明 |
|------|------|
| `读取数据` | 读取 CSV/Excel 文件 |
| `匹配关联` | 连接多张表（类似 VLOOKUP） |
| `分组聚合` | 按列分组，求和/平均/计数等 |
| `数据透视表` | 创建交叉透视表 |
| `条件筛选` | 按条件过滤行 |
| `排序` | 按列排序 |
| `添加计算列` | 新增计算列（如 总分 = 语文 + 数学） |
| `添加合计行` | 末尾追加合计行 |
| `导出 Excel` | 导出结果到 Excel |

### 使用示例

```
按 circle_name 分组，对 duration_min 求和和平均值，加合计行
```

```
匹配 user_mapping.xlsx，按 user_id 关联，然后按 department 分组求总时长
```

```
匹配 math.csv 和 en.csv，按姓名关联，加一列加权总分 = 语文*0.4 + 数学*0.35 + 英语*0.25
```

```
只看运动挑战，按日期求总时长，升序排列
```

## 快速开始

### 1. 克隆并安装

```bash
git clone https://github.com/yourname/excel-helper.git
cd excel-helper
pip install -r requirements.txt
```

### 2. 配置 API Key

```bash
cp .env.example .env
# 编辑 .env，填入你的 Deepseek API Key：
# DEEPSEEK_API_KEY=sk-你的key
# HF_ENDPOINT=https://hf-mirror.com   （国内用户设置此项，加速模型下载）
```

在 [platform.deepseek.com](https://platform.deepseek.com/) 注册并获取 API Key。

### 3. 启动

```bash
python server.py
```

浏览器打开 `http://127.0.0.1:8765`

### 4. 使用流程

1. **上传文件** —— 侧边栏上传 CSV 或 XLSX（支持多文件）
2. **描述需求** —— 聊天框输入自然语言指令
3. **确认步骤** —— 查看 AI 解析出的步骤卡片
4. **执行** —— 右侧面板显示结果，可下载 Excel
5. **保存序列** —— 命名保存，下次一键回放
6. **回放** —— 传新数据后输入序列名，或直接点侧边栏 ▶ Run

## 架构

```
excel_agent.html  ──fetch──>  server.py (FastAPI :8765)
  （浏览器界面）                ├── /api/parse     → agent.py → RAG + Deepseek → 步骤 JSON
                              ├── /api/execute   → executor.py → pandas → 结果
                              ├── /api/upload    → 存储文件，返回列结构
                              ├── /api/download  → 下载生成的 Excel
                              └── /api/sequences → 保存/加载/回放步骤序列
```

- **只在"教"的时候调用 LLM**（自然语言 → 步骤解析）。回放是纯 pandas 执行，快速且确定。
- **RAG 在执行前检索知识库**，将相关业务规则注入提示词，确保 AI 按正确口径工作。
- **步骤序列** 以 JSON 文件存储在 `steps/` 目录，可手动编辑或分享。

## 自定义知识库（可选）

`knowledge_base/` 目录存放 Markdown 格式的业务知识文档。RAG 系统会在每次解析指令前，从中检索相关内容注入提示词。

- `field_glossary.md` —— 字段定义和数据质量说明
- `business_rules.md` —— 业务规则和约束条件
- `calc_formulas.md` —— 指标定义和计算公式

**要添加你自己的业务知识**，在 `knowledge_base/` 中创建新的 `.md` 文件，然后在侧边栏点 **Rebuild KB**（或删除 `chroma_db/` 后重启）。

你也可以删除整个 `knowledge_base/` —— 系统不依赖它也能正常运行。RAG 是锦上添花，不是必需品。

## 项目结构

```
ExcelHelper/
├── server.py              # FastAPI 后端入口
├── agent.py               # LangChain: RAG → Deepseek → 步骤 JSON
├── executor.py            # Pandas 执行引擎（9 种操作）
├── recorder.py            # 步骤序列存取
├── prompts.py             # System prompt + few-shot 示例
├── knowledge.py           # RAG 向量库（Chroma）
├── excel_agent.html       # 浏览器界面
├── requirements.txt       # Python 依赖
├── .env.example           # API Key 配置模板
├── .gitignore
├── knowledge_base/        # 业务知识文档（可选）
│   ├── field_glossary.md
│   ├── business_rules.md
│   └── calc_formulas.md
├── data/                  # 上传的文件（gitignore）
├── steps/                 # 保存的步骤序列（JSON）
└── output/                # 生成的 Excel 文件（gitignore）
```

## 技术栈

| 层级 | 技术 |
|------|------|
| 界面 | 原生 HTML/CSS/JS（单页，无框架） |
| 后端 | FastAPI (Python) |
| LLM 编排 | LangChain (`ChatOpenAI` → Deepseek) |
| RAG | Chroma + HuggingFaceEmbeddings (`all-MiniLM-L6-v2`) |
| 数据处理 | Pandas + OpenPyXL |
| 前端文件解析 | SheetJS (xlsx) |
| 持久化 | JSON 文件（步骤序列）、Chroma SQLite（向量库） |

## License

MIT
