import time
from typing import Dict, List, Any
from astrbot.api import logger

class RetryManager:
    """处理失败消息重试的类"""
    
    def __init__(self, plugin, cache_manager, message_builder, message_sender):
        self.plugin = plugin
        self.cache_manager = cache_manager
        self.message_builder = message_builder
        self.message_sender = message_sender
    
    async def retry_failed_messages(self):
        """尝试重新发送缓存的失败消息"""
        failed_messages_cache = self.cache_manager.get_all_failed_messages()
        if not failed_messages_cache:
            return
        
        logger.info(f"开始重试发送失败消息，共 {len(failed_messages_cache)} 个目标会话")
        
        for target_session in list(failed_messages_cache.keys()):
            messages = failed_messages_cache[target_session]
            
            for i, msg in enumerate(list(messages)):
                try:
                    # 增加重试计数
                    retry_count = self.cache_manager.increment_retry_count(target_session, i)
                    
                    # 提高放弃阈值，但更智能地处理重试
                    if retry_count > 5:
                        logger.warning(f"消息重试次数超过5次，放弃重试: {msg}")
                        # 从失败缓存中永久删除
                        self.cache_manager.remove_failed_message(target_session, msg["task_id"], msg["source_session"])
                        continue
                    
                    # 根据重试次数指数增加等待时间，避免频繁重试
                    # 第1次：立即，第2次：1小时，第3次：4小时，第4次：9小时...
                    # 判断上次重试时间是否足够长
                    last_retry_time = msg.get("last_retry_time", 0)
                    current_time = time.time()
                    
                    # 计算需要等待的时间（小时）
                    wait_hours = (retry_count - 1) ** 2
                    wait_seconds = wait_hours * 3600
                    
                    time_since_last_retry = current_time - last_retry_time
                    if time_since_last_retry < wait_seconds:
                        # 还没到重试时间，跳过
                        logger.debug(f"消息重试冷却中，还需等待 {(wait_seconds-time_since_last_retry)/3600:.1f} 小时: {msg}")
                        continue
                    
                    # 更新最后重试时间
                    msg["last_retry_time"] = current_time
                    
                    task_id = msg["task_id"]
                    source_session = msg["source_session"]
                    
                    # 检查任务是否存在、是否启用、消息缓存是否存在
                    if not await self._validate_retry_prerequisites(task_id, source_session):
                        continue
                    
                    # 检查目标会话格式
                    target_parts = target_session.split(":", 2) if ":" in target_session else []
                    if len(target_parts) != 3:
                        logger.warning(f"目标会话格式无效: {target_session}")
                        continue
                    
                    target_platform, target_type, target_id = target_parts
                    
                    logger.info(f"重试发送任务 {task_id} 从 {source_session} 到 {target_session} 的消息")
                    
                    valid_messages = self.plugin.message_cache.get(task_id, {}).get(source_session, [])
                    
                    if not valid_messages:
                        logger.warning(f"任务 {task_id} 会话 {source_session} 的消息缓存为空，无法重试")
                        continue
                    
                    # 根据平台选择发送方式
                    if target_platform == "aiocqhttp":
                        await self._retry_send_to_qq(target_session, valid_messages)
                        # 发送成功，删除失败缓存记录
                        self.cache_manager.remove_failed_message(target_session, task_id, source_session)
                    else:
                        logger.warning(f"目前重试功能只支持QQ平台，跳过 {target_session}")
                        # 对于非QQ平台，不再重试，直接删除缓存记录
                        self.cache_manager.remove_failed_message(target_session, task_id, source_session)
                
                except Exception as e:
                    logger.error(f"重试发送消息到 {target_session} 失败: {e}")
    
    async def _validate_retry_prerequisites(self, task_id: str, source_session: str) -> bool:
        """验证重试的前提条件
        
        Args:
            task_id: 任务ID
            source_session: 源会话ID
            
        Returns:
            bool: 条件满足返回True，否则返回False
        """
        task = self.plugin.get_task_by_id(task_id)
        if not task:
            logger.warning(f"任务 {task_id} 不存在，无法重试转发")
            return False
        
        if not task.get('enabled', True):
            logger.warning(f"任务 {task_id} 已禁用，无法重试转发")
            return False
        
        if (task_id not in self.plugin.message_cache or 
            source_session not in self.plugin.message_cache[task_id] or
            not self.plugin.message_cache[task_id][source_session]):
            logger.warning(f"任务 {task_id} 会话 {source_session} 的消息缓存已清空，无法重试转发")
            return False
        
        return True
    
    async def _retry_send_to_qq(self, target_session: str, valid_messages: List[Dict]):
        """重试发送消息到QQ平台
        
        Args:
            target_session: 目标会话ID
            valid_messages: 有效的消息列表
        """
        nodes_list = []
        
        # 构建消息节点
        for msg_data in valid_messages:
            try:
                node = await self.message_builder.build_forward_node(msg_data)
                nodes_list.append(node)
            except Exception as e:
                logger.error(f"重试时构造转发消息节点失败: {e}")
        
        # 添加底部信息节点
        footer_node = self.message_builder.build_footer_node("", len(valid_messages), True)
        nodes_list.append(footer_node)
        
        # 直接使用原生API发送
        await self.message_sender.send_forward_message_via_api(target_session, nodes_list)
        logger.info(f"成功重试发送消息到 {target_session}")
