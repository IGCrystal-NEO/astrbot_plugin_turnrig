"""
消息序列化与反序列化工具喵～ 📦

由于AstrBot 3.0+的文件处理逻辑改变喵，在异步上下文中必须使用异步API获取文件喵！
请优先使用 async_serialize_message 和 async_compress_message 函数喵～
以避免"不可以在异步上下文中同步等待下载"的警告喵！ ⚠️

这个小工具会帮你：
- 📦 序列化消息组件
- 🔄 反序列化消息内容
- 🗜️ 压缩和解压消息
- ✨ 处理各种消息类型

Note:
    建议使用异步版本避免警告喵！ 💡
"""

import base64
import json
import os
from typing import Any

import astrbot.api.message_components as Comp
from astrbot.api import logger

from .message_utils import fetch_forward_message_nodes


def serialize_message(message: list[Comp.BaseMessageComponent]) -> list[dict[str, Any]]:
    """
    将消息组件列表序列化为可存储的格式喵～ 📦
    （同步版本，有文件下载警告）

    Args:
        message: 消息组件列表喵

    Returns:
        可存储的序列化消息喵～

    Warning:
        此函数可能导致"不可以在异步上下文中同步等待下载"警告喵！ ⚠️
        建议使用 async_serialize_message 异步版本喵～
    """
    serialized = []

    # 空消息直接返回喵～ 📭
    if not message:
        return serialized

    # 一个一个处理消息组件喵～ 🔄
    for msg in message:
        try:
            # 处理MFace特殊消息类型喵～ 😸
            if (
                hasattr(msg, "raw_data")
                and isinstance(msg.raw_data, dict)
                and msg.raw_data.get("type") == "mface"
            ):
                mface_data = {"type": "mface", "data": msg.raw_data.get("data", {})}
                serialized.append(mface_data)
                logger.debug(f"序列化原始MFace数据喵: {mface_data} 😸")
                continue

            # 识别文件上传通知事件喵～ 📁
            if hasattr(msg, "notice_type") and msg.notice_type == "group_upload":
                file_data = getattr(msg, "file", {})  # 警告: 同步获取file喵 ⚠️
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
                logger.info(f"序列化群文件上传通知喵: {file_info} 📁")
                continue

            # 现有的消息类型处理喵～ 🔍
            if isinstance(msg, Comp.Plain):
                text = getattr(msg, "text", "") or ""
                if text.strip():
                    serialized.append({"type": "plain", "text": text})
                else:
                    logger.debug("跳过空Plain消息喵～ ⏭️")
            elif isinstance(msg, Comp.Image):
                url = getattr(msg, "url", "") or ""
                file = getattr(msg, "file", "") or ""  # 警告: 同步获取file喵 ⚠️
                base64 = getattr(msg, "base64", "") or ""
                if url or file or base64:
                    serialized.append(
                        {"type": "image", "url": url, "file": file, "base64": base64}
                    )
                else:
                    logger.debug("跳过空Image消息喵～ 🖼️")
            elif isinstance(msg, Comp.At):
                # 尝试从raw_data获取name信息喵～ 👤
                name = getattr(msg, "name", "")
                qq = getattr(msg, "qq", "")

                # 调试：输出raw_data结构喵～ 🔍
                if hasattr(msg, "raw_data"):
                    logger.debug(f"At组件raw_data结构喵: {msg.raw_data} 📋")

                # 如果name为空，尝试从raw_data中获取喵～ 🔍
                if (
                    not name
                    and hasattr(msg, "raw_data")
                    and isinstance(msg.raw_data, dict)
                ):
                    # 尝试多种可能的路径获取name喵～ 🔍
                    raw_name = msg.raw_data.get("data", {}).get("name", "")
                    if not raw_name:
                        # 直接从raw_data获取name喵～ 🔍
                        raw_name = msg.raw_data.get("name", "")

                    if raw_name:
                        name = raw_name
                        logger.info(f"从raw_data获取到At组件的name喵: {raw_name} ✅")
                    else:
                        logger.debug(f"raw_data中未找到name信息喵: {msg.raw_data} 😿")

                logger.debug(f"序列化At组件喵: qq={qq}, name='{name}' 👤")
                serialized.append({"type": "at", "qq": qq, "name": name})
            elif isinstance(msg, Comp.Record):
                serialized.append(
                    {
                        "type": "record",
                        "url": getattr(msg, "url", ""),
                        "file": getattr(msg, "file", ""),
                    }
                )  # 警告: 同步获取file喵 ⚠️
            elif isinstance(msg, Comp.Video):
                # 序列化视频组件喵～ 🎬
                video_url = getattr(msg, "url", "")
                video_file = getattr(msg, "file", "")  # 警告: 同步获取file喵 ⚠️
                logger.info(f"序列化视频组件喵: url={video_url}, file={video_file} 📹")
                serialized.append(
                    {
                        "type": "video",
                        "url": video_url,
                        "file": video_file,
                    }
                )
            elif isinstance(msg, Comp.File):
                file_data = {
                    "type": "file",
                    "url": getattr(msg, "url", ""),
                    "name": getattr(msg, "name", ""),
                    "file": getattr(msg, "file", ""),  # 警告: 同步获取file喵 ⚠️
                    "size": getattr(msg, "size", 0),
                    "busid": getattr(msg, "busid", ""),
                }
                # 从raw_data中获取额外信息喵～ 📋
                if hasattr(msg, "raw_data") and isinstance(msg.raw_data, dict):
                    for key, val in msg.raw_data.items():
                        if key not in file_data:
                            file_data[key] = val
                serialized.append(file_data)
            elif isinstance(msg, Comp.Reply):
                try:
                    if hasattr(msg, "content") and msg.content:
                        node_content = [{"type": "plain", "text": str(msg.content)}]
                    else:
                        node_content = []

                    # 安全地获取引用消息属性，优先从 raw_data 获取喵～ 🛡️
                    reply_id = getattr(msg, "id", "") or ""
                    reply_seq = getattr(msg, "seq", 0) or 0
                    sender_id = getattr(msg, "sender_id", "") or ""
                    sender_nickname = getattr(msg, "sender_nickname", "") or "未知用户"

                    # 如果基本属性为空，尝试从 raw_data 中获取喵～ 🔍
                    if (not reply_id or not sender_id) and hasattr(msg, "raw_data") and isinstance(msg.raw_data, dict):
                        raw_data = msg.raw_data.get("data", {})
                        if not reply_id:
                            reply_id = raw_data.get("id", "") or ""
                        if not sender_id:
                            sender_id = raw_data.get("qq", "") or ""
                        # 还可以尝试获取其他字段
                        if sender_nickname == "未知用户":
                            sender_nickname = raw_data.get("nickname", "") or "未知用户"

                    serialized.append(
                        {
                            "type": "reply",
                            "data": {
                                "id": str(reply_id),
                                "seq": int(reply_seq) if str(reply_seq).isdigit() else 0,
                                "content": node_content,
                                "sender_id": str(sender_id),
                                "sender_nickname": sender_nickname,
                            },
                        }
                    )
                    logger.debug(f"序列化引用消息喵: id={reply_id}, sender={sender_nickname}({sender_id}) 📨")
                except Exception as e:
                    logger.warning(f"序列化引用消息失败，使用简化格式喵: {e} ⚠️")
                    # 使用简化的引用消息格式喵～ 📝
                    serialized.append({
                        "type": "plain",
                        "text": "[引用消息 - 内容获取失败]"
                    })
            elif isinstance(msg, Comp.Node):
                node_data = {
                    "name": getattr(msg, "name", ""),
                    "uin": getattr(msg, "uin", ""),
                    "content": [],
                    "seq": getattr(msg, "seq", ""),
                    "time": getattr(msg, "time", 0),
                }

                # 递归处理节点内容喵～ 🔄
                if hasattr(msg, "content") and isinstance(msg.content, list):
                    node_data["content"] = serialize_message(msg.content)

                serialized.append({"type": "node", "data": node_data})
            elif isinstance(msg, Comp.Face):
                serialized.append({"type": "face", "id": getattr(msg, "id", "")})
            elif hasattr(msg, 'type') and str(getattr(msg, 'type', '')).lower() == 'forward':
                # 处理转发消息组件喵～ 📤
                forward_id = getattr(msg, "id", "")
                logger.info(f"检测到转发消息组件喵: id={forward_id} 📨")

                # 同步版本无法获取转发内容，使用简单表示喵～ 📝
                serialized.append({
                    "type": "plain",
                    "text": f"[转发消息: {forward_id[:20]}...]"
                })
            elif str(type(msg)).lower().find('forward') != -1:
                # 备用检测方法：通过类型名称检测Forward组件喵～ 🔍
                forward_id = getattr(msg, "id", "")
                logger.info(f"通过类型名称检测到转发消息组件喵: type={type(msg)}, id={forward_id} 📨")

                # 同步版本无法获取转发内容，使用简单表示喵～ 📝
                serialized.append({
                    "type": "plain",
                    "text": f"[转发消息: {forward_id[:20]}...]"
                })
            else:
                # 处理未知类型的消息喵～ ❓
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
            # 序列化过程中出错了喵！ 😿
            logger.warning(f"序列化消息组件失败喵: {e}")

    # 如果没有序列化任何内容，添加默认消息喵～ 📝
    if not serialized:
        serialized.append({"type": "plain", "text": "[消息内容无法识别喵]"})

    return serialized


async def async_serialize_message(
    message: list[Comp.BaseMessageComponent], event=None
) -> list[dict[str, Any]]:
    """
    将消息组件列表异步序列化为可存储的格式喵～ 📦✨
    修复异步文件获取问题的安全版本！

    Args:
        message: 消息组件列表喵
        event: 消息事件对象，用于获取转发消息内容喵

    Returns:
        可存储的序列化消息喵～

    Note:
        这是推荐使用的异步版本，避免同步获取文件的警告喵！ 💡
    """
    serialized = []

    if not message:
        return serialized

    for msg in message:
        try:
            # 处理MFace特殊消息类型喵～ 😸
            if (
                hasattr(msg, "raw_data")
                and isinstance(msg.raw_data, dict)
                and msg.raw_data.get("type") == "mface"
            ):
                mface_data = {"type": "mface", "data": msg.raw_data.get("data", {})}
                serialized.append(mface_data)
                logger.debug(f"序列化原始MFace数据喵: {mface_data} 😸")
                continue

            # 识别文件上传通知事件喵～ 📁
            if hasattr(msg, "notice_type") and msg.notice_type == "group_upload":
                # 异步获取文件数据
                file_data = {}
                if hasattr(msg, "get_file"):
                    try:
                        file_data = await msg.get_file()
                    except Exception as e:
                        logger.warning(f"异步获取文件数据失败喵: {e}")
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
                logger.info(f"序列化群文件上传通知喵: {file_info} 📁")
                continue

            # 现有的消息类型处理喵～ 🔍
            if isinstance(msg, Comp.Plain):
                text = getattr(msg, "text", "") or ""
                if text.strip():
                    serialized.append({"type": "plain", "text": text})
                else:
                    logger.debug("跳过空Plain消息喵～ ⏭️")
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
                        logger.debug(f"异步获取Image文件数据失败喵: {e}")

                if url or file or base64:
                    serialized.append(
                        {"type": "image", "url": url, "file": file, "base64": base64}
                    )
                else:
                    logger.debug("跳过空Image消息喵～ 🖼️")
            elif isinstance(msg, Comp.At):
                # 尝试从raw_data获取name信息喵～ 👤
                name = getattr(msg, "name", "")
                qq = getattr(msg, "qq", "")

                # 如果name为空，尝试从raw_data中获取喵～ 🔍
                if (
                    not name
                    and hasattr(msg, "raw_data")
                    and isinstance(msg.raw_data, dict)
                ):
                    raw_name = msg.raw_data.get("data", {}).get("name", "")
                    if raw_name:
                        name = raw_name
                        logger.info(f"从raw_data获取到At组件的name喵: {raw_name} ✅")

                logger.debug(f"异步序列化At组件喵: qq={qq}, name='{name}' 👤")
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
                        logger.debug(f"异步获取Record文件数据失败喵: {e}")

                serialized.append({"type": "record", "url": url, "file": file})
            elif isinstance(msg, Comp.Video):
                # 异步序列化视频组件喵～ 🎬
                video_url = getattr(msg, "url", "") or ""
                video_file = getattr(msg, "file", "") or ""  # 先获取file属性

                # 异步获取文件数据（如果有异步方法的话）
                if hasattr(msg, "get_file"):
                    try:
                        async_file = await msg.get_file()
                        if async_file:
                            video_file = str(async_file)
                    except Exception as e:
                        logger.debug(f"异步获取Video文件数据失败，使用同步属性喵: {e}")

                logger.info(f"异步序列化视频组件喵: url={video_url}, file={video_file} 📹")
                serialized.append({"type": "video", "url": video_url, "file": video_file})
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
                        logger.debug(f"异步获取File文件数据失败喵: {e}")

                if hasattr(msg, "raw_data") and isinstance(msg.raw_data, dict):
                    for key, val in msg.raw_data.items():
                        if key not in file_data:
                            file_data[key] = val

                serialized.append(file_data)
            elif isinstance(msg, Comp.Reply):
                try:
                    if hasattr(msg, "content") and msg.content:
                        node_content = [{"type": "plain", "text": str(msg.content)}]
                    else:
                        node_content = []

                    # 安全地获取引用消息属性，优先从 raw_data 获取喵～ 🛡️
                    reply_id = getattr(msg, "id", "") or ""
                    reply_seq = getattr(msg, "seq", 0) or 0
                    sender_id = getattr(msg, "sender_id", "") or ""
                    sender_nickname = getattr(msg, "sender_nickname", "") or "未知用户"

                    # 如果基本属性为空，尝试从 raw_data 中获取喵～ 🔍
                    if (not reply_id or not sender_id) and hasattr(msg, "raw_data") and isinstance(msg.raw_data, dict):
                        raw_data = msg.raw_data.get("data", {})
                        if not reply_id:
                            reply_id = raw_data.get("id", "") or ""
                        if not sender_id:
                            sender_id = raw_data.get("qq", "") or ""
                        # 还可以尝试获取其他字段
                        if sender_nickname == "未知用户":
                            sender_nickname = raw_data.get("nickname", "") or "未知用户"

                    serialized.append(
                        {
                            "type": "reply",
                            "data": {
                                "id": str(reply_id),
                                "seq": int(reply_seq) if str(reply_seq).isdigit() else 0,
                                "content": node_content,
                                "sender_id": str(sender_id),
                                "sender_nickname": sender_nickname,
                            },
                        }
                    )
                    logger.debug(f"异步序列化引用消息喵: id={reply_id}, sender={sender_nickname}({sender_id}) 📨")
                except Exception as e:
                    logger.warning(f"异步序列化引用消息失败，使用简化格式喵: {e} ⚠️")
                    # 使用简化的引用消息格式喵～ 📝
                    serialized.append({
                        "type": "plain",
                        "text": "[引用消息 - 内容获取失败]"
                    })
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
                        msg.content, event
                    )  # 递归使用异步版本，传递event

                serialized.append({"type": "node", "data": node_data})
            elif isinstance(msg, Comp.Face):
                serialized.append({"type": "face", "id": getattr(msg, "id", "")})
            elif hasattr(msg, '__class__') and 'Forward' in str(msg.__class__):
                # 处理转发消息组件喵～ 📤
                forward_id = getattr(msg, "id", "")
                logger.info(f"检测到Forward组件喵: id={forward_id} 📨")

                # 尝试获取转发消息的实际内容喵～ 🔍
                if event:
                    forward_nodes = await fetch_forward_message_nodes(forward_id, event)
                    if forward_nodes and len(forward_nodes) > 0:
                        logger.info(f"成功获取转发消息节点内容喵: {len(forward_nodes)} 个节点 ✅")
                        # 创建包含节点数据的转发消息标记喵～ 📋
                        serialized.append({
                            "type": "forward",
                            "id": forward_id,
                            "nodes": forward_nodes
                        })
                    else:
                        # 获取失败时使用简单的文本表示喵～ 📝
                        logger.warning(f"获取转发消息内容失败，使用简单表示喵: {forward_id} 😿")
                        serialized.append({
                            "type": "plain",
                            "text": f"[转发消息: {forward_id[:20]}...]"
                        })
                else:
                    # 没有event对象时使用简单的表示喵～ ⚠️
                    logger.warning(f"缺少event对象，无法获取转发消息内容喵: {forward_id} 😿")
                    serialized.append({
                        "type": "plain",
                        "text": f"[转发消息: {forward_id[:20]}...]"
                    })
            elif hasattr(msg, 'type') and str(getattr(msg, 'type', '')).lower() == 'forward':
                # 处理转发消息组件喵～ 📤
                forward_id = getattr(msg, "id", "")
                logger.info(f"检测到转发消息组件喵: id={forward_id} 📨")

                # 同步版本无法获取转发内容，使用简单表示喵～ 📝
                serialized.append({
                    "type": "plain",
                    "text": f"[转发消息: {forward_id[:20]}...]"
                })
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
            logger.warning(f"序列化消息组件失败喵: {e}")

    if not serialized:
        serialized.append({"type": "plain", "text": "[消息内容无法识别喵]"})

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
            elif msg["type"] == "forward":
                # 对于转发消息，创建一个简单的文本表示喵～ 📤
                forward_id = msg.get("id", msg.get("data", {}).get("id", "未知ID"))
                components.append(Comp.Plain(text=f"[转发消息: {forward_id}]"))
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
            logger.error(f"反序列化消息组件失败喵: {e}, 消息数据喵: {msg}")
            components.append(
                Comp.Plain(
                    text=f"[消息组件解析错误喵: {msg.get('type', '未知类型喵')}]"
                )
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


async def async_compress_message(message: list[Comp.BaseMessageComponent], event=None) -> str:
    """将消息异步序列化并压缩为base64字符串，减少存储空间

    Args:
        message: 消息组件列表
        event: 消息事件对象，用于获取转发消息内容喵

    Returns:
        str: 压缩后的base64字符串
    """
    import zlib

    serialized = await async_serialize_message(message, event)
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
        logger.error(f"解压缩消息失败喵: {e}")
        return [Comp.Plain(text="[消息解析失败喵]")]


# 导出函数
__all__ = [
    "serialize_message",
    "async_serialize_message",
    "deserialize_message",
    "compress_message",
    "async_compress_message",
    "deserialize_message_compressed",
]
