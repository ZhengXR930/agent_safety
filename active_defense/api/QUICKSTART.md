# 🚀 快速入门指南

---

## 🎯 第一步：运行示例（推荐）

项目包含一个完整的示例 `main.py`，展示了流式响应的日志记录。

### 1. 配置你的 API

编辑 `main.py` 文件，修改 API 配置：

```python
# API 配置
API_URL = "https://yunwu.ai/v1/chat/completions"  # 你的 API 地址
API_KEY = "sk-your-api-key-here"                          # 你的 API Key
MODEL = "claude-sonnet-4-20250514"                        # 你使用的模型
```

### 2. 运行示例

```bash
python main.py
```

### 3. 查看输出

你会看到：
```
发送流式请求...
注意：包装器会自动添加 stream_options 以获取 token 统计

--------------------------------------------------------------------------------
✓ 流式响应完成！
[响应内容显示在这里]
✓ 日志已自动记录（包含完整的 token 统计）

================================================================================
查看刚才的流式调用记录
================================================================================
[显示详细的调用统计，包括 token 数量、耗时等]
```

**完成！** 日志已自动保存到 `api_logs/` 目录。

---

## 💡 main.py 做了什么？

让我们看看 `main.py` 的核心代码（已简化）：

```python
from local_api_logger import wrap_requests_call, print_recent_calls

# 1️⃣ 准备请求参数
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}

payload = {
    "model": MODEL,
    "messages": [{"role": "user", "content": "数从1到10"}],
    "stream": True  # 开启流式响应
}

# 2️⃣ 使用包装器发送请求（自动记录日志）
stream = wrap_requests_call(
    model=MODEL,
    url=API_URL,
    headers=headers,
    payload=payload,
    user="stream_user",  # 可选：用户标识
    verify=False         # 可选：SSL 验证
)

# 3️⃣ 处理流式响应
for line in stream:
    # 逐行处理流式数据
    print(line, end='', flush=True)

# 4️⃣ 查看调用记录
print_recent_calls(model=MODEL, limit=1)
```

**关键点：**
- ✅ 使用 `wrap_requests_call` 替代 `requests.post`
- ✅ 流式响应自动处理，日志自动记录
- ✅ Token 统计自动提取（包装器会添加 `stream_options`）
- ✅ 可以立即查看统计数据

---

## 📝 第二步：集成到你的代码

理解了 `main.py` 后，你可以轻松集成到自己的代码中。

```bash
# 将库复制到你的项目目录
cp -r local_api_logger /path/to/your/project/
```

### 方式 1：流式响应（如 main.py）

```python
from local_api_logger import wrap_requests_call

# 流式请求
payload = {
    "model": "claude-3-opus",
    "messages": [{"role": "user", "content": "你好"}],
    "stream": True
}

# 自动处理流式响应并记录日志
stream = wrap_requests_call(
    model="claude-3-opus",
    url=API_URL,
    headers=headers,
    payload=payload,
    user="my_app"
)

# 逐块输出
for chunk in stream:
    print(chunk, end='', flush=True)

# 日志已自动记录！
```

### 方式 2：手动记录（最灵活）

如果你已经有现成的 API 调用代码：

```python
from local_api_logger import log_completion
import requests

# 你原有的代码
response = requests.post(API_URL, headers=headers, json=payload).json()

# 添加一行代码记录日志 ✨
log_completion(
    model="claude-3-opus",
    request_data=payload,
    response_data=response,  # 必须包含 usage 字段
    user="my_app"
)
```

---

## 📊 第三步：查看统计

### 查看最近的调用

```python
from local_api_logger import print_recent_calls

# 查看最近 5 次调用
print_recent_calls(limit=5)

# 仅查看特定模型
print_recent_calls(model="claude-sonnet-4-20250514", limit=10)
```

**输出示例：**
```
================================================================================
最近的 API 调用记录
================================================================================

[1] 2025-10-21 10:30:45 | claude-sonnet-4-20250514 | stream_user
    输入 tokens: 50 | 输出 tokens: 100 | 总计: 150
    耗时: 1234ms | 状态: ✓ 成功
```

### 查看统计摘要

```python
from local_api_logger import print_stats_summary

# 查看所有统计
print_stats_summary()

# 仅查看特定模型
print_stats_summary(model="claude-sonnet-4-20250514")

# 仅查看特定月份
print_stats_summary(month="2025-10")
```

**输出示例：**
```
================================================================================
API 调用统计摘要
================================================================================

总调用次数: 10
总输入 Tokens: 500
总输出 Tokens: 1,200
总 Tokens: 1,700

按模型统计:
--------------------------------------------------------------------------------
claude-sonnet-4-20250514: 调用 10 次, 输入 500, 输出 1,200, 总计 1,700 tokens
```

### 导出为 CSV

```python
from local_api_logger import export_to_csv

# 导出所有数据
export_to_csv("api_stats.csv")

# 导出特定月份
export_to_csv("october_stats.csv", month="2025-10")

# 导出特定模型
export_to_csv("claude_stats.csv", model="claude-sonnet-4-20250514")
```

---

## 📁 日志存储位置

运行 `main.py` 后，日志会自动保存在：

```
api_logs/
├── calls/                                    # 完整调用记录
│   └── claude-sonnet-4-20250514/            # 按模型分类
│       └── 2025-10/                         # 按月归档
│           └── 2025-10-21.jsonl             # 按日存储
└── stats/                                    # 统计记录（轻量）
    └── claude-sonnet-4-20250514/            # 按模型分类
        └── stream_user_2025-10.jsonl        # 按用户+月存储
```

**查看日志文件：**
```bash
# 查看完整调用记录
cat api_logs/calls/claude-sonnet-4-20250514/2025-10/2025-10-21.jsonl

# 查看统计记录
cat api_logs/stats/claude-sonnet-4-20250514/stream_user_2025-10.jsonl
```

---

## ⚙️ 自定义配置

### 修改日志目录

```python
from local_api_logger import set_log_dir

# 在使用其他功能之前设置
set_log_dir("/custom/path/to/logs")
```

### 禁用 SSL 验证

```python
# 在 wrap_requests_call 中添加 verify=False
stream = wrap_requests_call(
    model=MODEL,
    url=API_URL,
    headers=headers,
    payload=payload,
    verify=False
)
```

---

## ❓ 常见问题

### Q: 如何修改 main.py 用于我的 API？

A: 只需修改这三个配置：
```python
API_URL = "你的API地址"
API_KEY = "你的API密钥"
MODEL = "你使用的模型名"
```

### Q: 我的 API 不支持流式响应怎么办？

A: 将 `main.py` 中的 `"stream": True` 改为 `"stream": False`，其他代码保持不变。

### Q: Token 统计准确吗？

A: 非常准确！包装器会自动添加 `stream_options: {"include_usage": True}` 参数，从服务商返回的数据中提取精确的 token 统计。

### Q: 日志会很大吗？

A: 不会。统计日志（stats/）非常轻量，只包含 token 数量和时长。完整日志（calls/）包含请求和响应，但按日期分文件存储，方便定期清理。

---

**开始使用 Local API Logger，享受简单高效的 API 调用追踪！** 🚀
