import os
import asyncio
import json
import traceback
import base64
from typing import Dict, List, Any
from astrbot.api import logger
from astrbot.api.message_components import Plain, Image

class MessageSender:
    """消息发送器，负责处理消息的发送"""
    
    def __init__(self, plugin, download_helper):
        self.plugin = plugin
        self.download_helper = download_helper
    
    async def send_forward_message_via_api(self, target_session: str, nodes_list: List[Dict]) -> bool:
        """使用原生API直接发送转发消息
        
        Args:
            target_session: 目标会话ID
            nodes_list: 节点列表
            
        Returns:
            bool: 发送成功返回True，否则返回False
        """
        try:
            # 获取群号或用户ID
            target_parts = target_session.split(":", 2)
            if len(target_parts) != 3:
                logger.warning(f"目标会话格式无效: {target_session}")
                return False
                
            target_platform, target_type, target_id = target_parts
            
            # 记录转发的节点结构，便于调试
            logger.debug(f"发送转发消息，共 {len(nodes_list)} 个节点")
            for i, node in enumerate(nodes_list[:2]):  # 只记录前两个节点避免日志过长
                logger.debug(f"节点{i+1}结构: {json.dumps(node, ensure_ascii=False)[:100]}...")
            
            # 调用API发送
            if "GroupMessage" in target_session:
                action = "send_group_forward_msg"
                payload = {"group_id": int(target_id), "messages": nodes_list}
            else:
                action = "send_private_forward_msg"
                payload = {"user_id": int(target_id), "messages": nodes_list}
            
            # 获取client并调用API
            client = self.plugin.context.get_platform("aiocqhttp").get_client()
            response = await client.call_action(action, **payload)
            
            logger.info(f"使用原生API发送转发消息结果: {response}")
            return True
        except Exception as e:
            logger.error(f"使用原生API发送转发消息失败: {e}")
            logger.error(traceback.format_exc())
            # 尝试使用备选方案发送
            fallback_result = await self.send_with_fallback(target_session, nodes_list)
            return fallback_result  # 返回备选方案的结果
    
    async def send_with_fallback(self, target_session: str, nodes_list: List[Dict]) -> bool:
        """当合并转发失败时，尝试直接发送消息
        
        Args:
            target_session: 目标会话ID
            nodes_list: 节点列表
            
        Returns:
            bool: 发送成功返回True，否则返回False
        """
        try:
            # 获取目标平台和ID
            target_parts = target_session.split(":", 2)
            if len(target_parts) != 3:
                logger.warning(f"目标会话格式无效: {target_session}")
                return False
                
            target_platform, target_type, target_id = target_parts
            
            # 获取client
            client = self.plugin.context.get_platform("aiocqhttp").get_client()
            
            # 发送消息前提示
            header_text = f"[无法使用合并转发，将直接发送 {len(nodes_list) - 1} 条消息]"  # -1 是因为最后一个节点是footer
            
            if "GroupMessage" in target_session:
                await client.call_action("send_group_msg", group_id=int(target_id), message=header_text)
            else:
                await client.call_action("send_private_msg", user_id=int(target_id), message=header_text)
            
            # 逐条发送消息
            for node in nodes_list[:-1]:  # 跳过最后一个footer节点
                if node["type"] == "node":
                    await self._send_node_content(target_session, target_id, node)
                    # 添加延迟避免频率限制
                    await asyncio.sleep(1)
            
            # 发送footer
            if nodes_list and nodes_list[-1]["type"] == "node":
                footer_content = nodes_list[-1]["data"].get("content", [])
                if "GroupMessage" in target_session:
                    await client.call_action("send_group_msg", group_id=int(target_id), message=footer_content)
                else:
                    await client.call_action("send_private_msg", user_id=int(target_id), message=footer_content)
            
            logger.info(f"成功使用备选方案发送消息到 {target_session}")
            return True
        except Exception as e:
            logger.error(f"备选方案发送失败: {e}")
            logger.error(traceback.format_exc())
            return False
    
    async def _send_node_content(self, target_session: str, target_id: str, node: Dict):
        """发送节点内容
        
        Args:
            target_session: 目标会话ID
            target_id: 目标ID
            node: 节点数据
        """
        sender_name = node["data"].get("name", "未知")
        content = node["data"].get("content", [])
        
        # 获取client
        client = self.plugin.context.get_platform("aiocqhttp").get_client()
        
        try:
            # 创建包含所有内容的消息链
            from astrbot.api.event import MessageChain
            import astrbot.api.message_components as Comp
            
            message_parts = [Comp.Plain(f"{sender_name}:\n")]
            
            # 处理所有内容项
            for item in content:
                item_type = item.get("type", "")
                
                if item_type == "text":
                    message_parts.append(Comp.Plain(item["data"].get("text", "")))
                
                elif item_type == "image":
                    # 尝试获取图片
                    img_path = await self._prepare_image(item)
                    if img_path:
                        if img_path.startswith('http'):
                            # 对于URL，尝试下载
                            local_path = await self.download_helper.download_image(img_path)
                            if local_path and os.path.exists(local_path):
                                message_parts.append(Comp.Image.fromFileSystem(local_path))
                            else:
                                # 如果下载失败，尝试直接使用URL
                                message_parts.append(Comp.Image.fromURL(img_path))
                        elif img_path.startswith('file:///'):
                            # 对于本地文件
                            local_path = img_path[8:]
                            if os.path.exists(local_path):
                                message_parts.append(Comp.Image.fromFileSystem(local_path))
                        elif os.path.exists(img_path):
                            # 直接就是本地路径
                            message_parts.append(Comp.Image.fromFileSystem(img_path))
                
                elif item_type == "at":
                    message_parts.append(Comp.At(qq=item["data"].get("qq", "")))
            
            # 创建消息链并发送
            message = MessageChain(message_parts)
            
            if "GroupMessage" in target_session:
                await self.plugin.context.send_message(f"aiocqhttp:GroupMessage:{target_id}", message)
            else:
                await self.plugin.context.send_message(f"aiocqhttp:PrivateMessage:{target_id}", message)
                
            logger.info(f"成功发送消息到 {target_session}")
            
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            logger.error(traceback.format_exc())
            
            # 如果上面的方法失败，尝试使用传统方法
            try:
                message = [{"type": "text", "data": {"text": f"{sender_name}:\n"}}]
                message.extend(content)
                
                if "GroupMessage" in target_session:
                    await client.call_action("send_group_msg", group_id=int(target_id), message=message)
                else:
                    await client.call_action("send_private_msg", user_id=int(target_id), message=message)
            except Exception as e2:
                logger.error(f"备用方法发送也失败: {e2}")
                logger.error(traceback.format_exc())
    
    async def _prepare_image(self, img_item: Dict) -> str:
        """准备图片，返回可用于发送的路径
        
        Args:
            img_item: 图片项
            
        Returns:
            str: 图片路径
        """
        try:
            # 尝试从不同字段提取图片信息
            file_path = ""
            img_url = ""
            base64_data = ""
            
            # 检查消息格式，提取图片信息
            if "data" in img_item:
                file_path = img_item["data"].get("file", "")
                img_url = img_item["data"].get("url", "")
                base64_data = img_item["data"].get("base64", "")
            else:
                # 兼容直接存储的序列化格式
                file_path = img_item.get("file", "")
                img_url = img_item.get("url", "")
                base64_data = img_item.get("base64", "")
            
            logger.debug(f"准备图片信息: file_path={file_path}, url={img_url}, has_base64={'是' if base64_data else '否'}")
            
            # 检查是否是QQ链接
            is_qq_url = False
            if img_url and ("multimedia.nt.qq.com.cn" in img_url or "gchat.qpic.cn" in img_url):
                is_qq_url = True
            if file_path and ("multimedia.nt.qq.com.cn" in file_path or "gchat.qpic.cn" in file_path):
                is_qq_url = True
                
            # 对于QQ链接，直接返回URL更可能成功
            if is_qq_url:
                logger.info(f"检测到QQ图片链接，直接使用URL发送")
                return img_url or file_path
            
            # 如果有base64数据，优先使用base64
            if base64_data:
                # 保存为临时文件
                try:
                    import uuid
                    temp_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                            "temp", f"{uuid.uuid4()}.jpg")
                    os.makedirs(os.path.dirname(temp_file), exist_ok=True)
                    
                    # 确保base64数据格式正确
                    if "base64://" in base64_data:
                        base64_data = base64_data.split("base64://")[1]
                    
                    image_data = base64.b64decode(base64_data)
                    with open(temp_file, "wb") as f:
                        f.write(image_data)
                    
                    logger.debug(f"成功从base64保存临时图片: {temp_file}")
                    return f"file:///{temp_file}"
                except Exception as e:
                    logger.error(f"从base64保存图片失败: {e}")
            
            # 优先使用本地文件
            if file_path:
                # 处理可能的多种格式
                if file_path.startswith("file:///"):
                    clean_path = file_path[8:]
                    if os.path.exists(clean_path):
                        logger.debug(f"使用本地文件 (file://): {file_path}")
                        return file_path
                elif file_path.startswith("http"):
                    # 如果file字段包含URL，当作URL处理
                    logger.debug(f"文件路径包含URL，作为URL处理: {file_path}")
                    # 对于QQ多媒体URL，直接返回更可能成功
                    if "multimedia.nt.qq.com.cn" in file_path or "gchat.qpic.cn" in file_path:
                        return file_path
                    
                    local_path = await self.download_helper.download_image(file_path)
                    if local_path and os.path.exists(local_path):
                        logger.debug(f"已下载URL图片到: {local_path}")
                        return f"file:///{local_path}"
                    elif local_path:  # 如果download_image返回了原始URL
                        return local_path
                elif os.path.exists(file_path):
                    logger.debug(f"使用本地文件 (直接路径): {file_path}")
                    return f"file:///{file_path}"
                else:
                    logger.warning(f"文件路径不存在: {file_path}")
            
            # 其次使用URL
            if img_url:
                # 对于QQ多媒体URL，直接返回更可能成功
                if "multimedia.nt.qq.com.cn" in img_url or "gchat.qpic.cn" in img_url:
                    return img_url
                
                # 检查是否已经下载过相同的图片URL
                cache_key = f"img_cache_{hash(img_url)}"
                cached_path = self.plugin.config.get(cache_key, "")
                
                if cached_path and os.path.exists(cached_path):
                    logger.debug(f"从缓存获取图片: {cached_path}")
                    return f"file:///{cached_path}"
                
                # 下载图片
                logger.debug(f"下载图片URL: {img_url}")
                local_path = await self.download_helper.download_image(img_url)
                if local_path and os.path.exists(local_path):
                    # 缓存路径以便下次使用
                    self.plugin.config[cache_key] = local_path
                    logger.debug(f"已下载URL图片到: {local_path}")
                    return f"file:///{local_path}"
                elif local_path:  # 如果download_image返回了原始URL
                    return local_path
                else:
                    logger.warning(f"图片URL下载失败: {img_url}")
                    # 下载失败时直接返回URL
                    return img_url
            
            logger.warning("图片准备失败: 无可用来源")
            return None
        except Exception as e:
            logger.error(f"准备图片失败: {e}")
            logger.error(traceback.format_exc())
            return None

    async def _send_image(self, client, target_session: str, target_id: str, sender_name: str, file_path: str) -> bool:
        """发送图片
        
        Args:
            client: API客户端
            target_session: 目标会话ID
            target_id: 目标ID
            sender_name: 发送者名称
            file_path: 图片文件路径
            
        Returns:
            bool: 发送成功返回True，否则返回False
        """
        try:
            logger.info(f"尝试发送图片: {file_path}")
            
            # 检查是否为URL
            is_url = file_path.startswith("http")
            
            # 方式0：对QQ多媒体URL使用专用格式发送
            if is_url and ("multimedia.nt.qq.com.cn" in file_path or "gchat.qpic.cn" in file_path):
                try:
                    message = [
                        {"type": "text", "data": {"text": f"{sender_name}:\n"}},
                        {"type": "image", "data": {"url": file_path}}
                    ]
                    
                    if "GroupMessage" in target_session:
                        await client.call_action("send_group_msg", group_id=int(target_id), message=message)
                    else:
                        await client.call_action("send_private_msg", user_id=int(target_id), message=message)
                    
                    logger.info("QQ多媒体URL方式发送图片成功")
                    return True
                except Exception as e:
                    logger.warning(f"QQ多媒体URL方式发送图片失败: {e}，尝试其他方式")
            
            # 方式1: 使用标准格式发送 (推荐方式)
            try:
                message = [
                    {"type": "text", "data": {"text": f"{sender_name}:\n"}},
                    {"type": "image", "data": {"file": file_path}}
                ]
                
                if "GroupMessage" in target_session:
                    await client.call_action("send_group_msg", group_id=int(target_id), message=message)
                else:
                    await client.call_action("send_private_msg", user_id=int(target_id), message=message)
                
                logger.info("方式1发送图片成功")
                return True
            except Exception as e:
                logger.warning(f"方式1发送图片失败: {e}，尝试方式2")
            
            # 方式2: 使用Base64发送 (适用于小图片)
            try:
                local_path = file_path
                if file_path.startswith("file:///"):
                    local_path = file_path[8:]
                elif file_path.startswith("http"):
                    # 如果是URL，尝试先下载
                    local_path = await self.download_helper.download_image(file_path)
                    if not local_path or not os.path.exists(local_path):
                        logger.warning(f"无法下载URL图片: {file_path}")
                        local_path = None
                
                if local_path and os.path.exists(local_path):
                    # 检查文件大小，大于1MB的图片可能会导致Base64发送失败
                    file_size = os.path.getsize(local_path)
                    if file_size > 1048576:  # 1MB
                        logger.warning(f"图片过大({file_size/1024/1024:.2f}MB)，跳过Base64方式")
                    else:
                        # 读取文件并转换为Base64
                        with open(local_path, "rb") as f:
                            image_bytes = f.read()
                        
                        base64_data = base64.b64encode(image_bytes).decode('utf-8')
                        base64_image = f"base64://{base64_data}"
                        
                        message = [
                            {"type": "text", "data": {"text": f"{sender_name}:\n"}},
                            {"type": "image", "data": {"file": base64_image}}
                        ]
                        
                        if "GroupMessage" in target_session:
                            await client.call_action("send_group_msg", group_id=int(target_id), message=message)
                        else:
                            await client.call_action("send_private_msg", user_id=int(target_id), message=message)
                        
                        logger.info("方式2发送图片成功")
                        return True
            except Exception as e:
                logger.warning(f"方式2发送图片失败: {e}，尝试方式3")
            
            # 方式3: 使用CQ码发送 (最后尝试)
            try:
                if file_path.startswith("file:///"):
                    local_path = file_path[8:]
                    cq_message = f"{sender_name}:\n[CQ:image,file=file:///{local_path}]"
                elif file_path.startswith("http"):
                    cq_message = f"{sender_name}:\n[CQ:image,url={file_path}]"
                else:
                    cq_message = f"{sender_name}:\n[CQ:image,file={file_path}]"
                
                if "GroupMessage" in target_session:
                    await client.call_action("send_group_msg", group_id=int(target_id), message=cq_message)
                else:
                    await client.call_action("send_private_msg", user_id=int(target_id), message=cq_message)
                
                logger.info("方式3发送图片成功")
                return True
            except Exception as e:
                logger.error(f"方式3发送图片失败: {e}")
            
            # 方式4: 最后尝试发送纯文本消息，让用户知道有图片但无法显示
            try:
                text_message = f"{sender_name}:\n[图片无法显示，原始链接: {file_path}]"
                
                if "GroupMessage" in target_session:
                    await client.call_action("send_group_msg", group_id=int(target_id), message=text_message)
                else:
                    await client.call_action("send_private_msg", user_id=int(target_id), message=text_message)
                
                logger.info("方式4发送图片失败提示成功")
                return True
            except Exception as e:
                logger.error(f"方式4发送图片失败提示失败: {e}")
            
            logger.error(f"所有方式发送图片均失败: {file_path}")
            return False
        except Exception as e:
            logger.error(f"发送图片处理过程中出错: {e}")
            logger.error(traceback.format_exc())
            return False
    
    async def send_to_non_qq_platform(self, target_session: str, source_name: str, valid_messages: List[Dict]):
        """发送消息到非QQ平台
        
        Args:
            target_session: 目标会话ID
            source_name: 消息来源名称
            valid_messages: 有效的消息列表
            
        Returns:
            bool: 发送成功返回True，否则返回False
        """
        try:
            from .message_serializer import deserialize_message
            
            # 发送头部信息
            header_text = f"📨 收到来自{source_name}的 {len(valid_messages)} 条消息："
            await self.plugin.context.send_message(target_session, [Plain(text=header_text)])
            
            # 逐条发送消息
            for msg in valid_messages:
                sender = msg.get('sender_name', '未知用户')
                message_components = deserialize_message(msg.get('message', []))
                
                await self.plugin.context.send_message(target_session, [Plain(text=f"{sender}:")])
                
                if message_components:
                    await self.plugin.context.send_message(target_session, message_components)
                else:
                    await self.plugin.context.send_message(target_session, [Plain(text="[空消息]")])
                
                await asyncio.sleep(0.5)
            
            # 发送底部信息
            footer_text = f"[此消息包含 {len(valid_messages)} 条消息，来自{source_name}]"
            await self.plugin.context.send_message(target_session, [Plain(text=footer_text)])
            
            return True
        except Exception as e:
            logger.error(f"发送消息到非QQ平台失败: {e}")
            logger.error(traceback.format_exc())
            return False
