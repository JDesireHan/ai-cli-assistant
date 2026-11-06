"""工具注册表：AI 助手能「动手干活」的全部能力都在这里。

核心概念（面试必考）：
- LLM 本身只会生成文字，所谓「工具调用」是：LLM 输出一个结构化的
  函数名+参数 → 我们的代码真正执行这个函数 → 把结果喂回给 LLM。
- schema 是给 LLM 看的「说明书」，写得越清楚，调用越准。

Week 1 学习任务：读懂注册表模式，然后自己动手加一个新工具（见 TODO.md）。
"""
import datetime
from pathlib import Path
import json

# ==================== 工具实现（真正的 Python 函数） ====================


def get_current_time() -> str:
    """获取当前本地时间"""
    now = datetime.datetime.now()
    return now.strftime("%Y-%m-%d %H:%M:%S %A")


def read_local_file(path: str) -> str:
    """读取本项目目录内的文本文件。

    安全设计（也是面试加分点）：
    1. 限定只能读项目目录内的文件 —— 防止 LLM 幻觉出一个路径就越权访问
    2. 限制最多返回 5000 字符 —— 防止把上下文窗口撑爆
    """
    project_root = Path(__file__).resolve().parent.parent
    target = (project_root / path).resolve()

    if not str(target).startswith(str(project_root)):
        return "错误：出于安全考虑，只允许读取项目目录内的文件。"
    if not target.exists():
        return f"错误：文件不存在：{path}"
    try:
        content = target.read_text(encoding="utf-8")
        if len(content) > 5000:
            return content[:5000] + "\n...(内容过长，已截断)"
        return content
    except Exception as e:
        return f"读取失败：{e}"


def list_project_files(path: str = ".") -> str:

    """列出项目目录内所有的 .py 文件路径"""
    project_root = Path(__file__).resolve().parent.parent  # 获取项目根目录
    py_files = []  # 存储找到的 Python 文件相对路径

    # 遍历项目目录，查找所有 .py 文件
    for file_path in sorted(project_root.rglob("*.py")):
        # 排除 __pycache__ 目录下的文件
        if "__pycache__" in str(file_path):
            continue
        # 排除 .venv 目录下的文件
        if ".venv" in str(file_path):
            continue
        # 计算相对于项目根目录的路径
        relative_path = file_path.relative_to(project_root)
        py_files.append(str(relative_path))  # 添加到结果列表

    # 如果没有找到任何 Python 文件，返回提示信息
    if not py_files:
        return "未找到任何 .py 文件"

    # 将所有路径用换行符连接返回
    return "\n".join(py_files)


# ==================== 用户档案：记忆的应用层实现 ====================
#
# 面试要点：模型是无状态的，它什么都不「记住」。
# 所谓记忆 = 应用每次请求时，把持久化的数据重新塞进 messages 造出来的假象。
# 读写逻辑集中在本文件，main.py 只负责读出来注入 system prompt。

USER_PROFILE_FILE = Path(__file__).resolve().parent.parent / "user_profile.json"


def _read_profile() -> dict:
    """读取用户档案；文件不存在、JSON 损坏、类型异常都返回空档案，绝不抛异常。"""
    try:
        if not USER_PROFILE_FILE.exists():
            return {}
        data = json.loads(USER_PROFILE_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return {}


def load_user_name() -> str | None:
    """读取当前用户名；无记录返回 None，供 main.py 注入 system prompt。"""
    name = _read_profile().get("name")
    # isinstance + strip：脏数据不能污染 system prompt
    return name if isinstance(name, str) and name.strip() else None


def set_user_name(name: str) -> str:
    """工具实现：把用户名写入本地档案；换名时把旧名存入 historyname。

    约束（与 AGENTS.md 一致）：
    - 返回值必须是字符串，失败也返回错误字符串，不抛异常
    - historyname 去重，最多保留 10 条，防止无限增长
    """
    name = (name or "").strip()
    if not name:
        return "错误：名字不能为空。"

    profile = _read_profile()
    old_name = profile.get("name")
    history = profile.get("historyname", [])
    if not isinstance(history, list):
        history = []

    # 只有「旧名存在、且与新名不同、且没记过」时才追加，避免重复说同一名字刷屏
    if isinstance(old_name, str) and old_name and old_name != name and old_name not in history:
        history.append(old_name)

    profile["name"] = name
    profile["historyname"] = history[-10:]

    try:
        USER_PROFILE_FILE.write_text(
            json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except OSError as e:
        return f"保存失败：{e}"
    return f"已记住：当前用户叫 {name}。"


# ==================== 注册表：schema（给 LLM 看）+ fn（真正执行） ====================
#
# 新增一个工具只需两步：
#   1. 上面写一个函数
#   2. 在 TOOLS 列表里加一项（schema + fn）

TOOLS = [
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "get_current_time",
                "description": "获取当前的本地日期和时间。当用户询问时间、日期或需要时间上下文时调用。",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        },
        "fn": get_current_time,
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "read_local_file",
                "description": "读取本项目目录内指定路径的文本文件内容，如 README.md、TODO.md。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "相对于项目根目录的文件路径，例如 README.md 或 docs/notes.txt",
                        }
                    },
                    "required": ["path"],
                },
            },
        },
        "fn": read_local_file,
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "list_project_files",
                "description": "列出本项目内所有的 Python 源代码文件（.py），用于了解项目结构或查找文件。",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        },
        "fn": list_project_files,
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "set_user_name",
                "description": (
                    "当用户说出自己的名字、介绍自己是谁、要求改名时调用，"
                    "例如「我叫张三」「我是李四」「以后叫我小王」。"
                    "调用后把名字保存到本地档案，用于跨会话记住用户身份。"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "用户自称的名字"}
                    },
                    "required": ["name"],
                },
            },
        },
        "fn": set_user_name,
    },
]

# 给 API 用的 schema 列表（不含 fn，fn 不能序列化）
TOOL_SCHEMAS = [t["schema"] for t in TOOLS]

# 名字 -> 实现函数 的映射，用于执行
TOOL_IMPLS = {t["schema"]["function"]["name"]: t["fn"] for t in TOOLS}


def execute_tool(name: str, arguments_json: str) -> str:
    """执行一次工具调用，返回字符串结果。

    失败也要返回字符串（而不是抛异常）—— 把错误信息交给 LLM，
    让它自己决定重试还是换路，这是 Agent 容错的基本套路。
    """
    fn = TOOL_IMPLS.get(name)
    if fn is None:
        return f"错误：未知工具 {name}"
    try:
        args = arguments_json if arguments_json.strip() else "{}"
        kwargs = json.loads(args)
        return str(fn(**kwargs))
    except Exception as e:
        return f"工具执行出错：{e}"
