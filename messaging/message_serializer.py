import os
import astrbot.api.message_components as Comp
from astrbot.api import logger

def serialize_message(message):
    """将消息序列化以便存储喵～"""
    serialized = []
    
    # 处理空消息的情况
    if not message:
        logger.warning("尝试序列化空消息")
        return [{"type": "plain", "text": "[空消息]"}]
        
    for msg in message:
        try:
            if isinstance(msg, Comp.Plain):
                # 确保文本非空
                text = getattr(msg, "text", "") or ""
                if text.strip():  # 只有当文本非空且非纯空白时才添加
                    serialized.append({"type": "plain", "text": text})
                else:
                    logger.debug("跳过空Plain消息")
            elif isinstance(msg, Comp.Image):
                # 确保至少有一个图片属性非空
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
                        # 如果内容是列表，递归序列化
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
                # 默认类型，尽可能保存所有属性
                data = {"type": "unknown"}
                if hasattr(msg, "type"):
                    data["original_type"] = msg.type
                else:
                    data["original_type"] = str(type(msg))
                    
                # 尝试保存消息对象的所有属性
                for attr_name in dir(msg):
                    if not attr_name.startswith("_") and not callable(getattr(msg, attr_name)):
                        try:
                            value = getattr(msg, attr_name)
                            # 只保存简单类型的属性
                            if isinstance(value, (str, int, float, bool)) or value is None:
                                data[attr_name] = value
                        except:
                            pass
                serialized.append(data)
        except Exception as e:
            logger.error(f"序列化消息组件时出错: {e}, 组件类型: {type(msg).__name__}")
            # 添加错误信息而不是跳过，确保消息链的完整性
            serialized.append({"type": "error", "error": str(e), "component_type": str(type(msg).__name__)})

    # 如果序列化后仍然为空，添加一个提示信息
    if not serialized:
        logger.warning("序列化后消息为空，添加默认消息")
        serialized.append({"type": "plain", "text": "[消息内容无法识别]"})
        
    return serialized

def deserialize_message(serialized):
    """将序列化的消息转换回消息组件喵～"""
    components = []
    for msg in serialized:
        try:
            if msg["type"] == "plain":
                components.append(Comp.Plain(text=msg["text"]))
            elif msg["type"] == "image":
                if msg.get("file"):
                    # 优先使用本地文件
                    if os.path.exists(msg["file"]):
                        components.append(Comp.Image.fromFileSystem(msg["file"]))
                    else:
                        # 文件不存在，尝试使用URL
                        components.append(Comp.Image.fromURL(msg.get("url", "")))
                elif msg.get("base64"):
                    # 使用base64
                    components.append(Comp.Image(base64=msg["base64"]))
                elif msg.get("url"):
                    # 使用URL
                    components.append(Comp.Image.fromURL(msg["url"]))
            elif msg["type"] == "at":
                components.append(Comp.At(qq=msg["qq"], name=msg.get("name", "")))
            elif msg["type"] == "record":
                if msg.get("file") and os.path.exists(msg["file"]):
                    components.append(Comp.Record(file=msg["file"]))
                else:
                    components.append(Comp.Record(url=msg["url", ""]))
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
                # 处理Node的内容
                node_content = []
                if msg.get("content"):
                    # 如果内容是序列化的消息列表，递归反序列化
                    node_content = deserialize_message(msg["content"])
                
                components.append(Comp.Node(
                    name=msg.get("name", ""),
                    uin=msg.get("uin", ""),
                    content=node_content,
                    time=msg.get("time", 0)
                ))
            elif msg["type"] == "nodes":
                # 处理Nodes
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
                components.append(Comp.Nodes(nodes=nodes_list))  # 修复这里，返回 Comp.Nodes 对象
        except Exception as e:
            logger.error(f"反序列化消息组件失败: {e}, 消息数据: {msg}")
            # 添加一个文本消息表明有错误
            components.append(Comp.Plain(text=f"[消息组件解析错误: {msg.get('type', '未知类型')}]"))
    return components