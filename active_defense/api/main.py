from local_api_logger import wrap_requests_call
import json
import time

# API 配置
API_URL = "https://yunwu.ai/v1/chat/completions"
API_KEY = "sk-K5tm4pV*********nc2JEP"
MODEL = "claude-sonnet-4-20250514"

def collect_stream_data(stream_generator):
    """Collect reasoning and content from SSE stream generator"""
    reasoning_parts, content_parts = [], []

    for line in stream_generator:
        # 生成器已经返回了包含换行符的行，需要去除空白
        line = line.strip()

        if not line or not line.startswith('data: '):
            continue

        data = line[6:].strip()
        if data == '[DONE]':
            continue

        try:
            parsed = json.loads(data)

            # 安全检查 choices 数组
            if not parsed.get('choices') or len(parsed['choices']) == 0:
                continue

            delta = parsed['choices'][0].get('delta', {})

            if reasoning := delta.get('reasoning_content'):
                reasoning_parts.append(reasoning)

            if content := delta.get('content'):
                content_parts.append(content)
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            # 调试：打印解析失败的数据
            print(f"解析失败: {e}, 数据: {data[:100]}")
            continue

    return ''.join(reasoning_parts), ''.join(content_parts)

def main():
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": "数从1到10"
            }
        ],
        "stream": True  # 开启流式响应
    }

    print("\n发送流式请求...")
    print("注意：包装器会自动添加 stream_options 以获取 token 统计\n")

    reasoning_parts = []
    content_parts = []

    try:
        # 使用包装器处理流式响应
        # 它会返回一个生成器
        stream = wrap_requests_call(
            model=MODEL,
            url=API_URL,
            headers=headers,
            payload=payload,
            user="data",
            verify=False
        )

        reasoning_parts, content_parts = collect_stream_data(stream)

        print("-" * 80)
        print("\n✓ 流式响应完成！")
        print(reasoning_parts, content_parts)
        print("✓ 日志已自动记录（包含完整的 token 统计）")

    except Exception as e:
        print(f"✗ 请求失败: {e}")
        import traceback
        traceback.print_exc()

    # 等待日志写入
    time.sleep(0.2)

    # 查看统计
    from local_api_logger import print_recent_calls

    print("\n" + "=" * 80)
    print("查看刚才的流式调用记录")
    print("=" * 80)
    print_recent_calls(model=MODEL, limit=1)


if __name__ == "__main__":
    main()
    
    # 查看所有统计
    time.sleep(0.5)
    from local_api_logger import print_stats_summary
    print_stats_summary()
