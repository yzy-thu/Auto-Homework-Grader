[English](./README.md) | **中文**

# 自动批改系统

基于网页的自动作业批改应用。上传标准答案（图片/PDF）和学生作业（文件夹路径或 ZIP 上传），系统自动识别内容（PDF/Markdown/图片），调用 Gemini API 进行比对打分（5 并发），实时展示进度，支持中途暂停，最终输出 CSV 成绩表。

## 技术栈

- **前端**：Vue 3 + Vite
- **后端**：Python Flask
- **AI**：Google Gemini API
- **通信**：SSE（Server-Sent Events）实时进度推送，支持断线自动重连

## 快速开始

### 1. 安装依赖

```bash
# 后端
cd backend
pip install -r requirements.txt

# 前端
cd frontend
npm install
```

### 2. 配置 API Key

编辑 `backend/.env`，填入你的 Gemini API Key：

```
GEMINI_API_KEY=your_api_key_here
```

### 3. 启动服务

```bash
# 终端 1 — 启动后端（端口 5001）
cd backend
python app.py

# 终端 2 — 启动前端（端口 3000）
cd frontend
npm run dev
```

打开浏览器访问 `http://localhost:3000`。

## 使用流程

1. **上传标准答案**：拖拽文件到上传区域，或点击 "Browse Files" 按钮选择文件（支持图片和 PDF）
2. **指定学生作业**：两种方式可选
   - **Folder Path**：输入包含学生作业的文件夹绝对路径
   - **Upload ZIP**：拖拽或选择包含所有学生作业的 ZIP 文件上传
3. **设置评分规则**：在文本框中描述评分标准（如总分、扣分规则等）
4. **开始批改**：点击 "Start Grading"，系统以 5 并发自动处理每个学生的作业
5. **查看进度**：实时查看批改进度条和日志输出
6. **暂停（可选）**：点击 "Stop" 按钮可中途暂停，已批改的结果会保留并可导出
7. **下载结果**：批改完成（或暂停）后，点击 "Download CSV" 下载成绩表

## 学生提交文件命名

学生文件夹中可以混合包含 ZIP 文件和直接的 PDF/图片文件，系统会统一处理。

### 智能文件名解析

系统采用两级策略从文件名中提取学生信息：

1. **默认规则**（不调用 Gemini）：识别 `学号_姓名_随机数.ext` 格式
   - 例如：`2024001_张三_12345.zip`、`2020080089_钱致中_1920.pdf`
   - 当 ≥80% 的文件符合此格式时自动使用

2. **Gemini 智能解析**（自动降级）：当大部分文件名不符合默认格式时，调用一次 Gemini 分析所有文件名，自动识别字段结构（如学号、姓名、班级、日期等任意组合）

### 动态 CSV 列

CSV 输出的列由文件名解析结果决定，前面是解析出的元数据列，**分数（Score）和反馈（Feedback）始终为最后两列**。例如：

| 学号 | 姓名 | 分数 | 反馈 | 错误信息 |
|------|------|------|------|----------|
| 2024001 | 张三 | 95 | 解答完整... | |

## 支持的文件格式

- **图片**：PNG、JPG、JPEG、GIF、BMP、WebP
- **文档**：PDF、Markdown（.md）、TXT

## API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/upload-answers` | POST | 上传标准答案文件，返回 `session_id` |
| `/api/upload-submissions` | POST | 上传学生作业 ZIP，解压后返回文件夹路径 |
| `/api/grade` | POST | 启动批改任务（5 并发），返回 `job_id` |
| `/api/grade/stream?job_id=` | GET | SSE 流，推送实时进度（支持断线重连） |
| `/api/grade/stop` | POST | 暂停批改任务，保留已完成结果 |
| `/api/download?job_id=` | GET | 下载 CSV 成绩文件（完成或暂停后均可） |

## 错误处理

- 损坏的 ZIP 文件：跳过并记录错误，继续下一个学生
- 无作业文件：记录提示，继续下一个学生
- Gemini API 错误：自动重试最多 5 次，指数退避（2s → 4s → 8s → 16s → 32s），覆盖限流、服务端错误、网络超时等
- 文件过大：跳过超过 20MB 的单个文件
- 嵌套 ZIP：自动递归解压（深度限制 2 层）
- SSE 断线：前端自动重连，后端回放错过的事件，不丢数据

## 项目结构

```
num_analysis/
├── backend/
│   ├── app.py                 # Flask 入口（端口 5001）
│   ├── config.py              # 配置（环境变量、路径、模型名）
│   ├── requirements.txt       # Python 依赖
│   ├── .env                   # GEMINI_API_KEY
│   ├── services/
│   │   ├── zip_extractor.py   # ZIP 解压 + 中文编码处理（UTF-8/GBK）
│   │   ├── file_processor.py  # 文件检测 + 转 Gemini Part
│   │   ├── gemini_grader.py   # Gemini 打分 + 文件名解析 + 自动重试
│   │   └── csv_exporter.py    # CSV 生成（动态列 + UTF-8 BOM）
│   ├── routes/
│   │   ├── grading.py         # 批改相关接口（并行打分 + 暂停）
│   │   └── upload.py          # 答案上传 + 作业 ZIP 上传接口
│   └── utils/
│       └── sse.py             # SSE 格式化工具（含事件 ID）
├── frontend/
│   ├── package.json
│   ├── vite.config.js         # 代理到 Flask 5001 端口
│   ├── index.html
│   └── src/
│       ├── main.js
│       ├── App.vue
│       ├── components/
│       │   ├── GradingForm.vue     # 输入表单（拖拽/选择上传）
│       │   ├── ProgressTracker.vue # 进度条 + 实时日志 + 暂停按钮
│       │   └── ResultsTable.vue    # 动态列成绩表格 + CSV 下载
│       ├── composables/
│       │   ├── useGrading.js       # SSE 连接 + 状态管理 + 暂停
│       │   └── useFileUpload.js    # 文件上传逻辑（含进度条）
│       └── assets/
│           └── style.css
└── .gitignore
```
