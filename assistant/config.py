"""配置加载：从 .env 读取 API Key 和模型配置。

为什么要单独一个文件？—— 把「密钥和模型选择」与「业务逻辑」分离，
是所有 AI 应用的第一课：换模型不改代码，密钥永远不进 Git。
"""
import os

from dotenv import load_dotenv

load_dotenv()

# API Key：从 .env 读取，绝不硬编码
API_KEY = os.getenv("LLM_API_KEY", "")

# Base URL：默认用 DeepSeek（国内便宜好用），换成其他兼容服务只改这一行
# 可选：https://api.deepseek.com | https://api.openai.com/v1 | https://api.moonshot.cn/v1
BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com")

# 模型名：DeepSeek 用 deepseek-chat，其他服务换成对应模型名
MODEL = os.getenv("LLM_MODEL", "deepseek-chat")


def validate() -> bool:
    """启动前检查配置是否齐全"""
    if not API_KEY:
        print("错误：未找到 LLM_API_KEY。")
        print("请复制 .env.example 为 .env，并填入你的 API Key。")
        return False
    return True
