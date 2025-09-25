"""
基础命令处理器喵～ 🎯
提供所有命令处理器共用的基础功能和工具方法！

包含：
- 权限检查
- 参数验证
- 会话ID处理
- 任务验证
- 通用工具方法
"""

import time
from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent

# 从utils导入会话格式化工具
from ...utils.session_formatter import normalize_session_id


class BaseCommandHandler:
    """
    基础命令处理器类喵～ 🎮
    提供所有命令处理器的共同功能！
    
    这个基类包含：
    - 🔧 参数验证和解析
    - ✅ 权限检查机制
    - 📋 任务管理辅助
    - 🔍 会话ID处理
    - 🧹 数据迁移和清理
    
    Note:
        所有的命令处理器都应该继承这个基类喵！ 💫
    """
    
    def __init__(self, plugin_instance):
        """
        初始化基础命令处理器喵～ 🎮
        
        Args:
            plugin_instance: TurnRigPlugin的实例，提供配置和服务喵～
        """
        self.plugin = plugin_instance
        
        # 迁移旧格式的processed_message_ids到新格式喵～ 🔄
        self._migrate_processed_message_ids()
    
    def _migrate_processed_message_ids(self):
        """
        将旧格式的processed_message_ids迁移到新格式喵～ 🔄
        把全局的消息ID记录按任务分组存储！
        
        Note:
            这样可以更好地管理不同任务的消息处理记录喵～ ✨
        """
        if "processed_message_ids" in self.plugin.config and isinstance(
            self.plugin.config["processed_message_ids"], list
        ):
            logger.info("检测到旧格式的processed_message_ids，正在迁移到新格式喵～ 🔄")
            
            # 获取所有任务ID喵～ 📋
            task_ids = [str(task.get("id", "")) for task in self.plugin.config["tasks"]]
            
            if task_ids:
                # 如果有任务，将所有消息ID分配给第一个任务（简单处理）喵～ 📤
                first_task_id = task_ids[0]
                self.plugin.config[f"processed_message_ids_{first_task_id}"] = [
                    {"id": msg_id, "timestamp": int(time.time())}
                    for msg_id in self.plugin.config["processed_message_ids"]
                ]
                logger.info(
                    f"已将 {len(self.plugin.config['processed_message_ids'])} 个消息ID迁移到任务 {first_task_id} 喵～ ✅"
                )
            
            # 删除旧的全局processed_message_ids喵～ 🗑️
            del self.plugin.config["processed_message_ids"]
            self.plugin.save_config_file()
            logger.info("迁移完成喵～ 🎉")
    
    def _ensure_full_session_id(self, session_id):
        """
        确保会话ID是完整格式喵～ 🔍
        把简短的会话ID转换为标准格式！
        
        Args:
            session_id: 原始会话ID喵
        
        Returns:
            标准化后的完整会话ID喵～
        
        Note:
            会检测并修复各种不规范的ID格式喵！ 🔧
        """
        if not session_id:
            return session_id
        
        # 确保session_id是字符串类型喵～ 📝
        session_id = str(session_id)
        
        # 处理单独的"群聊"或"私聊"关键词喵～ ⚠️
        if session_id == "群聊" or session_id == "私聊":
            logger.warning(
                f"检测到单独的'{session_id}'关键词，需要提供完整的会话ID格式喵：{session_id} <ID> 😿"
            )
            return session_id
        
        # 检查session_id是否含有无效空格喵～ 🧹
        session_id = session_id.strip()
        
        # 正常处理流程喵～ ⚙️
        normalized_id = normalize_session_id(session_id)
        
        # 检查是否包含两个冒号，表示是完整会话ID喵～ 🔍
        if normalized_id.count(":") == 2:
            return normalized_id
        else:
            logger.warning(
                f"会话ID '{session_id}' 不是有效的完整会话ID格式，已转换为 '{normalized_id}' 但可能仍然无效喵～ ⚠️"
            )
            return normalized_id
    
    async def _check_admin(
        self,
        event: AstrMessageEvent,
        error_msg: str = "只有管理员才能执行此操作喵～ 🚫",
    ):
        """
        检查用户是否为管理员喵～ 👮
        验证命令执行权限的安全守卫！
        
        Args:
            event: 消息事件对象喵
            error_msg: 权限不足时的错误提示喵
        
        Returns:
            tuple: (是否是管理员, 响应消息) 喵～
        
        Note:
            所有重要操作都需要管理员权限喵！ 🔒
        """
        if not event.is_admin():
            return False, event.plain_result(error_msg)
        return True, None
    
    def _get_validated_task(
        self, event: AstrMessageEvent, task_id: str, need_reply: bool = True
    ):
        """
        获取并验证任务是否存在喵～ 📋
        安全地获取任务配置！
        
        Args:
            event: 消息事件对象喵
            task_id: 任务ID喵
            need_reply: 是否需要错误回复喵
        
        Returns:
            tuple: (任务对象, 错误消息) 喵～
        
        Note:
            如果任务不存在会给出友好提示喵！ ❓
        """
        if not task_id:
            if need_reply:
                return None, "请提供任务ID喵～ 🆔"
            return None, None
        
        task = self.plugin.get_task_by_id(task_id)
        if not task:
            if need_reply:
                return None, f"未找到ID为 {task_id} 的任务喵～ ❌"
            return None, None
        
        return task, None
    
    def _parse_session_id_from_command(
        self, event, cmd_text, chat_type, chat_id, task_id=None, command_name=""
    ):
        """
        从命令参数中提取和标准化会话ID喵～ 🔍
        智能解析各种格式的会话ID参数！
        
        Args:
            event: 消息事件对象喵
            cmd_text: 原始命令文本喵
            chat_type: 聊天类型参数喵
            chat_id: 聊天ID参数喵
            task_id: 任务ID，用于错误消息喵
            command_name: 命令名称，用于错误消息格式化喵
        
        Returns:
            tuple: (完整会话ID, 错误回复) 喵～
            成功时错误回复为None，失败时完整会话ID为None喵
        
        Note:
            支持多种ID格式的智能识别和转换喵！ ✨
        """
        # 确保类型转换喵～ 🔄
        if chat_type is not None:
            chat_type = str(chat_type)
        if chat_id is not None:
            chat_id = str(chat_id)
        
        full_session_id = None
        
        # 检查是否直接传入了完整会话ID (带冒号的格式)喵～ 🎯
        if chat_type and ":" in chat_type:
            # 直接使用chat_type作为会话ID喵～ 📋
            full_session_id = self._ensure_full_session_id(chat_type)
            logger.info(f"检测到完整会话ID喵: {full_session_id} ✨")
        # 检查是否为纯数字ID喵～ 🔢
        elif chat_type and chat_type.isdigit() and not chat_id:
            # 发现纯数字ID，要求用户明确指定群聊或私聊喵～ ⚠️
            error_msg = f"请明确指定会话类型喵～ 🤔\n正确格式：/turnrig {command_name} <任务ID> 群聊/私聊 <会话ID>"
            if task_id:
                error_msg += (
                    f"\n例如：/turnrig {command_name} {task_id} 群聊 {chat_type}"
                )
            return None, event.plain_result(error_msg)
        else:
            # 分析原始命令文本喵～ 📄
            parts = cmd_text.split()
            # 查找 "群聊" 或 "私聊" 关键字喵～ 🔍
            for i, part in enumerate(parts):
                if part in ["群聊", "私聊"] and i + 1 < len(parts):
                    # 构造会话ID组合喵～ 🔗
                    session_id_text = f"{part} {parts[i + 1]}"
                    full_session_id = self._ensure_full_session_id(session_id_text)
                    logger.info(
                        f"从命令文本提取会话ID喵: {session_id_text} -> {full_session_id} ✅"
                    )
                    break
            
            # 如果上面的方法失败，尝试常规处理流程喵～ 🔄
            if not full_session_id:
                # 检查基本参数喵～ 📋
                if not chat_type or chat_type not in ["群聊", "私聊"]:
                    return None, event.plain_result(
                        f"请明确指定会话类型喵～ 🤔\n正确格式：/turnrig {command_name} <任务ID> 群聊/私聊 <会话ID>"
                    )
                
                if not chat_id:
                    return None, event.plain_result(
                        f"请提供{chat_type}ID喵～ 🆔\n正确格式：/turnrig {command_name} <任务ID> {chat_type} <会话ID>"
                    )
                
                # 使用参数构造会话ID喵～ 🏗️
                session_id_text = f"{chat_type} {chat_id}"
                full_session_id = self._ensure_full_session_id(session_id_text)
                logger.info(
                    f"从参数构造会话ID喵: {session_id_text} -> {full_session_id} ✅"
                )
        
        if not full_session_id:
            return None, event.plain_result(
                f"无法识别会话ID格式喵～ 😿\n正确格式：/turnrig {command_name} <任务ID> 群聊/私聊 <会话ID>"
            )
        
        return full_session_id, None
    
    async def _validate_command_params(
        self,
        event,
        task_id,
        error_msg="只有管理员才能执行此操作喵～ 🚫",
        command_name="",
    ):
        """
        验证通用命令参数喵～ 🔍
        包括管理员权限和任务ID的安全检查！
        
        Args:
            event: 消息事件对象喵
            task_id: 任务ID参数喵
            error_msg: 权限错误提示喵
            command_name: 命令名称，用于错误消息格式化喵
        
        Returns:
            tuple: (任务对象, 命令文本, 错误回复) 喵～
            成功时错误回复为None喵
        
        Note:
            所有重要命令都会经过这里的安全验证喵！ 🛡️
        """
        # 权限检查喵～ 👮
        is_admin, response = await self._check_admin(event, error_msg)
        if not is_admin:
            return None, None, response
        
        # 获取并验证任务
        task, err_msg = self._get_validated_task(event, task_id)
        if err_msg:
            if command_name:
                err_msg += (
                    f"\n正确格式：/turnrig {command_name} <任务ID> 群聊/私聊 <会话ID>"
                )
            return None, None, event.plain_result(err_msg)
        
        # 获取原始命令文本用于日志
        cmd_text = event.message_str
        if not cmd_text and hasattr(event.message_obj, "raw_message"):
            cmd_text = str(event.message_obj.raw_message)
        logger.info(f"处理命令: {cmd_text}")
        return task, cmd_text, None
    
    def _update_session_list(
        self, task, session_id, list_name, action="add", session_type="会话"
    ):
        """
        更新任务的会话列表喵～ 📝
        智能添加或删除监听和目标会话！
        
        Args:
            task: 任务对象喵
            session_id: 完整会话ID（如 aiocqhttp:GroupMessage:123456）喵
            list_name: 列表名称，如'monitor_groups', 'target_sessions'等喵
            action: 操作类型，"add" 或 "remove"喵
            session_type: 会话类型描述，用于响应消息喵
        
        Returns:
            str: 操作结果消息喵～
        
        Note:
            会自动识别群聊和私聊，存储到正确的列表中喵！ ✨
        """
        task_name = task.get("name", "未命名")
        
        # 解析完整会话ID以确定应该存储到哪个列表喵～ 🔍
        parsed_info = self._parse_session_id_info(session_id)
        if not parsed_info:
            return f"无法解析会话ID格式喵: {session_id}，请使用完整的会话ID格式 😿"
        
        actual_list_name = list_name
        actual_id = parsed_info["id"]
        
        # 根据会话类型决定实际的列表名称和存储的ID喵～ 🎯
        if list_name in ["monitor_sessions", "monitor_groups", "monitor_private_users"]:
            if parsed_info["is_group"]:
                actual_list_name = "monitor_groups"
                session_type = "群聊"
            else:
                actual_list_name = "monitor_private_users"
                session_type = "私聊用户"
            
            # 对于监听列表，我们存储纯ID而不是完整会话ID喵～ 💾
            storage_id = actual_id
            logger.info(
                f"监听会话喵: {session_id} -> 存储到 {actual_list_name}: {storage_id} ✅"
            )
        else:
            # 对于其他列表（如target_sessions），存储完整会话ID喵～ 🎯
            storage_id = session_id
            logger.info(
                f"目标会话喵: {session_id} -> 存储到 {actual_list_name}: {storage_id} ✅"
            )
        
        # 确保列表存在喵～ 📋
        if actual_list_name not in task:
            task[actual_list_name] = []
        
        # 添加操作喵～ ➕
        if action == "add":
            if storage_id not in task[actual_list_name]:
                task[actual_list_name].append(storage_id)
                self.plugin.save_config_file()
                return f"已将{session_type} {actual_id} 添加到任务 [{task_name}] 的 {actual_list_name} 列表中喵～ ✅"
            else:
                return f"{session_type} {actual_id} 已经在任务 [{task_name}] 的 {actual_list_name} 列表中了喵～ ⚠️"
        
        # 删除操作喵～ ➖
        elif action == "remove":
            if storage_id in task[actual_list_name]:
                task[actual_list_name].remove(storage_id)
                self.plugin.save_config_file()
                return f"已将{session_type} {actual_id} 从任务 [{task_name}] 的 {actual_list_name} 列表中移除喵～ ✅"
            else:
                return f"{session_type} {actual_id} 不在任务 [{task_name}] 的 {actual_list_name} 列表中喵～ ❓"
        
        return f"未知操作喵: {action} 😿"
    
    def _parse_session_id_info(self, session_id):
        """
        解析完整会话ID喵～ 🔍
        提取平台、类型和ID等详细信息！
        
        Args:
            session_id: 完整会话ID，如 'aiocqhttp:GroupMessage:123456'喵
        
        Returns:
            dict: 包含解析结果的字典喵～
                {
                    'platform': 'aiocqhttp',
                    'message_type': 'GroupMessage',
                    'id': '123456',
                    'is_group': True/False,
                    'full_id': 'aiocqhttp:GroupMessage:123456'
                }
                如果解析失败则返回None喵
        
        Note:
            支持标准的三段式会话ID格式喵！ 📋
        """
        if not session_id or not isinstance(session_id, str):
            return None
        
        # 检查是否为完整会话ID格式（platform:type:id）喵～ 🔍
        parts = session_id.split(":")
        if len(parts) != 3:
            logger.warning(
                f"会话ID格式不正确喵: {session_id}，期望格式: platform:type:id 😿"
            )
            return None
        
        platform, message_type, id_part = parts
        
        # 判断是否为群聊喵～ 👥
        is_group = "group" in message_type.lower()
        
        return {
            "platform": platform,
            "message_type": message_type,
            "id": id_part,
            "is_group": is_group,
            "full_id": session_id,
        }
    
    def _extract_session_id(
        self,
        event: AstrMessageEvent,
        cmd_text: str = None,
        chat_type: str = None,
        chat_id: str = None,
        args=None,
    ):
        """从命令参数中提取会话ID"""
        # 获取命令文本
        if not cmd_text:
            cmd_text = event.message_str
            if not cmd_text and hasattr(event.message_obj, "raw_message"):
                cmd_text = str(event.message_obj.raw_message)
        
        # 初始化会话ID
        session_id = None
        
        # 如果chat_type和chat_id都存在，组合成会话ID
        if chat_type in ["群聊", "私聊"] and chat_id:
            session_id = f"{chat_type} {chat_id}"
            if args:  # 如果还有额外参数
                session_id = f"{session_id} {' '.join(args)}"
            logger.info(f"从参数中检测到会话ID: {session_id}")
        
        # 如果只有chat_type，可能是完整的会话ID已经作为一个参数传入
        elif chat_type and not chat_id:
            session_id = chat_type
            logger.info(f"可能的完整会话ID: {session_id}")
        
        # 如果无法从参数中获取完整的会话ID，尝试从命令文本中解析
        if not session_id or session_id in ["群聊", "私聊"]:
            parts = cmd_text.split()
            # 查找"群聊"或"私聊"关键词
            for i, part in enumerate(parts):
                if part in ["群聊", "私聊"] and i + 1 < len(parts):
                    session_id = f"{part} {parts[i + 1]}"
                    logger.info(f"从命令文本中提取会话ID: {session_id}")
                    break
        
        # 如果提取到会话ID，进行标准化
        if session_id:
            full_session_id = self._ensure_full_session_id(session_id)
            logger.info(f"标准化会话ID: {session_id} -> {full_session_id}")
            return full_session_id
        
        return None
