import os

import asyncio
from typing import List, Dict
from astrbot.api import logger
import traceback

# 修改导入路径，使用forward子目录
from .forward import (
    CacheManager,
    DownloadHelper, 
    MessageBuilder,
    MessageSender,
    RetryManager
)

class ForwardManager:
    """处理消息转发功能的类喵～"""
    
    def __init__(self, plugin):
        self.plugin = plugin
        
        # 创建媒体下载目录
        self.image_dir = os.path.join(self.plugin.data_dir, "temp")
        os.makedirs(self.image_dir, exist_ok=True)
          # 初始化各个子组件
        self.download_helper = DownloadHelper(self.image_dir)
        self.message_builder = MessageBuilder(self.download_helper, self.plugin)
        self.cache_manager = CacheManager(plugin)
        self.message_sender = MessageSender(plugin, self.download_helper)
        self.retry_manager = RetryManager(plugin, self.cache_manager, self.message_builder, self.message_sender)
        
        # 启动定期重试任务
        asyncio.create_task(self.periodic_retry_operations())
    async def periodic_retry_operations(self):
        """定期重试发送失败的消息"""
        while True:
            try:
                await asyncio.sleep(3600)  # 每小时重试一次（原来是15分钟）
                await self.retry_manager.retry_failed_messages()
            except Exception as e:
                logger.error(f"定期重试操作失败: {e}")
    
    def save_failed_messages_cache(self):
        """将失败消息缓存保存到文件"""
        self.cache_manager.save_failed_messages_cache()
    
    async def build_forward_node(self, msg_data: Dict) -> Dict:
        """构建单个转发节点，委托给MessageBuilder"""
        return await self.message_builder.build_forward_node(msg_data)
    
    async def send_forward_message_via_api(self, target_session: str, nodes_list: List[Dict]) -> bool:
        """使用原生API发送转发消息，委托给MessageSender"""
        return await self.message_sender.send_forward_message_via_api(target_session, nodes_list)
    
    async def send_with_fallback(self, target_session: str, nodes_list: List[Dict]) -> bool:
        """使用备选方案发送消息，委托给MessageSender"""
        return await self.message_sender.send_with_fallback(target_session, nodes_list)
    
    async def retry_failed_messages(self):
        """重试发送失败消息，委托给RetryManager"""
        await self.retry_manager.retry_failed_messages()
    
    async def forward_messages(self, task_id: str, session_id: str):
        """转发消息到目标会话喵～"""
        try:
            # 获取任务信息
            task = self.plugin.get_task_by_id(task_id)
            if not task:
                logger.error(f"未找到ID为 {task_id} 的任务喵～")
                return
                
            # 检查目标会话
            target_sessions = task.get("target_sessions", [])
            if not target_sessions:
                logger.warning(f"任务 {task_id}: 没有设置任何转发目标，跳过转发喵～")
                return
            
            # 获取消息缓存
            messages = self.plugin.message_cache.get(task_id, {}).get(session_id, [])
            if not messages:
                logger.warning(f"任务 {task_id}: 会话 {session_id} 没有缓存的消息，跳过转发喵～")
                return
              # 筛选有效消息
            valid_messages = []
            for msg in messages:
                message_components = msg.get("messages", [])  # 修复：使用正确的字段名
                
                if message_components:
                    valid_messages.append(msg)
                else:
                    logger.warning(f"跳过空消息: {msg}")
                    
            if not valid_messages:
                logger.warning(f"任务 {task_id}: 会话 {session_id} 没有有效消息，跳过转发喵～")
                return
                
            logger.info(f"任务 {task_id}: 将 {len(valid_messages)} 条有效消息从 {session_id} 转发到 {len(target_sessions)} 个目标喵～")
            
            # 获取来源信息
            source_type = session_id.split(":", 2)[1] if ":" in session_id else "Unknown"
            source_id = session_id.split(":", 2)[2] if ":" in session_id and len(session_id.split(":", 2)) > 2 else "Unknown"
            is_group = "Group" in source_type
            source_name = f"群 {source_id}" if is_group else f"用户 {source_id}"
            
            # 构建节点列表
            nodes_list = []
            
            for msg in valid_messages:
                node = await self.build_forward_node(msg)
                nodes_list.append(node)
            
            # 添加底部信息节点
            footer_node = self.message_builder.build_footer_node(source_name, len(valid_messages))
            nodes_list.append(footer_node)
            
            # 向每个目标会话发送消息
            for target_session in target_sessions:
                try:
                    # 解析目标会话信息
                    target_parts = target_session.split(":", 2) if ":" in target_session else []
                    if len(target_parts) != 3:
                        logger.warning(f"目标会话格式无效: {target_session}")
                        continue
                        
                    target_platform, target_type, target_id = target_parts
                    
                    # 检查平台适配器是否存在
                    platform = self.plugin.context.get_platform(target_platform)
                    if not platform:
                        logger.warning(f"未找到平台适配器: {target_platform}")
                        continue
                    
                    # 根据平台选择发送方式
                    if target_platform == "aiocqhttp":
                        logger.debug(f"开始尝试发送QQ合并转发消息到 {target_session}")
                        api_result = await self.send_forward_message_via_api(target_session, nodes_list)
                        
                        if not api_result:
                            logger.warning("使用原生API发送转发消息失败，但已通过备选方案处理")
                        
                        # 清除失败缓存
                        self.cache_manager.remove_failed_message(target_session, task_id, session_id)
                    else:
                        # 非QQ平台使用常规方式发送
                        await self.message_sender.send_to_non_qq_platform(target_session, source_name, valid_messages)
                    
                    logger.info(f"成功将消息转发到 {target_session}")
                    
                except Exception as e:
                    logger.error(f"转发消息到 {target_session} 失败: {e}")
                    logger.error(traceback.format_exc())
                    
                    # 记录失败消息到缓存
                    self.cache_manager.add_failed_message(target_session, task_id, session_id)
              # 清除已处理的消息缓存
            self.plugin.message_cache[task_id][session_id] = []
            logger.info(f"任务 {task_id}: 已清除会话 {session_id} 的消息缓存")
            
            self.plugin.save_message_cache()
            
        except Exception as e:
            logger.error(f"转发消息时出错喵: {e}")
            logger.error(traceback.format_exc())