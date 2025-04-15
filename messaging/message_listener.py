import asyncio
import time
from typing import Dict, Any, List
import astrbot.api.message_components as Comp
from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent
from astrbot.api.message_components import Plain, Image, At, Reply, Forward

# 更新导入路径
from .message_serializer import serialize_message
from ..utils.session_formatter import normalize_session_id
from .message_utils import fetch_message_detail

class MessageListener:
    """处理消息监听和缓存的类喵～"""
    
    def __init__(self, plugin):
        self.plugin = plugin
        # 调试计数器
        self.message_count = 0
    
    async def on_all_message(self, event: AstrMessageEvent):
        """监听所有消息并进行处理喵～"""
        try:
            logger.info(f"MessageListener.on_all_message 被调用，处理消息: {event.message_str}")
            # 获取消息平台名称，判断是否为 aiocqhttp
            platform_name = event.get_platform_name()
            logger.info(f"消息平台: {platform_name}")
            
            self.message_count += 1
            # 记录每100条消息的调试信息
            if self.message_count % 100 == 0:
                logger.debug(f"已处理 {self.message_count} 条消息喵~")
            
            # 获取消息源
            session_id = event.unified_msg_origin
            logger.debug(f"统一消息ID: {session_id}")
            
            # 获取启用的任务列表
            enabled_tasks = self.plugin.get_all_enabled_tasks()
            logger.debug(f"获取到 {len(enabled_tasks)} 个已启用任务")
            if not enabled_tasks:
                logger.warning("没有已启用的任务，跳过处理")
                return
                
            # 优先使用事件的message_str属性
            plain_text = event.message_str
            if not plain_text and hasattr(event.message_obj, 'message_str'):
                plain_text = event.message_obj.message_str
                
            # 详细记录消息内容，帮助调试
            logger.debug(f"收到消息 [{event.get_sender_name()}]: '{plain_text}' (长度: {len(plain_text) if plain_text else 0})")
            
            # 更详细地输出原始消息对象，以便诊断问题
            logger.debug(f"原始消息对象: {event.message_obj}")
            
            # 调试原始消息内容
            messages = event.get_messages()
            if not messages:
                logger.debug("⚠️ 消息组件列表为空！尝试从其他属性获取内容")
                # 尝试从raw_message中获取内容
                if hasattr(event.message_obj, 'raw_message') and event.message_obj.raw_message:
                    logger.debug(f"从raw_message找到内容: {event.message_obj.raw_message}")
                    messages = [Plain(text=str(event.message_obj.raw_message))]
            else:
                components_info = []
                for i, comp in enumerate(messages):
                    comp_type = type(comp).__name__
                    if isinstance(comp, Plain):
                        text_content = getattr(comp, "text", "")
                        components_info.append(f"[{i}] [{comp_type}] '{text_content}' (长度: {len(text_content)})")
                    else:
                        components_info.append(f"[{i}] [{comp_type}]")
                logger.debug(f"消息组件: {' | '.join(components_info)}")
            
            # 处理每个任务
            task_matched = False
            for task in enabled_tasks:
                # 确保任务有ID，避免None值
                task_id = task.get('id')
                if not task_id:
                    logger.warning(f"跳过没有ID的任务: {task}")
                    continue
                
                logger.debug(f"检查任务 [{task.get('name', '未命名')}](ID: {task_id}) 是否匹配当前消息")
                
                # 检查此会话是否应该被监听
                should_monitor = self._should_monitor_session(task, event)
                if not should_monitor:
                    logger.debug(f"任务 [{task.get('name', '未命名')}] 不监听此会话，跳过")
                    continue
                
                # 检查是否应该监听此用户
                should_monitor_user = self._should_monitor_user(task, event)
                if not should_monitor_user:
                    logger.debug(f"任务 [{task.get('name', '未命名')}] 不监听此用户，跳过")
                    continue
                
                task_matched = True
                logger.info(f"任务 [{task.get('name', '未命名')}](ID: {task_id}) 匹配当前消息！")
                
                # 初始化缓存
                if task_id not in self.plugin.message_cache:
                    logger.debug(f"为任务 {task_id} 创建消息缓存")
                    self.plugin.message_cache[task_id] = {}
                    
                if session_id not in self.plugin.message_cache[task_id]:
                    logger.debug(f"为任务 {task_id} 下的会话 {session_id} 创建消息列表")
                    self.plugin.message_cache[task_id][session_id] = []
                    
                # 获取消息详情
                sender_name = event.get_sender_name() or "未知用户"
                sender_id = event.get_sender_id() or "0"
                timestamp = int(time.time())
                # 安全获取message_id，确保有默认值
                message_id = getattr(event.message_obj, "message_id", "unknown") if hasattr(event, "message_obj") else "unknown"
                
                # 开始诊断：打印完整的原始消息对象
                logger.debug(f"详细消息对象: {event.message_obj.__dict__ if hasattr(event.message_obj, '__dict__') else 'No __dict__'}")
                
                # 确保消息非空 - 优先使用各种方式确保获取到内容
                has_content = False
                
                # 序列化消息
                serialized_messages = serialize_message(messages)
                
                # 如果序列化后没有内容，但原始消息有内容，则直接创建一个纯文本组件
                if (not serialized_messages or 
                    (len(serialized_messages) == 1 and 
                     serialized_messages[0].get('type') == 'plain' and 
                     not serialized_messages[0].get('text'))) and plain_text:
                    logger.debug(f"消息序列化后为空，使用plain_text替代: '{plain_text}'")
                    serialized_messages = [{"type": "plain", "text": plain_text}]
                    has_content = True
                
                # 检查message_obj的属性，尝试找到有效内容
                if not has_content and not serialized_messages:
                    # 尝试从raw_message获取
                    if hasattr(event.message_obj, 'raw_message') and event.message_obj.raw_message:
                        raw_text = str(event.message_obj.raw_message)
                        logger.debug(f"使用raw_message作为消息内容: '{raw_text}'")
                        serialized_messages = [{"type": "plain", "text": raw_text}]
                        has_content = True
                
                # 最后尝试，如果依然没有内容但我们知道确实收到了消息，添加一个备用文本
                if not has_content and not serialized_messages:
                    backup_text = f"[收到来自 {sender_name} 的消息，但内容无法识别]"
                    logger.debug(f"使用备用文本作为消息内容: '{backup_text}'")
                    serialized_messages = [{"type": "plain", "text": backup_text}]
                
                # 创建消息概要
                message_outline = plain_text[:30] + ("..." if len(plain_text) > 30 else "") if plain_text else ""
                if not message_outline and serialized_messages:
                    # 尝试从序列化消息中提取文本内容作为概要
                    for msg in serialized_messages:
                        if msg.get('type') == 'plain' and msg.get('text'):
                            text = msg.get('text', '')
                            message_outline = text[:30] + ("..." if len(text) > 30 else "")
                            break
                
                # 如果仍然没有概要，但有消息类型，使用类型描述
                if not message_outline:
                    # 如果仍然没有概要，使用通用消息类型描述
                    non_text_types = []
                    for msg in serialized_messages:
                        if msg.get('type') != 'plain' or not msg.get('text'):
                            non_text_types.append(msg.get('type', 'unknown'))
                    
                    if non_text_types:
                        message_outline = f"[{'、'.join(non_text_types)}]"
                    else:
                        message_outline = "[消息]"
                
                # 保存消息到缓存
                self.plugin.message_cache[task_id][session_id].append({
                    "sender_name": sender_name,
                    "sender_id": sender_id,
                    "message": serialized_messages,
                    "timestamp": timestamp,
                    "message_id": message_id,
                    "message_outline": message_outline
                })
                
                logger.info(f"已缓存消息到任务 {task_id}, 会话 {session_id}, 缓存大小: {len(self.plugin.message_cache[task_id][session_id])}")
                
                # 立即保存缓存，确保不丢失数据
                self.plugin.save_message_cache()
                
                # 检查是否达到转发阈值
                max_messages = task.get('max_messages', self.plugin.config.get('default_max_messages', 20))
                
                if len(self.plugin.message_cache[task_id][session_id]) >= max_messages:
                    logger.info(f"任务 {task_id}: 会话 {session_id} 的消息达到阈值 {max_messages}，准备转发喵～")
                    await self.plugin.forward_manager.forward_messages(task_id, session_id)
            
            if not task_matched:
                logger.debug("没有任务匹配当前消息，消息未被缓存")
        
        except Exception as e:
            logger.error(f"处理消息时出错喵: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def _should_monitor_session(self, task: Dict, event: AstrMessageEvent) -> bool:
        """判断是否应该监听此会话"""
        session_id = event.unified_msg_origin
        
        # 调试信息
        logger.debug(f"判断会话 {session_id} 是否应被监听")
        logger.debug(f"当前任务监听的群组: {task.get('monitor_groups', [])}")
        logger.debug(f"当前任务监听的私聊用户: {task.get('monitor_private_users', [])}")
        logger.debug(f"当前任务直接监听的会话: {task.get('monitor_sessions', [])}")
        
        # 最重要的修复：直接检查会话ID是否存在于任务的monitor_groups中
        if session_id in task.get('monitor_groups', []):
            logger.debug(f"会话ID {session_id} 直接存在于群组监听列表中，应监听此会话")
            return True
            
        # 检查会话ID是否存在于私聊监听列表中
        if session_id in task.get('monitor_private_users', []):
            logger.debug(f"会话ID {session_id} 直接存在于私聊监听列表中，应监听此会话")
            return True
            
        # 最后检查完整的session_id是否直接匹配monitor_sessions
        if session_id in task.get('monitor_sessions', []):
            logger.debug(f"会话ID {session_id} 直接匹配特定会话监听列表，应监听此会话")
            return True
        
        # 检查消息来源是否在监听列表中
        if event.get_message_type().name == "GROUP_MESSAGE":
            group_id = event.get_group_id()
            
            # 检查群号是否在监听列表中
            group_id_str = str(group_id) if group_id else ""
            if group_id_str and any(str(g) == group_id_str for g in task.get('monitor_groups', [])):
                logger.debug(f"群号 {group_id} 在监听列表中，应监听此会话")
                return True
            
            # 逐一比较检查会话完整ID是否可以通过拼接得到
            for g in task.get('monitor_groups', []):
                expected_id = f"aiocqhttp:GroupMessage:{g}"
                if session_id == expected_id:
                    logger.debug(f"会话ID {session_id} 匹配拼接ID {expected_id}，应监听此会话")
                    return True
            
            # 检查其他可能的格式
            possible_formats = [
                f"aiocqhttp:group_message:{group_id}",
                f"aiocqhttp:group:{group_id}",
                group_id_str
            ]
            
            for fmt in possible_formats:
                if fmt in task.get('monitor_groups', []):
                    logger.debug(f"会话ID格式 {fmt} 在监听列表中，应监听此会话")
                    return True
                
        elif event.get_message_type().name == "PRIVATE_MESSAGE":
            user_id = event.get_sender_id()
            
            # 检查QQ号是否在监听列表中
            user_id_str = str(user_id) if user_id else ""
            if user_id_str and any(str(u) == user_id_str for u in task.get('monitor_private_users', [])):
                logger.debug(f"用户ID {user_id} 在私聊监听列表中，应监听此会话")
                return True
            
            # 检查会话完整ID是否在监听列表中
            if any(session_id == f"aiocqhttp:FriendMessage:{u}" for u in task.get('monitor_private_users', [])):
                logger.debug(f"会话ID {session_id} 在私聊监听列表中，应监听此会话")
                return True
                
            # 检查其他可能的格式
            possible_formats = [
                f"aiocqhttp:private_message:{user_id}",
                f"aiocqhttp:private:{user_id}",
                f"aiocqhttp:friend_message:{user_id}",
                f"aiocqhttp:friend:{user_id}",
                user_id_str
            ]
            
            for fmt in possible_formats:
                if fmt in task.get('monitor_private_users', []):
                    logger.debug(f"会话ID格式 {fmt} 在私聊监听列表中，应监听此会话")
                    return True
        
        # 最后检查完整的session_id是否直接匹配
        if session_id in task.get('monitor_sessions', []):
            logger.debug(f"会话ID {session_id} 直接匹配监听列表，应监听此会话")
            return True
            
        logger.debug(f"会话 {session_id} 不应被监听")
        return False

    def _should_monitor_user(self, task: Dict, event: AstrMessageEvent) -> bool:
        """判断是否应该监听此用户"""
        # 如果是私聊消息，只要在监听列表中就应该监听
        message_type_name = event.get_message_type().name
        if message_type_name == "PRIVATE_MESSAGE" or message_type_name == "FRIEND_MESSAGE":
            logger.debug(f"私聊消息 ({message_type_name})，直接允许监听")
            return True
            
        # 如果是群聊消息，检查是否只监听特定用户
        group_id = event.get_group_id()
        if not group_id:
            logger.debug("群ID为空，无法确定群内特定用户，跳过监听")
            return False
            
        # 获取群中需要监听的用户列表，如果为空则监听所有用户
        group_id_str = str(group_id)
        monitored_users = task.get('monitored_users_in_groups', {}).get(group_id_str, [])
        
        # 如果没有指定用户列表，则监听所有人
        if not monitored_users:
            logger.debug(f"群 {group_id} 没有指定特定监听用户，监听所有用户")
            return True
            
        # 检查发送者是否在监听列表中
        sender_id = event.get_sender_id()
        sender_id_str = str(sender_id)
        is_monitored = any(str(u) == sender_id_str for u in monitored_users)
        
        if is_monitored:
            logger.debug(f"用户 {sender_id} 在群 {group_id} 的监听列表中，应监听")
        else:
            logger.debug(f"用户 {sender_id} 不在群 {group_id} 的监听列表中，不监听")
            
        return is_monitored