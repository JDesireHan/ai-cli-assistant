"""CLI 入口：交互式多轮对话。

运行方式：
    cd ai-cli-assistant
    pip install -r requirements.txt
    copy .env.example .env   （然后填入你的 API Key）
    python main.py
"""
from assistant import config
from assistant.loop import SYSTEM_PROMPT, chat_once, create_client
from assistant.tools import load_user_name


def build_system_prompt() -> str:
    """把用户档案里的名字作为「元信息」拼进 system prompt。

    为什么是 system prompt 而不是 user message：
    - 用户名是元信息，塞进 user message 会污染用户输入、每轮重复
    - 模型只看得见 messages 里的内容，光存文件不带进来等于没存
    """
    name = load_user_name()
    if not name:
        return SYSTEM_PROMPT
    return (
        f"{SYSTEM_PROMPT}\n\n"
        f"[用户元信息] 当前用户叫 {name}；用户问起自己名字时据此回答。"
    )


def main() -> None:
    if not config.validate():
        return

    client = create_client()

    # 会话级常量：/clear 清空历史时必须保留它，否则用户名会被一起清掉
    system_prompt = build_system_prompt()

    # 消息历史：多轮对话的本质就是把这个列表越滚越长发给 LLM
    messages = [{"role": "system", "content": system_prompt}]

    print("=" * 50)
    print("AI 命令行助手 (Week 1 项目 #1)")
    print(f"模型: {config.MODEL} | 输入 exit 退出, /clear 清空历史")
    print("=" * 50)

    while True:
        try:
            user_input = input("\n你：").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n再见！")
            break

        if not user_input:
            continue
        if user_input.lower() == "exit":
            print("再见！")
            break
        if user_input == "/clear":
            messages = [{"role": "system", "content": system_prompt}]
            print("（对话历史已清空）")
            continue

        messages.append({"role": "user", "content": user_input})
        messages = chat_once(client, messages)


if __name__ == "__main__":
    main()
