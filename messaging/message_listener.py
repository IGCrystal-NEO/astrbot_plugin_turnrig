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
            # 获取消息ID，避免重复处理
            message_id = event.message_obj.message_id
            
            # 初始化关键变量
            has_mface = False
            serialized_messages = []
            
            # 检查消息是否已经处理过
            if self._is_message_processed(message_id):
                logger.debug(f"消息 {message_id} 已经处理过，跳过")
                return
            
            # 检查是否为插件指令，如果是则跳过监听
            plain_text = event.message_str
            if plain_text:
                # 检查是否为插件的指令前缀
                if plain_text.startswith('/tr ') or plain_text.startswith('/turnrig ') or plain_text == '/tr' or plain_text == '/turnrig':
                    logger.debug(f"消息 {message_id} 是插件指令，跳过监听")
                    return
                # 检查是否为转发指令
                if plain_text.startswith('/fn ') or plain_text == '/fn':
                    logger.debug(f"消息 {message_id} 是转发指令，跳过监听")
                    return
                            
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
            
            # 在调试原始消息内容部分之后添加
            if not messages and hasattr(event.message_obj, 'message') and isinstance(event.message_obj.message, list):
                logger.warning("框架未处理message列表，直接进行处理")
                # 简单处理为文本消息
                for msg_part in event.message_obj.message:
                    if isinstance(msg_part, dict):
                        if msg_part.get('type') == 'text' and 'data' in msg_part and 'text' in msg_part['data']:
                            messages.append(Plain(text=msg_part['data']['text']))
                        elif msg_part.get('type') == 'mface':
                            # 记录发现了mface，稍后会用专门的逻辑处理
                            logger.warning(f"在message列表中发现mface项: {msg_part}")

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
            
            # 在序列化消息之前添加直接解析原始事件数据的代码
            # 强制检查消息原始数据 - 直接处理aicqhttp适配器转发的原始事件
            if hasattr(event.message_obj, '__dict__'):
                raw_obj = event.message_obj.__dict__
                logger.warning(f"强制检查原始消息对象属性: {list(raw_obj.keys())}")
                
                # 直接检查是否有特殊表情相关结构
                if 'message' in raw_obj and isinstance(raw_obj['message'], list):
                    logger.warning("发现message列表，开始检查特殊表情")
                    for msg in raw_obj['message']:
                        if isinstance(msg, dict) and msg.get('type') == 'mface':
                            has_mface = True
                            logger.warning(f"直接从__dict__找到mface: {msg}")
                            
                            # 提取数据
                            data = msg.get('data', {})
                            url = data.get('url', '')
                            summary = data.get('summary', '[表情]')
                            emoji_id = data.get('emoji_id', '')
                            package_id = data.get('emoji_package_id', '')
                            key = data.get('key', '')
                            
                            # 创建图像类型的表情消息
                            mface_data = {
                                "type": "image",
                                "url": url,
                                "is_mface": True,
                                "is_gif": True,
                                "flash": True,
                                "summary": summary,
                                "emoji_id": emoji_id,
                                "emoji_package_id": package_id,
                                "key": key
                            }
                            
                            # 添加到序列化消息列表
                            serialized_messages.append(mface_data)
                            logger.warning(f"从原始对象直接添加特殊表情: {summary} -> {url}")

            # 在开始处理每个任务之前添加
            # 开始激进检测模式，查找所有可能的mface内容
            logger.warning(f"开始激进检测mface，原始对象类型: {type(event.message_obj)}")
            # 打印所有可能的属性
            for attr_name in dir(event.message_obj):
                if not attr_name.startswith('_'):
                    try:
                        attr_value = getattr(event.message_obj, attr_name)
                        if 'mface' in str(attr_value).lower():
                            logger.warning(f"在属性 {attr_name} 中发现可能的mface信息: {attr_value}")
                    except:
                        pass

            # 处理每个任务
            task_matched = False
            matched_task_ids = []
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
                matched_task_ids.append(task_id)
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
                
                # 开始诊断：打印完整的原始消息对象
                logger.debug(f"详细消息对象: {event.message_obj.__dict__ if hasattr(event.message_obj, '__dict__') else 'No __dict__'}")
                
                # 确保消息非空 - 优先使用各种方式确保获取到内容
                has_content = False
                
                # 序列化消息 - 保存之前已探测到的特殊表情
                mface_components = [msg for msg in serialized_messages if msg.get('is_mface')]
                
                # 重新序列化常规消息
                task_serialized_messages = serialize_message(messages)
                
                # 合并普通消息和特殊表情消息
                for mface_msg in mface_components:
                    if mface_msg not in task_serialized_messages:
                        task_serialized_messages.append(mface_msg)
                
                # 更新序列化消息，保留已发现的特殊表情
                serialized_messages = task_serialized_messages
                
                # 重置特殊表情标记，单独检测每个任务
                task_has_mface = has_mface
                
                # 方法1: 直接从message属性获取
                if not task_has_mface and hasattr(event.message_obj, 'message') and isinstance(event.message_obj.message, list):
                    logger.warning(f"检查message列表中的mface: {event.message_obj.message}")
                    for msg in event.message_obj.message:
                        if isinstance(msg, dict) and msg.get('type') == 'mface':
                            task_has_mface = True
                            logger.warning(f"从message列表找到mface: {msg}")
                            
                            # 提取数据
                            data = msg.get('data', {})
                            url = data.get('url', '')
                            summary = data.get('summary', '[表情]')
                            emoji_id = data.get('emoji_id', '')
                            package_id = data.get('emoji_package_id', '')
                            key = data.get('key', '')
                            
                            # 创建图像类型的表情消息
                            mface_data = {
                                "type": "image",
                                "url": url,
                                "is_mface": True,
                                "is_gif": True,
                                "flash": True,
                                "summary": summary,
                                "emoji_id": emoji_id,
                                "emoji_package_id": package_id,
                                "key": key
                            }
                            
                            # 添加到序列化消息列表
                            serialized_messages.append(mface_data)
                            logger.warning(f"直接添加特殊表情: {summary} -> {url}")

                # 从原始消息中提取图片文件名和处理特殊表情
                if not task_has_mface and hasattr(event.message_obj, 'raw_message') and event.message_obj.raw_message:
                    try:
                        raw_message = event.message_obj.raw_message
                        logger.warning(f"原始消息类型: {type(raw_message)}")
                        
                        # 方法2: 检查raw_message对象结构
                        msg_list = []
                        
                        # 先尝试从raw_message对象中获取message列表
                        if hasattr(raw_message, 'message') and isinstance(raw_message.message, list):
                            msg_list = raw_message.message
                            logger.warning(f"从raw_message.message获取列表: {msg_list}")
                        # 再尝试从raw_message字典中获取message列表
                        elif isinstance(raw_message, dict) and 'message' in raw_message:
                            msg_list = raw_message['message']
                            logger.warning(f"从raw_message字典获取列表: {msg_list}")
                            
                        # 处理获取到的消息列表
                        for raw_msg in msg_list:
                            # 处理图片
                            if isinstance(raw_msg, dict) and raw_msg.get('type') == 'image' and 'data' in raw_msg:
                                extracted_filename = raw_msg['data'].get('filename')
                                if extracted_filename:
                                    logger.debug(f"从原始消息提取到filename: {extracted_filename}")
                                    # 将filename添加到对应的图片消息组件
                                    for i, msg in enumerate(serialized_messages):
                                        if msg.get('type') == 'image':
                                            serialized_messages[i]['filename'] = extracted_filename
                                            logger.debug(f"已将filename {extracted_filename} 添加到图片消息")
                                            break
                            
                            # 处理特殊表情(mface)
                            elif isinstance(raw_msg, dict) and raw_msg.get('type') == 'mface':
                                task_has_mface = True
                                logger.warning(f"从raw_message列表找到mface: {raw_msg}")
                                
                                # 提取表情数据
                                data = raw_msg.get('data', {})
                                url = raw_msg.get('url', '') or data.get('url', '')
                                summary = raw_msg.get('summary', '') or data.get('summary', '[表情]')
                                emoji_id = raw_msg.get('emoji_id', '') or data.get('emoji_id', '')
                                package_id = raw_msg.get('emoji_package_id', '') or data.get('emoji_package_id', '')
                                key = raw_msg.get('key', '') or data.get('key', '')
                                
                                # 创建一个图片类型的消息，添加特殊标记
                                mface_as_image = {
                                    "type": "image",
                                    "url": url,
                                    "is_mface": True,  # 标记为特殊表情
                                    "is_gif": True,    # 标记为GIF
                                    "flash": True,     # 使用闪图模式
                                    "summary": summary,
                                    "emoji_id": emoji_id,
                                    "emoji_package_id": package_id,
                                    "key": key
                                }
                                
                                # 添加到序列化消息列表
                                serialized_messages.append(mface_as_image)
                                logger.warning(f"添加特殊表情: {summary} -> {url}")
                        
                        # 方法3: 尝试从raw_message字符串中解析mface
                        if not task_has_mface and hasattr(event.message_obj, 'raw_message'):
                            raw_str = str(event.message_obj.raw_message)
                            # 扩展检测条件，包含更多可能的标识
                            if '[CQ:mface' in raw_str or 'mface' in raw_str.lower():
                                logger.warning(f"从字符串解析mface: {raw_str}")
                                
                                # 尝试从字符串中提取URL和名称
                                url = ""
                                summary = "[表情]"
                                
                                # 尝试正则匹配URL
                                import re
                                url_match = re.search(r'url=(https?://[^,\]]+)', raw_str)
                                if url_match:
                                    url = url_match.group(1)
                                    logger.warning(f"从字符串中提取到URL: {url}")
                                
                                # 尝试提取summary
                                summary_match = re.search(r'summary=([^,\]]+)', raw_str)
                                if summary_match:
                                    summary = summary_match.group(1)
                                    logger.warning(f"从字符串中提取到summary: {summary}")
                                
                                # 创建一个通用的mface表情
                                mface_as_image = {
                                    "type": "image",
                                    "url": url,
                                    "is_mface": True,
                                    "is_gif": True,
                                    "flash": True,
                                    "summary": summary
                                }
                                
                                # 添加到序列化消息列表
                                serialized_messages.append(mface_as_image)
                                logger.warning(f"从字符串解析添加特殊表情: {summary} -> {url}")
                                task_has_mface = True
                    except Exception as e:
                        logger.error(f"处理图片或特殊表情时出错: {e}", exc_info=True)

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
                        # 新增: 为特殊表情添加专门的概要
                        elif msg.get('type') == 'image' and msg.get('is_mface') and msg.get('summary'):
                            message_outline = f"[表情:{msg.get('summary')}]"
                            break
                
                # 如果仍然没有概要，但有消息类型，使用类型描述
                if not message_outline:
                    # 如果仍然没有概要，使用通用消息类型描述
                    non_text_types = []
                    for msg in serialized_messages:
                        if msg.get('type') != 'plain' or not msg.get('text'):
                            msg_type = msg.get('type', 'unknown')
                            # 新增: 为特殊表情提供友好的类型名称
                            if msg.get('is_mface'):
                                non_text_types.append('特殊表情')
                            else:
                                non_text_types.append(msg_type)
                    
                    if non_text_types:
                        message_outline = f"[{'、'.join(non_text_types)}]"
                    else:
                        message_outline = "[消息]"

                # 在保存消息到缓存之前，添加特殊标记
                if task_has_mface or has_mface:
                    message_outline = message_outline or "[特殊表情]"
                    # 添加特殊标记
                    for msg in serialized_messages:
                        if msg.get('is_mface'):
                            # 确保所有必要的字段都存在
                            if not msg.get('summary'):
                                msg['summary'] = "[表情]"
                            if not msg.get('is_gif'):
                                msg['is_gif'] = True
                            if not msg.get('flash'):
                                msg['flash'] = True
                
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
            
            # 标记消息为已处理，按任务ID分组存储
            self._mark_message_processed(message_id, matched_task_ids)
        
        except Exception as e:
            logger.error(f"处理消息时出错喵: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def _is_message_processed(self, message_id: str) -> bool:
        """检查消息是否已经处理过，使用新的按任务分组的结构"""
        # 检查所有任务的processed_message_ids
        for key in self.plugin.config:
            if key.startswith('processed_message_ids_'):
                message_ids = self.plugin.config[key]
                for msg in message_ids:
                    if isinstance(msg, dict) and msg.get('id') == message_id:
                        return True
                    elif msg == message_id:  # 兼容旧格式
                        return True
        return False
    
    def _mark_message_processed(self, message_id: str, task_ids: List[str]):
        """将消息标记为已处理，使用新的按任务分组的结构
        
        Args:
            message_id: 消息ID
            task_ids: 匹配到的任务ID列表
        """
        timestamp = int(time.time())
        
        # 为每个匹配的任务添加消息ID
        for task_id in task_ids:
            key = f'processed_message_ids_{task_id}'
            
            # 如果键不存在，创建一个空列表
            if key not in self.plugin.config:
                self.plugin.config[key] = []
                
            # 添加消息ID和时间戳
            self.plugin.config[key].append({
                'id': message_id,
                'timestamp': timestamp
            })
        
        # 保存配置
        self.plugin.save_config_file()

    def _should_monitor_session(self, task: Dict, event: AstrMessageEvent) -> bool:
        """判断是否应该监听此会话"""
        session_id = event.unified_msg_origin
        
        # 调试信息
        logger.debug(f"判断会话 {session_id} 是否应被监听")
        logger.debug(f"当前任务监听的群组: {task.get('monitor_groups', [])}")
        logger.debug(f"当前任务监听的私聊用户: {task.get('monitor_private_users', [])}")
        logger.debug(f"当前任务直接监听的会话: {task.get('monitor_sessions', [])}")
        
        # 新增：检查群是否在monitored_users_in_groups中配置了特定用户监听
        # 处理monitored_users_in_groups中使用完整会话ID作为键的情况
        if event.get_message_type().name == "GROUP_MESSAGE":
            group_id = event.get_group_id()
            group_id_str = str(group_id) if group_id else ""
            
            # 检查纯群号格式
            if group_id_str and group_id_str in task.get('monitored_users_in_groups', {}):
                logger.debug(f"群 {group_id} 已配置特定用户监听，应监听此会话")
                return True
                
            # 检查完整会话ID格式 - 关键修改！
            if session_id in task.get('monitored_users_in_groups', {}):
                logger.debug(f"会话ID {session_id} 直接存在于群内用户监听配置中，应监听此会话")
                return True
        
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
        
        # 最后再检查一次完整的session_id是否直接匹配
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
            
        # 获取群中需要监听的用户列表
        group_id_str = str(group_id)
        session_id = event.unified_msg_origin
        
        # 重要修改：同时检查纯群号和完整会话ID两种格式
        monitored_users = task.get('monitored_users_in_groups', {}).get(group_id_str, [])
        
        # 如果使用纯群号没有找到，尝试使用完整会话ID
        if not monitored_users and session_id in task.get('monitored_users_in_groups', {}):
            monitored_users = task.get('monitored_users_in_groups', {}).get(session_id, [])
        
        # 增加日志，显示该群中监听的用户列表
        logger.debug(f"群 {group_id} 中监听的用户列表: {monitored_users}")
        
        # 如果没有指定用户列表，则监听所有人
        if not monitored_users:
            logger.debug(f"群 {group_id} 没有指定特定监听用户，监听所有用户")
            return True
            
        # 检查发送者是否在监听列表中
        sender_id = event.get_sender_id()
        sender_id_str = str(sender_id)
        
        # 增加日志，显示当前消息发送者ID
        logger.debug(f"检查发送者 {sender_id_str} 是否在监听列表中")
        
        is_monitored = False
        for user_id in monitored_users:
            user_id_str = str(user_id)
            if user_id_str == sender_id_str:
                is_monitored = True
                logger.debug(f"匹配成功: 用户ID {sender_id_str} 与监听列表中的 {user_id_str} 匹配")
                break
        
        if is_monitored:
            logger.debug(f"用户 {sender_id} 在群 {group_id} 的监听列表中，应监听")
        else:
            logger.debug(f"用户 {sender_id} 不在群 {group_id} 的监听列表中，不监听")
            
        return is_monitored