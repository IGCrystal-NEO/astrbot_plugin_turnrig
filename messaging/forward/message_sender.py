import os
import asyncio
import json
import traceback
from typing import Dict, List, Any
from astrbot.api import logger
from astrbot.api.message_components import Plain

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
        
        # 构建消息
        message = [{"type": "text", "data": {"text": f"{sender_name}:\n"}}]
        
        # 获取client
        client = self.plugin.context.get_platform("aiocqhttp").get_client()
        
        # 检查内容是否有图片，先处理图片
        has_image = False
        for item in content:
            if item.get("type") == "image":
                has_image = True
                # 尝试提取本地文件路径
                file_path = item.get("data", {}).get("file", "")
                
                if file_path.startswith("file:///"):
                    # 移除前缀
                    file_path = file_path[8:]
                    await self._send_image(client, target_session, target_id, sender_name, file_path)
                    has_image = False
                    break
                elif item.get("data", {}).get("url"):
                    # 尝试下载并发送图片
                    img_url = item.get("data", {}).get("url")
                    local_path = await self.download_helper.download_image(img_url)
                    if local_path and os.path.exists(local_path):
                        await self._send_image(client, target_session, target_id, sender_name, local_path)
                        has_image = False
                        break
        
        # 如果没有图片或图片发送失败，发送所有内容
        if not has_image:
            message.extend(content)
            
            # 发送
            if "GroupMessage" in target_session:
                await client.call_action("send_group_msg", group_id=int(target_id), message=message)
            else:
                await client.call_action("send_private_msg", user_id=int(target_id), message=message)
    
    async def _send_image(self, client, target_session: str, target_id: str, sender_name: str, file_path: str):
        """发送图片
        
        Args:
            client: API客户端
            target_session: 目标会话ID
            target_id: 目标ID
            sender_name: 发送者名称
            file_path: 图片文件路径
        """
        try:
            logger.info(f"发送图片: {file_path}")
            if "GroupMessage" in target_session:
                await client.call_action(
                    "send_group_msg", 
                    group_id=int(target_id), 
                    message=[
                        {"type": "text", "data": {"text": f"{sender_name}:\n"}},
                        {"type": "image", "data": {"file": f"file:///{file_path}"}}
                    ]
                )
            else:
                await client.call_action(
                    "send_private_msg", 
                    user_id=int(target_id), 
                    message=[
                        {"type": "text", "data": {"text": f"{sender_name}:\n"}},
                        {"type": "image", "data": {"file": f"file:///{file_path}"}}
                    ]
                )
        except Exception as e:
            logger.error(f"发送图片失败: {e}")
            logger.error(traceback.format_exc())
    
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
