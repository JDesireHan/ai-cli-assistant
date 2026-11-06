"""Agent 循环：整个 AI 应用的心脏。

一次完整的工具调用流程（务必读懂，面试会让你白板讲）：

    用户输入
      ↓
    把消息发给 LLM（附上工具清单）
      ↓
    LLM 返回两种可能：
      a) 直接回答 → 打印，结束本轮
      b) 要求调用工具 → 我们执行工具 → 结果追加进消息历史 → 回到上面
      ↓
    （循环上限 MAX_ITERATIONS，防止 LLM 死循环 —— 这本身就是
      Agent 安全设计，面试讲「Agent 失败模式」时的标准答案之一）
"""
from openai import OpenAI

from . import config
from .tools import TOOL_SCHEMAS, execute_tool

# 单轮对话最多工具调用次数（防死循环）
MAX_ITERATIONS = 5

SYSTEM_PROMPT = (
    "你是一个运行在命令行里的 AI 助手。"
    "你可以调用工具来获取时间、读取项目内文件。"
    "回答保持简洁；如果任务需要工具，先调用工具再回答。"
)


def create_client() -> OpenAI:
    return OpenAI(api_key=config.API_KEY, base_url=config.BASE_URL)


def chat_once(client: OpenAI, messages: list) -> list:
    """处理一轮对话（调用方已把用户消息追加进 messages），返回更新后的消息历史。"""

    for _ in range(MAX_ITERATIONS):

        resp = client.chat.completions.create(
            model=config.MODEL,
            messages=messages,
            tools=TOOL_SCHEMAS,
        )
        msg = resp.choices[0].message

        # 情况 a：LLM 直接回答，本轮结束
        if not msg.tool_calls:
            messages.append({"role": "assistant", "content": msg.content or ""})
            print(f"\n助手：{msg.content}\n")
            return messages

        # 情况 b：LLM 要求调用工具（可能一次要调好几个）
        #
        # 为什么要把 assistant 这条消息也 append 回去？——协议强制要求，不是可选风格：
        # 1. API 是无状态的：每次请求都要把「完整对话」重新发一遍，历史缺一条都不行。
        # 2. tool 结果消息必须靠 tool_call_id 找到「是哪次调用的结果」。
        #    如果历史里没有这条带 id 的 assistant 消息，下面 role="tool" 的消息就成了
        #    没有爹的孤儿，API 会直接返回 400 报错。
        # 3. arguments 是 JSON 字符串（不是字典），必须原样回传，不要 json.loads 后再塞回去。
        # 4. content 用 `or ""`：模型请求工具时 content 常为 null，而协议要求该字段存在。
        #
        # 为什么要用列表推导式？因为一次回复可能同时请求多个工具（并行调用），
        # 我们需要把 SDK 对象列表逐个转成「纯 dict」列表，才能放进 messages 发回去。
        messages.append(
            {
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in msg.tool_calls
                ],
            }
        )

        # 真正执行工具的是我们，不是 LLM
        for tc in msg.tool_calls:
            print(f"  [调用工具] {tc.function.name}({tc.function.arguments})")
            result = execute_tool(tc.function.name, tc.function.arguments)
            print(f"  [工具结果] {result[:100]}{'...' if len(result) > 100 else ''}")
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                }
            )
        # 工具结果已入列，继续循环让 LLM 看着结果继续说话

    print("\n警告：达到单轮工具调用上限，强制结束（防死循环机制生效）。")
    return messages
