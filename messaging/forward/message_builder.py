import os
import time
import json
from typing import Dict, List, Any
from astrbot.api import logger

class MessageBuilder:
    """消息构建器，负责构建各类消息结构"""
    
    def __init__(self, download_helper):
        self.download_helper = download_helper
    
    async def build_forward_node(self, msg_data: Dict) -> Dict:
        """构建单个转发节点
        
        Args:
            msg_data: 消息数据字典
            
        Returns:
            Dict: 转发节点（适合QQ API的字典格式）
        """
        sender_name = msg_data.get('sender_name', '未知用户')
        sender_id = msg_data.get('sender_id', '0')
        
        # 确保sender_id是字符串类型
        sender_id_str = str(sender_id)
        
        timestamp = msg_data.get('timestamp', int(time.time()))
        
        # 获取原始消息序列化数据
        serialized_message = msg_data.get('message', [])
        message_components = []
        
        # 处理消息内容，提取所有类型的消息组件
        for comp in serialized_message:
            comp_type = comp.get('type', '')
            
            # 处理不同类型的组件
            component = await self._process_component(comp_type, comp, timestamp)
            if component:
                message_components.append(component)
        
        # 如果没有内容，使用纯文本消息
        if not message_components:
            message_components = [{"type": "text", "data": {"text": "[空消息]"}}]
        
        # 添加更详细的日志，帮助调试
        logger.debug(f"构建转发节点: {sender_name}({sender_id_str}), 共 {len(message_components)} 个组件")
        for i, comp in enumerate(message_components[:3]):  # 只显示前三个组件避免日志过长
            logger.debug(f"组件{i+1}: 类型={comp.get('type')}, 数据={comp.get('data')}")
        
        # 直接返回适合QQ API的字典格式
        node_data = {
            "type": "node",
            "data": {
                "uin": sender_id_str,
                "name": sender_name,
                "content": message_components,
                "time": timestamp
            }
        }
        
        # 添加节点构建完整日志，便于调试
        try:
            for comp in message_components:
                if comp.get('type') == 'image':
                    logger.debug(f"图片组件详情: {json.dumps(comp, ensure_ascii=False)}")
            logger.debug(f"完整转发节点结构: {json.dumps(node_data, ensure_ascii=False)}")
        except Exception as e:
            logger.debug(f"序列化节点结构失败: {e}")

        return node_data
    
    async def _process_component(self, comp_type: str, comp: Dict, timestamp: int) -> Dict:
        """处理单个消息组件
        
        Args:
            comp_type: 组件类型
            comp: 组件数据
            timestamp: 消息时间戳
            
        Returns:
            Dict: 处理后的组件数据
        """
        if comp_type == 'plain':
            return {
                "type": "text", 
                "data": {"text": comp.get('text', '')}
            }
        
        elif comp_type == 'image':
            return await self._process_image_component(comp)
            
        elif comp_type == 'at':
            return {
                "type": "at",
                "data": {
                    "qq": comp.get('qq', ''),
                    "name": comp.get('name', '')
                }
            }
            
        elif comp_type == 'face':
            return {
                "type": "face",
                "data": {"id": comp.get('id', '0')}
            }
            
        elif comp_type == 'record':
            return await self._process_record_component(comp)
            
        elif comp_type == 'file':
            return {
                "type": "file",
                "data": {
                    "url": comp.get('url', ''),
                    "name": comp.get('name', ''),
                    "file": comp.get('file', '')
                }
            }
            
        elif comp_type == 'reply':
            return {
                "type": "reply",
                "data": {
                    "id": comp.get('id', ''),
                    "text": comp.get('text', ''),
                    "qq": comp.get('sender_id', ''),
                    "time": comp.get('time', timestamp),
                    "sender": {"nickname": comp.get('sender_nickname', '未知用户')}
                }
            }
            
        elif comp_type == 'forward':
            return {
                "type": "text",
                "data": {"text": f"[转发消息: {comp.get('id', '未知ID')}]"}
            }
            
        else:
            # 处理其他未知类型的消息
            return {
                "type": "text",
                "data": {"text": f"[未知消息类型: {comp_type}]"}
            }
    
    async def _process_image_component(self, comp: Dict) -> Dict:
        """处理图片组件"""
        image_data = {"type": "image", "data": {}}
        
        # 获取图片信息
        url = comp.get('url', '')
        file = comp.get('file', '')
        base64_data = comp.get('base64', '')
        filename = comp.get('filename', '')
        
        # 检查是否为GIF - 新增！
        is_gif = False
        if url and url.lower().endswith('.gif'):
            is_gif = True
        elif file and file.lower().endswith('.gif'):
            is_gif = True
        elif filename and filename.lower().endswith('.gif'):
            is_gif = True
        
        # 如果是GIF，添加标记
        if is_gif:
            image_data["data"]["is_gif"] = True
            logger.info(f"检测到GIF图片: {filename or url or file}")
        
        # 增加日志，查看接收到的原始组件结构
        logger.debug(f"处理图片组件，原始comp: {comp}")
        
        # 处理QQ图片链接
        if ("multimedia.nt.qq.com.cn" in url or "gchat.qpic.cn" in url or 
            "multimedia.nt.qq.com.cn" in file or "gchat.qpic.cn" in file):
            
            # 保存原始URL供后续使用
            original_url = url or file
            
            # 保存原始URL和文件名，便于多级策略发送
            image_data["data"]["file"] = original_url  # 使用URL作为file字段
            
            # 保存文件名作为备选方案
            if filename:
                image_data["data"]["filename"] = filename
                # 将原始URL添加为备用
                image_data["data"]["original_url"] = original_url
                logger.debug(f"同时保存filename和URL: {filename}, {original_url}")
            else:
                logger.debug(f"仅使用URL: {original_url}")
            
            return image_data
        
        # 其它类型图片处理逻辑
        # base64编码图片
        if base64_data:
            if "base64://" not in base64_data:
                base64_data = f"base64://{base64_data}"
            logger.debug("使用base64图片")
            image_data["data"]["file"] = base64_data
            return image_data
        
        # 普通URL图片 - 也直接使用URL而非文件名
        if url:
            logger.debug(f"使用图片URL: {url}")
            image_data["data"]["file"] = url
            return image_data
        
        if file and file.startswith('http'):
            logger.debug(f"使用图片文件URL: {file}")
            image_data["data"]["file"] = file
            return image_data
        
        # 本地文件 - 合并转发不支持本地文件路径，尝试转为文件URL或base64
        if file:
            clean_path = file
            if file.startswith("file:///"):
                clean_path = file[8:]
            
            if os.path.exists(clean_path):
                try:
                    # 对于合并转发，尝试将本地文件转为base64
                    import base64
                    with open(clean_path, "rb") as f:
                        img_content = f.read()
                        if len(img_content) < 1048576:  # 小于1MB的图片转base64
                            b64_data = base64.b64encode(img_content).decode('utf-8')
                            image_data["data"]["file"] = f"base64://{b64_data}"
                            logger.debug(f"将本地文件转换为base64用于合并转发: {clean_path}")
                            return image_data
                except Exception as e:
                    logger.warning(f"转换本地文件为base64失败: {e}")
                
                # 如果base64转换失败，使用本地路径，但合并转发可能失败
                logger.debug(f"使用本地图片路径(合并转发可能失败): {clean_path}")
                image_data["data"]["file"] = clean_path
                return image_data
        
        # 兜底处理
        logger.warning("无法处理图片，使用占位图")
        image_data["data"]["file"] = "base64://iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVQI12NgAAIAAAUAAeImBZsAAAAASUVORK5CYII="
        
        return image_data
    
    async def _process_record_component(self, comp: Dict) -> Dict:
        """处理语音组件
        
        Args:
            comp: 组件数据
            
        Returns:
            Dict: 处理后的语音组件数据
        """
        record_data = {"type": "record", "data": {}}
        local_file_path = ""
        
        # 下载语音到本地
        if comp.get('url'):
            local_file_path = await self.download_helper.download_audio(comp.get('url'))
        elif comp.get('file') and comp.get('file').startswith('http'):
            local_file_path = await self.download_helper.download_audio(comp.get('file'))
        elif comp.get('file') and os.path.exists(comp.get('file')):
            local_file_path = comp.get('file')
        
        if local_file_path and os.path.exists(local_file_path):
            record_data["data"]["file"] = f"file:///{local_file_path}"
        else:
            # 下载失败时的回退方案
            if comp.get('url'):
                record_data["data"]["file"] = comp.get('url')
            elif comp.get('file'):
                record_data["data"]["file"] = comp.get('file')
        
        return record_data
    
    def build_footer_node(self, source_name: str, message_count: int, is_retry: bool = False) -> Dict:
        """构建底部信息节点
        
        Args:
            source_name: 消息来源名称
            message_count: 消息数量
            is_retry: 是否为重试消息
            
        Returns:
            Dict: 底部信息节点
        """
        suffix = "重试缓存" if is_retry else source_name
        footer_text = f"[此消息包含 {message_count} 条消息，来自{suffix}]"
        
        return {
            "type": "node",
            "data": {
                "uin": "0",
                "name": "消息转发系统",
                "content": [{"type": "text", "data": {"text": footer_text}}],
                "time": int(time.time())
            }
        }
