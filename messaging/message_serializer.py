import os
import base64
import json
from typing import List, Dict, Any, Union
import astrbot.api.message_components as Comp
from astrbot.api import logger

def serialize_message(message: List[Comp.BaseMessageComponent]) -> List[Dict[str, Any]]:
    """将消息组件列表序列化为可存储的格式
    
    Args:
        message: 消息组件列表
        
    Returns:
        List[Dict[str, Any]]: 可存储的序列化消息
    """
    serialized = []
    
    if not message:
        logger.warning("尝试序列化空消息")
        return [{"type": "plain", "text": "[空消息]"}]
        
    for msg in message:
        try:
            # 检查是否为MFace特殊表情类型
            # 方法1: 通过类名检测
            if type(msg).__name__ == 'MFace' or hasattr(msg, 'type') and getattr(msg, 'type') == 'mface':
                # 提取MFace特殊表情的关键数据
                mface_data = {
                    "type": "mface",
                    "url": getattr(msg, "url", ""),
                    "emoji_id": getattr(msg, "emoji_id", ""),
                    "emoji_package_id": getattr(msg, "emoji_package_id", ""),
                    "summary": getattr(msg, "summary", "[表情]")
                }
                
                # 处理可能位于data字段中的数据
                if hasattr(msg, "data") and isinstance(msg.data, dict):
                    for key, value in msg.data.items():
                        if key not in mface_data or not mface_data[key]:
                            mface_data[key] = value
                
                serialized.append(mface_data)
                logger.debug(f"序列化MFace特殊表情: {mface_data}")
                continue
                
            # 方法2: 检查原始消息字典数据
            if hasattr(msg, "raw_data") and isinstance(msg.raw_data, dict) and msg.raw_data.get("type") == "mface":
                mface_data = {
                    "type": "mface",
                    "data": msg.raw_data.get("data", {})
                }
                serialized.append(mface_data)
                logger.debug(f"序列化原始MFace数据: {mface_data}")
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
                file = getattr(msg, "file", "") or ""
                base64 = getattr(msg, "base64", "") or ""
                
                if url or file or base64:
                    serialized.append({
                        "type": "image", 
                        "url": url, 
                        "file": file, 
                        "base64": base64
                    })
                else:
                    logger.debug("跳过空Image消息")
            elif isinstance(msg, Comp.At):
                serialized.append({"type": "at", "qq": getattr(msg, "qq", ""), "name": getattr(msg, "name", "")})
            elif isinstance(msg, Comp.Record):
                serialized.append({"type": "record", "url": getattr(msg, "url", ""), "file": getattr(msg, "file", "")})
            elif isinstance(msg, Comp.File):
                serialized.append({
                    "type": "file", 
                    "url": getattr(msg, "url", ""), 
                    "name": getattr(msg, "name", ""), 
                    "file": getattr(msg, "file", "")
                })
            elif isinstance(msg, Comp.Reply):
                serialized.append({
                    "type": "reply", 
                    "id": getattr(msg, "id", ""),
                    "sender_id": getattr(msg, "sender_id", ""),
                    "sender_nickname": getattr(msg, "sender_nickname", ""),
                    "message_str": getattr(msg, "message_str", ""),
                    "text": getattr(msg, "text", "")
                })
            elif isinstance(msg, Comp.Forward):
                serialized.append({"type": "forward", "id": getattr(msg, "id", "")})
            elif isinstance(msg, Comp.Node):
                node_content = []
                if hasattr(msg, "content"):
                    if isinstance(msg.content, list):
                        node_content = serialize_message(msg.content)
                    elif isinstance(msg.content, str):
                        node_content = [{"type": "plain", "text": msg.content}]
                
                serialized.append({
                    "type": "node", 
                    "name": getattr(msg, "name", ""),
                    "uin": getattr(msg, "uin", ""),
                    "content": node_content,
                    "time": getattr(msg, "time", 0)
                })
            elif isinstance(msg, Comp.Nodes):
                nodes_list = []
                if hasattr(msg, "nodes") and msg.nodes:
                    for node in msg.nodes:
                        node_data = {
                            "type": "node", 
                            "name": getattr(node, "name", ""),
                            "uin": getattr(node, "uin", ""),
                            "content": serialize_message(node.content) if hasattr(node, "content") and isinstance(node.content, list) else [],
                            "time": getattr(node, "time", 0)
                        }
                        nodes_list.append(node_data)
                serialized.append({"type": "nodes", "nodes": nodes_list})
            elif isinstance(msg, Comp.Face):
                serialized.append({"type": "face", "id": getattr(msg, "id", 0)})
            elif isinstance(msg, Comp.Video):
                serialized.append({
                    "type": "video", 
                    "file": getattr(msg, "file", ""),
                    "url": getattr(msg, "url", ""),
                    "cover": getattr(msg, "cover", "")
                })
            else:
                # 尝试检查是否为mface消息 - 通过更多方式识别
                if hasattr(msg, '__dict__') and any(key in msg.__dict__ for key in ['emoji_id', 'emoji_package_id']):
                    mface_data = {
                        "type": "mface",
                        "summary": getattr(msg, "summary", "[表情]"),
                        "url": getattr(msg, "url", ""),
                    }
                    for key in ['emoji_id', 'emoji_package_id', 'key']:
                        if hasattr(msg, key):
                            mface_data[key] = getattr(msg, key)
                    serialized.append(mface_data)
                    logger.debug(f"通过字段识别并序列化MFace: {mface_data}")
                    continue
                
                # 通用未知类型处理
                data = {"type": "unknown"}
                if hasattr(msg, "type"):
                    data["original_type"] = msg.type
                else:
                    data["original_type"] = str(type(msg))
                    
                for attr_name in dir(msg):
                    if not attr_name.startswith("_") and not callable(getattr(msg, attr_name)):
                        try:
                            value = getattr(msg, attr_name)
                            if isinstance(value, (str, int, float, bool)) or value is None:
                                data[attr_name] = value
                        except:
                            pass
                serialized.append(data)
        except Exception as e:
            logger.error(f"序列化消息组件时出错: {e}, 组件类型: {type(msg).__name__}")
            serialized.append({"type": "error", "error": str(e), "component_type": str(type(msg).__name__)})

    if not serialized:
        logger.warning("序列化后消息为空，添加默认消息")
        serialized.append({"type": "plain", "text": "[消息内容无法识别]"})
        
    return serialized

def deserialize_message(serialized: List[Dict]) -> List[Comp.BaseMessageComponent]:
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
                    components.append(Comp.Image(base64=msg["base64"]))
                elif msg.get("file") and os.path.exists(msg["file"]):
                    components.append(Comp.Image.fromFileSystem(msg["file"]))
                elif msg.get("url"):
                    components.append(Comp.Image.fromURL(msg["url"]))
                else:
                    logger.warning(f"图片缺少有效的源: {msg}")
                    components.append(Comp.Plain(text="[图片无法显示]"))
            elif msg["type"] == "at":
                components.append(Comp.At(qq=msg["qq"], name=msg.get("name", "")))
            elif msg["type"] == "record":
                if msg.get("file") and os.path.exists(msg["file"]):
                    components.append(Comp.Record(file=msg["file"]))
                else:
                    components.append(Comp.Record(url=msg.get("url", "")))
            elif msg["type"] == "file":
                components.append(Comp.File(
                    url=msg.get("url", ""),
                    name=msg.get("name", "未命名文件"),
                    file=msg.get("file", "")
                ))
            elif msg["type"] == "reply":
                components.append(Comp.Reply(
                    id=msg["id"],
                    sender_id=msg.get("sender_id", ""),
                    sender_nickname=msg.get("sender_nickname", ""),
                    message_str=msg.get("message_str", ""),
                    text=msg.get("text", "")
                ))
            elif msg["type"] == "face":
                components.append(Comp.Face(id=msg["id"]))
            elif msg["type"] == "video":
                if msg.get("file") and os.path.exists(msg["file"]):
                    components.append(Comp.Video.fromFileSystem(msg["file"]))
                else:
                    components.append(Comp.Video.fromURL(msg["url"]))
            elif msg["type"] == "node":
                node_content = []
                if msg.get("content"):
                    node_content = deserialize_message(msg["content"])
                
                components.append(Comp.Node(
                    name=msg.get("name", ""),
                    uin=msg.get("uin", ""),
                    content=node_content,
                    time=msg.get("time", 0)
                ))
            elif msg["type"] == "nodes":
                nodes_list = []
                for node_data in msg.get("nodes", []):
                    node_content = []
                    if node_data.get("content"):
                        node_content = deserialize_message(node_data["content"])
                    
                    node = Comp.Node(
                        name=node_data.get("name", ""),
                        uin=node_data.get("uin", ""),
                        content=node_content,
                        time=node_data.get("time", 0)
                    )
                    nodes_list.append(node)
                components.append(Comp.Nodes(nodes=nodes_list))
        except Exception as e:
            logger.error(f"反序列化消息组件失败: {e}, 消息数据: {msg}")
            components.append(Comp.Plain(text=f"[消息组件解析错误: {msg.get('type', '未知类型')}]"))
    return components

def serialize_message_compressed(message: List[Comp.BaseMessageComponent]) -> str:
    """将消息序列化并压缩为base64字符串，减少存储空间
    
    Args:
        message: 消息组件列表
        
    Returns:
        str: base64编码的压缩消息数据
    """
    import zlib
    
    serialized_data = serialize_message(message)
    json_data = json.dumps(serialized_data, ensure_ascii=False)
    compressed = zlib.compress(json_data.encode('utf-8'))
    return base64.b64encode(compressed).decode('utf-8')

def deserialize_message_compressed(compressed_data: str) -> List[Comp.BaseMessageComponent]:
    """从压缩的base64字符串反序列化消息
    
    Args:
        compressed_data: 压缩的base64字符串
        
    Returns:
        List[Comp.BaseMessageComponent]: 消息组件列表
    """
    import zlib
    
    try:
        compressed_bytes = base64.b64decode(compressed_data)
        json_data = zlib.decompress(compressed_bytes).decode('utf-8')
        serialized_data = json.loads(json_data)
        return deserialize_message(serialized_data)
    except Exception as e:
        logger.error(f"解压缩消息失败: {e}")
        return [Comp.Plain(text="[消息解压缩失败]")]