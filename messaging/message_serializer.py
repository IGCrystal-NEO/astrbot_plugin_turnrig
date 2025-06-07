"""
消息序列化与反序列化工具

由于AstrBot 3.0+的文件处理逻辑改变，在异步上下文中必须使用异步API获取文件，
请优先使用 async_serialize_message 和 async_compress_message 函数
以避免"不可以在异步上下文中同步等待下载"的警告
"""

import base64
import json
import os
from typing import Any

import astrbot.api.message_components as Comp
from astrbot.api import logger


def serialize_message(message: list[Comp.BaseMessageComponent]) -> list[dict[str, Any]]:
    """将消息组件列表序列化为可存储的格式（同步版本，有文件下载警告）

    Args:
        message: 消息组件列表

    Returns:
        List[Dict[str, Any]]: 可存储的序列化消息

    Warning:
        此函数可能导致"不可以在异步上下文中同步等待下载"警告
        建议使用 async_serialize_message 异步版本
    """
    serialized = []

    if not message:
        return serialized

    for msg in message:
        try:
            # 处理MFace特殊消息类型
            if (
                hasattr(msg, "raw_data")
                and isinstance(msg.raw_data, dict)
                and msg.raw_data.get("type") == "mface"
            ):
                mface_data = {"type": "mface", "data": msg.raw_data.get("data", {})}
                serialized.append(mface_data)
                logger.debug(f"序列化原始MFace数据: {mface_data}")
                continue

            # 识别文件上传通知事件
            if hasattr(msg, "notice_type") and msg.notice_type == "group_upload":
                file_data = getattr(msg, "file", {})  # 警告: 同步获取file
                file_info = {
                    "type": "notice",
                    "notice_type": "group_upload",
                    "file": {
                        "name": file_data.get("name", ""),
                        "size": file_data.get("size", 0),
                        "url": file_data.get("url", ""),
                        "busid": file_data.get("busid", ""),
                        "id": file_data.get("id", ""),
                    },
                }
                serialized.append(file_info)
                logger.info(f"序列化群文件上传通知: {file_info}")
                continue

            # 现有的消息类型处理
            if isinstance(msg, Comp.Plain):
                text = getattr(msg, "text", "") or ""
                if text.strip():
                    serialized.append({"type": "plain", "text": text})
                else:
                    logger.debug("跳过空Plain消息")
            elif isinstance(msg, Comp.Image):
                url = getattr(msg, "url", "") or ""
                file = getattr(msg, "file", "") or ""  # 警告: 同步获取file
                base64 = getattr(msg, "base64", "") or ""
                if url or file or base64:
                    serialized.append(
                        {"type": "image", "url": url, "file": file, "base64": base64}
                    )
                else:
                    logger.debug("跳过空Image消息")
            elif isinstance(msg, Comp.At):
                # 尝试从raw_data获取name信息
                name = getattr(msg, "name", "")
                qq = getattr(msg, "qq", "")

                # 调试：输出raw_data结构
                if hasattr(msg, "raw_data"):
                    logger.debug(f"At组件raw_data结构: {msg.raw_data}")

                # 如果name为空，尝试从raw_data中获取
                if (
                    not name
                    and hasattr(msg, "raw_data")
                    and isinstance(msg.raw_data, dict)
                ):
                    # 尝试多种可能的路径获取name
                    raw_name = msg.raw_data.get("data", {}).get("name", "")
                    if not raw_name:
                        # 直接从raw_data获取name
                        raw_name = msg.raw_data.get("name", "")

                    if raw_name:
                        name = raw_name
                        logger.info(f"从raw_data获取到At组件的name: {raw_name}")
                    else:
                        logger.debug(f"raw_data中未找到name信息: {msg.raw_data}")

                logger.debug(f"序列化At组件: qq={qq}, name='{name}'")
                serialized.append({"type": "at", "qq": qq, "name": name})
            elif isinstance(msg, Comp.Record):
                serialized.append(
                    {
                        "type": "record",
                        "url": getattr(msg, "url", ""),
                        "file": getattr(msg, "file", ""),
                    }
                )  # 警告: 同步获取file
            elif isinstance(msg, Comp.File):
                file_data = {
                    "type": "file",
                    "url": getattr(msg, "url", ""),
                    "name": getattr(msg, "name", ""),
                    "file": getattr(msg, "file", ""),  # 警告: 同步获取file
                    "size": getattr(msg, "size", 0),
                    "busid": getattr(msg, "busid", ""),
                }
                if hasattr(msg, "raw_data") and isinstance(msg.raw_data, dict):
                    for key, val in msg.raw_data.items():
                        if key not in file_data:
                            file_data[key] = val
                serialized.append(file_data)
            elif isinstance(msg, Comp.Reply):
                if hasattr(msg, "content") and msg.content:
                    node_content = [{"type": "plain", "text": msg.content}]
                else:
                    node_content = []

                serialized.append(
                    {
                        "type": "reply",
                        "data": {
                            "id": getattr(msg, "id", ""),
                            "seq": getattr(msg, "seq", 0),
                            "content": node_content,
                        },
                    }
                )
            elif isinstance(msg, Comp.Node):
                node_data = {
                    "name": getattr(msg, "name", ""),
                    "uin": getattr(msg, "uin", ""),
                    "content": [],
                    "seq": getattr(msg, "seq", ""),
                    "time": getattr(msg, "time", 0),
                }

                if hasattr(msg, "content") and isinstance(msg.content, list):
                    node_data["content"] = serialize_message(msg.content)

                serialized.append({"type": "node", "data": node_data})
            elif isinstance(msg, Comp.Face):
                serialized.append({"type": "face", "id": getattr(msg, "id", "")})
            else:
                data = {}
                for attr in ["text", "url", "id", "name", "uin", "content"]:
                    if hasattr(msg, attr):
                        value = getattr(msg, attr, None)
                        if value is not None:
                            data[attr] = value

                if not data:
                    continue

                data["original_type"] = str(type(msg))
                data["type"] = "unknown"
                serialized.append(data)
        except Exception as e:
            logger.warning(f"序列化消息组件失败: {e}")

    if not serialized:
        serialized.append({"type": "plain", "text": "[消息内容无法识别]"})

    return serialized


async def async_serialize_message(
    message: list[Comp.BaseMessageComponent],
) -> list[dict[str, Any]]:
    """将消息组件列表异步序列化为可存储的格式 - 修复异步文件获取问题

    Args:
        message: 消息组件列表

    Returns:
        List[Dict[str, Any]]: 可存储的序列化消息
    """
    serialized = []

    if not message:
        return serialized

    for msg in message:
        try:
            # 处理MFace特殊消息类型
            if (
                hasattr(msg, "raw_data")
                and isinstance(msg.raw_data, dict)
                and msg.raw_data.get("type") == "mface"
            ):
                mface_data = {"type": "mface", "data": msg.raw_data.get("data", {})}
                serialized.append(mface_data)
                logger.debug(f"序列化原始MFace数据: {mface_data}")
                continue

            # 识别文件上传通知事件
            if hasattr(msg, "notice_type") and msg.notice_type == "group_upload":
                # 异步获取文件数据
                file_data = {}
                if hasattr(msg, "get_file"):
                    try:
                        file_data = await msg.get_file()
                    except Exception as e:
                        logger.warning(f"异步获取文件数据失败: {e}")
                        file_data = {}

                file_info = {
                    "type": "notice",
                    "notice_type": "group_upload",
                    "file": {
                        "name": file_data.get("name", ""),
                        "size": file_data.get("size", 0),
                        "url": file_data.get("url", ""),
                        "busid": file_data.get("busid", ""),
                        "id": file_data.get("id", ""),
                    },
                }
                serialized.append(file_info)
                logger.info(f"序列化群文件上传通知: {file_info}")
                continue

            # 现有的消息类型处理 - 使用异步方法获取文件数据
            if isinstance(msg, Comp.Plain):
                text = getattr(msg, "text", "") or ""
                if text.strip():
                    serialized.append({"type": "plain", "text": text})
                else:
                    logger.debug("跳过空Plain消息")
            elif isinstance(msg, Comp.Image):
                url = getattr(msg, "url", "") or ""
                file = ""
                base64 = getattr(msg, "base64", "") or ""

                # 异步获取文件数据
                if hasattr(msg, "get_file"):
                    try:
                        file = await msg.get_file()
                        if file:
                            file = str(file)
                    except Exception as e:
                        logger.debug(f"异步获取Image文件数据失败: {e}")

                if url or file or base64:
                    serialized.append(
                        {"type": "image", "url": url, "file": file, "base64": base64}
                    )
                else:
                    logger.debug("跳过空Image消息")
            elif isinstance(msg, Comp.At):
                # 尝试从raw_data获取name信息
                name = getattr(msg, "name", "")
                qq = getattr(msg, "qq", "")

                # 如果name为空，尝试从raw_data中获取
                if (
                    not name
                    and hasattr(msg, "raw_data")
                    and isinstance(msg.raw_data, dict)
                ):
                    raw_name = msg.raw_data.get("data", {}).get("name", "")
                    if raw_name:
                        name = raw_name
                        logger.info(f"从raw_data获取到At组件的name: {raw_name}")

                logger.debug(f"异步序列化At组件: qq={qq}, name='{name}'")
                serialized.append({"type": "at", "qq": qq, "name": name})
            elif isinstance(msg, Comp.Record):
                url = getattr(msg, "url", "") or ""
                file = ""

                # 异步获取文件数据
                if hasattr(msg, "get_file"):
                    try:
                        file = await msg.get_file()
                        if file:
                            file = str(file)
                    except Exception as e:
                        logger.debug(f"异步获取Record文件数据失败: {e}")

                serialized.append({"type": "record", "url": url, "file": file})
            elif isinstance(msg, Comp.File):
                file_data = {
                    "type": "file",
                    "url": getattr(msg, "url", ""),
                    "name": getattr(msg, "name", ""),
                    "file": "",
                    "size": getattr(msg, "size", 0),
                    "busid": getattr(msg, "busid", ""),
                }

                # 异步获取文件数据
                if hasattr(msg, "get_file"):
                    try:
                        file = await msg.get_file()
                        if file:
                            file_data["file"] = str(file)
                    except Exception as e:
                        logger.debug(f"异步获取File文件数据失败: {e}")

                if hasattr(msg, "raw_data") and isinstance(msg.raw_data, dict):
                    for key, val in msg.raw_data.items():
                        if key not in file_data:
                            file_data[key] = val

                serialized.append(file_data)
            elif isinstance(msg, Comp.Reply):
                if hasattr(msg, "content") and msg.content:
                    node_content = [{"type": "plain", "text": msg.content}]
                else:
                    node_content = []

                serialized.append(
                    {
                        "type": "reply",
                        "data": {
                            "id": getattr(msg, "id", ""),
                            "seq": getattr(msg, "seq", 0),
                            "content": node_content,
                        },
                    }
                )
            elif isinstance(msg, Comp.Node):
                node_data = {
                    "name": getattr(msg, "name", ""),
                    "uin": getattr(msg, "uin", ""),
                    "content": [],
                    "seq": getattr(msg, "seq", ""),
                    "time": getattr(msg, "time", 0),
                }

                if hasattr(msg, "content") and isinstance(msg.content, list):
                    node_data["content"] = await async_serialize_message(
                        msg.content
                    )  # 递归使用异步版本

                serialized.append({"type": "node", "data": node_data})
            elif isinstance(msg, Comp.Face):
                serialized.append({"type": "face", "id": getattr(msg, "id", "")})
            else:
                data = {}
                for attr in ["text", "url", "id", "name", "uin", "content"]:
                    if hasattr(msg, attr):
                        value = getattr(msg, attr, None)
                        if value is not None:
                            data[attr] = value

                if not data:
                    continue

                data["original_type"] = str(type(msg))
                data["type"] = "unknown"
                serialized.append(data)
        except Exception as e:
            logger.warning(f"序列化消息组件失败: {e}")

    if not serialized:
        serialized.append({"type": "plain", "text": "[消息内容无法识别]"})

    return serialized


def deserialize_message(serialized: list[dict]) -> list[Comp.BaseMessageComponent]:
    """将序列化的消息反序列化为消息组件列表

    Args:
        serialized: 序列化的消息列表

    Returns:
        List[Comp.BaseMessageComponent]: 消息组件列表
    """
    components = []

    for msg in serialized:
        try:
            if msg["type"] == "plain":
                components.append(Comp.Plain(text=msg["text"]))
            elif msg["type"] == "image":
                if msg.get("base64"):
                    components.append(Comp.Image.frombase64(msg["base64"]))
                elif msg.get("file") and os.path.exists(msg["file"]):
                    components.append(Comp.Image.fromFileSystem(msg["file"]))
                else:
                    components.append(Comp.Image.fromURL(msg.get("url", "")))
            elif msg["type"] == "at":
                components.append(Comp.At(qq=msg["qq"], name=msg.get("name", "")))
            elif msg["type"] == "record":
                if msg.get("file") and os.path.exists(msg["file"]):
                    components.append(Comp.Record(file=msg["file"]))
                else:
                    components.append(Comp.Record(url=msg.get("url", "")))
            elif msg["type"] == "file":
                components.append(
                    Comp.File(
                        url=msg.get("url", ""),
                        name=msg.get("name", "未命名文件"),
                        file=msg.get("file", ""),
                    )
                )
            elif msg["type"] == "reply":
                components.append(
                    Comp.Reply(
                        id=msg["id"],
                        sender_id=msg.get("sender_id", ""),
                        sender_nickname=msg.get("sender_nickname", ""),
                        message_str=msg.get("message_str", ""),
                        text=msg.get("text", ""),
                    )
                )
            elif msg["type"] == "face":
                components.append(Comp.Face(id=msg["id"]))
            elif msg["type"] == "node":
                node_content = []
                if msg.get("content"):
                    node_content = deserialize_message(msg["content"])

                components.append(
                    Comp.Node(
                        name=msg.get("name", ""),
                        uin=msg.get("uin", ""),
                        content=node_content,
                        time=msg.get("time", 0),
                    )
                )
        except Exception as e:
            logger.error(f"反序列化消息组件失败: {e}, 消息数据: {msg}")
            components.append(
                Comp.Plain(text=f"[消息组件解析错误: {msg.get('type', '未知类型')}]")
            )
    return components


def compress_message(message: list[Comp.BaseMessageComponent]) -> str:
    """将消息序列化并压缩为base64字符串，减少存储空间（同步版本）

    Args:
        message: 消息组件列表

    Returns:
        str: 压缩后的base64字符串

    Warning:
        此函数可能导致"不可以在异步上下文中同步等待下载"警告
        建议使用 async_compress_message 异步版本
    """
    import zlib

    serialized = serialize_message(message)
    json_data = json.dumps(serialized)
    compressed = zlib.compress(json_data.encode("utf-8"))
    return base64.b64encode(compressed).decode("utf-8")


async def async_compress_message(message: list[Comp.BaseMessageComponent]) -> str:
    """将消息异步序列化并压缩为base64字符串，减少存储空间

    Args:
        message: 消息组件列表

    Returns:
        str: 压缩后的base64字符串
    """
    import zlib

    serialized = await async_serialize_message(message)
    json_data = json.dumps(serialized)
    compressed = zlib.compress(json_data.encode("utf-8"))
    return base64.b64encode(compressed).decode("utf-8")


def deserialize_message_compressed(
    compressed_data: str,
) -> list[Comp.BaseMessageComponent]:
    """从压缩的base64字符串反序列化消息

    Args:
        compressed_data: 压缩的base64字符串

    Returns:
        List[Comp.BaseMessageComponent]: 消息组件列表
    """
    import zlib

    try:
        decoded = base64.b64decode(compressed_data)
        decompressed = zlib.decompress(decoded)
        json_data = decompressed.decode("utf-8")
        serialized = json.loads(json_data)
        return deserialize_message(serialized)
    except Exception as e:
        logger.error(f"解压缩消息失败: {e}")
        return [Comp.Plain(text="[消息解析失败]")]


# 导出函数
__all__ = [
    "serialize_message",
    "async_serialize_message",
    "deserialize_message",
    "compress_message",
    "async_compress_message",
    "deserialize_message_compressed",
]
