import time

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent

# 更新导入路径喵～ 📦
from ..utils.session_formatter import normalize_session_id


class CommandHandlers:
    """
    命令处理器喵～ 🎯
    专门负责处理各种TurnRig插件命令的可爱小助手！ ฅ(^•ω•^ฅ

    这个处理器会帮你：
    - 🔧 解析和验证命令参数
    - ✅ 检查管理员权限
    - 📋 管理任务的增删改查
    - 👂 处理监听和转发配置
    - 🧹 清理过期数据

    Note:
        所有的命令都会经过精心处理，确保安全执行喵！ 💫
    """

    def __init__(self, plugin_instance):
        """
        初始化命令处理器喵～ 🎮
        负责处理各种插件命令的智能助手！

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

    # turnrig 命令组处理方法
    async def handle_list_tasks(self, event: AstrMessageEvent):
        """
        列出所有转发任务喵～ 📋
        显示当前配置的所有任务信息！

        Args:
            event: 消息事件对象喵

        Returns:
            包含任务列表的回复消息喵～

        Note:
            会显示任务状态、监听数量、目标数量等详细信息喵！ ✨
        """
        tasks = self.plugin.config.get("tasks", [])

        if not tasks:
            return event.plain_result("当前没有配置任何转发任务喵～ 😿")

        result = "当前配置的转发任务列表喵～ 📋：\n"
        for i, task in enumerate(tasks):
            status = "✅启用" if task.get("enabled", True) else "❌禁用"
            result += f"{i + 1}. [{status}] {task.get('name', '未命名')} (ID: {task.get('id')})\n"
            result += f"  👂监听: {len(task.get('monitor_groups', []))} 个群, {len(task.get('monitor_private_users', []))} 个私聊用户\n"

            # 显示群内监听的用户数喵～ 👥
            total_group_users = sum(
                len(users)
                for users in task.get("monitored_users_in_groups", {}).values()
            )
            result += f"  👤监听群内用户: {total_group_users} 个\n"

            result += f"  🎯目标: {', '.join(task.get('target_sessions', ['无']))}\n"
            result += f"  📊消息阈值: {task.get('max_messages', self.plugin.config.get('default_max_messages', 20))}\n"

        return event.plain_result(result)

    async def handle_status(self, event: AstrMessageEvent, task_id: str = None):
        """查看特定任务的缓存状态喵～"""
        if task_id is None:
            # 显示所有任务的状态统计
            if not self.plugin.message_cache:
                return event.plain_result("当前没有任何消息缓存喵～")

            result = "消息缓存状态喵～：\n"
            for tid, sessions in self.plugin.message_cache.items():
                task = self.plugin.get_task_by_id(tid)
                task_name = task.get("name", "未知任务") if task else f"ID: {tid}"
                session_count = len(sessions)
                total_msgs = sum(len(msgs) for msgs in sessions.values())

                result += (
                    f"- {task_name}: {session_count} 个会话, 共 {total_msgs} 条消息\n"
                )

            return event.plain_result(result)
        else:
            # 显示指定任务的详细缓存
            if task_id not in self.plugin.message_cache:
                return event.plain_result(f"未找到任务 {task_id} 的消息缓存喵～")

            task = self.plugin.get_task_by_id(task_id)
            task_name = task.get("name", "未知任务") if task else f"ID: {task_id}"

            result = f"任务 {task_name} 的消息缓存状态喵～：\n"
            for session_id, messages in self.plugin.message_cache[task_id].items():
                result += f"- 会话 {session_id}: {len(messages)} 条消息\n"

            return event.plain_result(result)

    async def handle_create_task(self, event: AstrMessageEvent, task_name: str = None):
        """创建新的转发任务喵～"""
        # 权限检查
        is_admin, response = await self._check_admin(
            event, "只有管理员才能创建转发任务喵～"
        )
        if not is_admin:
            return response

        if not task_name:
            task_name = f"新任务_{len(self.plugin.config['tasks']) + 1}"

        # 生成顺序ID，从当前最大ID+1开始
        task_id = str(self.plugin.get_max_task_id() + 1)
        new_task = {
            "id": task_id,
            "name": task_name,
            "monitor_groups": [],
            "monitor_private_users": [],
            "monitored_users_in_groups": {},
            "target_sessions": [],
            "max_messages": self.plugin.config.get("default_max_messages", 20),
            "enabled": True,
        }

        self.plugin.config["tasks"].append(new_task)
        self.plugin.save_config_file()

        # 确保消息中的换行符正确显示
        return event.plain_result(
            f"已创建新的转发任务 [{task_name}]，ID: {task_id}\n\n"
            f"请使用以下命令添加监听源和目标：\n"
            f"/turnrig monitor {task_id} 群聊/私聊 <会话ID>\n"
            f"/turnrig target {task_id} 群聊/私聊 <会话ID>"
        )

    async def handle_delete_task(self, event: AstrMessageEvent, task_id: str = None):
        """处理删除任务的指令"""
        # 管理员权限检查
        is_admin, response = await self._check_admin(
            event, "只有管理员可以删除任务喵～"
        )
        if not is_admin:
            return response

        if not task_id:
            return event.plain_result(
                "请提供要删除的任务ID喵～\n用法: /turnrig delete <任务ID>"
            )

        # 查找并删除任务
        task_id_str = str(task_id)  # 确保使用字符串比较
        deleted = False
        tasks_to_keep = []

        # 使用列表推导而不是直接修改遍历中的列表
        for task in self.plugin.config["tasks"]:
            if str(task.get("id", "")) != task_id_str:
                tasks_to_keep.append(task)
            else:
                deleted = True
                task_name = task.get("name", "未命名")
                logger.info(f"找到要删除的任务: {task_name} (ID: {task_id})")

        # 只有在确实找到并删除了任务后才更新配置
        if deleted:
            # 更新配置中的任务列表
            self.plugin.config["tasks"] = tasks_to_keep

            # 删除相关的消息缓存
            if task_id_str in self.plugin.message_cache:
                del self.plugin.message_cache[task_id_str]
                logger.info(f"已删除任务 {task_id} 的消息缓存")

            # 删除任务特定的processed_message_ids
            processed_msg_key = f"processed_message_ids_{task_id_str}"
            if processed_msg_key in self.plugin.config:
                logger.info(f"删除任务 {task_id} 的processed_message_ids")
                del self.plugin.config[processed_msg_key]

            # 立即保存更新后的配置和缓存
            self.plugin.save_config_file()
            self.plugin.save_message_cache()

            # 强制重新加载缓存，以确保删除操作生效
            self.plugin.message_cache = (
                self.plugin.config_manager.load_message_cache() or {}
            )

            logger.info(f"已成功删除任务 {task_id} 并保存配置")
            return event.plain_result(f"已成功删除任务 {task_id} 喵～")
        else:
            logger.warning(f"未找到ID为 {task_id} 的任务")
            return event.plain_result(
                f"未找到ID为 {task_id} 的任务喵～，请检查任务ID是否正确"
            )

    async def handle_enable_task(self, event: AstrMessageEvent, task_id: str = None):
        """启用转发任务喵～"""
        # 权限检查
        is_admin, response = await self._check_admin(
            event, "只有管理员才能启用转发任务喵～"
        )
        if not is_admin:
            return response

        # 获取并验证任务
        task, error_msg = self._get_validated_task(event, task_id)
        if error_msg:
            return event.plain_result(error_msg)

        task["enabled"] = True
        self.plugin.save_config_file()

        return event.plain_result(f"已启用任务 [{task.get('name')}]，ID: {task_id}")

    async def handle_disable_task(self, event: AstrMessageEvent, task_id: str = None):
        """禁用转发任务喵～"""
        # 权限检查
        is_admin, response = await self._check_admin(
            event, "只有管理员才能禁用转发任务喵～"
        )
        if not is_admin:
            return response

        # 获取并验证任务
        task, error_msg = self._get_validated_task(event, task_id)
        if error_msg:
            return event.plain_result(error_msg)

        task["enabled"] = False
        self.plugin.save_config_file()

        return event.plain_result(f"已禁用任务 [{task.get('name')}]，ID: {task_id}")

    async def handle_add_monitor(
        self,
        event: AstrMessageEvent,
        task_id: str = None,
        chat_type: str = None,
        chat_id: str = None,
        *args,
    ):
        """添加监听源喵～"""
        # 验证参数
        task, cmd_text, error = await self._validate_command_params(
            event, task_id, "只有管理员才能添加监听源喵～", "monitor"
        )
        if error:
            return error

        # 解析会话ID
        session_id, error = self._parse_session_id_from_command(
            event, cmd_text, chat_type, chat_id, task_id, "monitor"
        )
        if error:
            return error
        # 根据会话类型更新监听列表（新的逻辑会自动判断群聊还是私聊）
        result = self._update_session_list(
            task, session_id, "monitor_sessions", "add", "会话"
        )

        return event.plain_result(result)

    async def handle_remove_monitor(
        self,
        event: AstrMessageEvent,
        task_id: str = None,
        chat_type: str = None,
        chat_id: str = None,
        *args,
    ):
        """删除监听源喵～"""
        # 验证参数
        task, cmd_text, error = await self._validate_command_params(
            event, task_id, "只有管理员才能删除监听源喵～", "unmonitor"
        )
        if error:
            return error

        # 解析会话ID
        session_id, error = self._parse_session_id_from_command(
            event, cmd_text, chat_type, chat_id, task_id, "unmonitor"
        )
        if error:
            return error
        # 根据会话类型更新监听列表（新的逻辑会自动判断群聊还是私聊）
        result = self._update_session_list(
            task, session_id, "monitor_sessions", "remove", "会话"
        )

        return event.plain_result(result)

    async def handle_add_target(
        self,
        event: AstrMessageEvent,
        task_id: str = None,
        chat_type: str = None,
        chat_id: str = None,
        *args,
    ):
        """添加转发目标喵～"""
        # 验证参数
        task, cmd_text, error = await self._validate_command_params(
            event, task_id, "只有管理员才能添加转发目标喵～", "target"
        )
        if error:
            return error

        # 解析会话ID
        session_id, error = self._parse_session_id_from_command(
            event, cmd_text, chat_type, chat_id, task_id, "target"
        )
        if error:
            return error

        # 更新目标列表
        result = self._update_session_list(
            task, session_id, "target_sessions", "add", "会话"
        )
        return event.plain_result(result)

    async def handle_remove_target(
        self,
        event: AstrMessageEvent,
        task_id: str = None,
        chat_type: str = None,
        chat_id: str = None,
        *args,
    ):
        """删除转发目标喵～"""
        # 验证参数
        task, cmd_text, error = await self._validate_command_params(
            event, task_id, "只有管理员才能删除转发目标喵～", "untarget"
        )
        if error:
            return error

        # 解析会话ID
        session_id, error = self._parse_session_id_from_command(
            event, cmd_text, chat_type, chat_id, task_id, "untarget"
        )
        if error:
            return error

        # 更新目标列表
        result = self._update_session_list(
            task, session_id, "target_sessions", "remove", "会话"
        )
        return event.plain_result(result)

    async def handle_set_threshold(
        self, event: AstrMessageEvent, task_id: str = None, threshold: int = None
    ):
        """设置消息阈值喵～"""
        # 权限检查
        is_admin, response = await self._check_admin(
            event, "只有管理员才能设置消息阈值喵～"
        )
        if not is_admin:
            return response

        # 获取并验证任务
        task, error_msg = self._get_validated_task(event, task_id)
        if error_msg:
            return event.plain_result(error_msg)

        if threshold is None:
            return event.plain_result("请指定消息阈值喵～")

        if threshold <= 0:
            return event.plain_result("消息阈值必须大于0喵～")

        task["max_messages"] = threshold
        self.plugin.save_config_file()
        return event.plain_result(
            f"已将任务 [{task.get('name')}] 的消息阈值设为 {threshold} 喵～"
        )

    async def handle_rename_task(
        self, event: AstrMessageEvent, task_id: str = None, new_name: str = None
    ):
        """重命名任务喵～"""
        # 权限检查
        is_admin, response = await self._check_admin(
            event, "只有管理员才能重命名任务喵～"
        )
        if not is_admin:
            return response

        # 获取并验证任务
        task, error_msg = self._get_validated_task(event, task_id)
        if error_msg:
            return event.plain_result(error_msg)

        if not new_name:
            return event.plain_result("请提供新的任务名称喵～")

        old_name = task.get("name", "未命名")
        task["name"] = new_name
        self.plugin.save_config_file()
        return event.plain_result(f"已将任务 [{old_name}] 重命名为 [{new_name}] 喵～")

    async def handle_manual_forward(
        self,
        event: AstrMessageEvent,
        task_id: str = None,
        chat_type: str = None,
        chat_id: str = None,
        *args,
    ):
        """手动触发转发喵～"""
        # 权限检查
        is_admin, response = await self._check_admin(
            event, "只有管理员才能手动触发转发喵～"
        )
        if not is_admin:
            return response

        # 获取并验证任务
        task, error_msg = self._get_validated_task(event, task_id)
        if error_msg:
            return event.plain_result(error_msg)

        # 获取原始命令文本
        cmd_text = event.message_str
        if not cmd_text and hasattr(event.message_obj, "raw_message"):
            cmd_text = str(event.message_obj.raw_message)
        logger.info(f"处理手动转发命令: {cmd_text}")

        # 从命令中提取会话ID（可选）
        session_id = self._extract_session_id(event, cmd_text, chat_type, chat_id, args)

        if not session_id:
            # 没有指定会话ID，转发所有会话
            if task_id not in self.plugin.message_cache:
                return event.plain_result("该任务没有任何缓存消息喵～")

            if not self.plugin.message_cache[task_id]:
                return event.plain_result("该任务没有任何缓存消息喵～")

            session_count = len(self.plugin.message_cache[task_id])
            total_msgs = sum(
                len(msgs) for msgs in self.plugin.message_cache[task_id].values()
            )

            await event.plain_result(
                f"正在转发任务 [{task.get('name')}] 的 {session_count} 个会话，共 {total_msgs} 条消息喵～"
            )

            for session in list(self.plugin.message_cache[task_id].keys()):
                await self.plugin.forward_manager.forward_messages(task_id, session)

            return event.plain_result(
                f"已完成任务 [{task.get('name')}] 的所有消息转发喵～"
            )
        else:
            # 只转发指定会话
            if (
                task_id not in self.plugin.message_cache
                or session_id not in self.plugin.message_cache[task_id]
            ):
                return event.plain_result(
                    f"未找到任务 {task_id} 在会话 {session_id} 的缓存消息喵～"
                )

            msg_count = len(self.plugin.message_cache[task_id][session_id])
            await event.plain_result(
                f"正在转发任务 [{task.get('name')}] 在会话 {session_id} 的 {msg_count} 条消息喵～"
            )

            await self.plugin.forward_manager.forward_messages(task_id, session_id)

            return event.plain_result(
                f"已完成任务 [{task.get('name')}] 在会话 {session_id} 的消息转发喵～"
            )

    async def handle_turnrig_help(self, event: AstrMessageEvent):
        """显示帮助信息喵～"""
        # 使用三引号字符串确保换行符被正确保留
        help_text = """▽ 转发侦听插件帮助 ▽

【基本信息】
- 插件可以监听特定会话，并将消息转发到指定目标
- 支持群聊、私聊消息的监听和转发
- 支持保留表情回应、图片、引用回复等

【主要指令】

· /turnrig list - 列出所有转发任务

· /turnrig status [任务ID] - 查看缓存状态

· /turnrig create [名称] - 创建新任务

· /turnrig delete <任务ID> - 删除任务

· /turnrig enable/disable <任务ID> - 启用/禁用任务

【任务配置指令】

· /turnrig monitor <任务ID> 群聊/私聊 <会话ID> - 添加监听源

· /turnrig unmonitor <任务ID> 群聊/私聊 <会话ID> - 删除监听源

· /turnrig adduser <任务ID> <群号> <QQ号> - 添加群聊内特定用户监听

· /turnrig removeuser <任务ID> <群号> <QQ号> - 删除群聊内特定用户监听

· /turnrig target <任务ID> 群聊/私聊 <会话ID> - 添加转发目标

· /turnrig untarget <任务ID> 群聊/私聊 <会话ID> - 删除转发目标

· /turnrig threshold <任务ID> <数量> - 设置消息阈值

【其他功能】

· /turnrig rename <任务ID> <名称> - 重命名任务

· /turnrig forward <任务ID> [群聊/私聊 <会话ID>] - 手动触发转发

· /turnrig cleanup <天数> - 清理指定天数前的已处理消息ID

【便捷指令】

我们还提供了简化版指令，自动使用当前会话ID：

· /tr add <任务ID> - 将当前会话添加到监听列表

· /tr target <任务ID> - 将当前会话设为转发目标

使用 /tr help 查看完整的简化指令列表

【会话ID格式说明】

- 推荐格式: "群聊 群号" 或 "私聊 QQ号"（注意空格）

- 标准格式: aiocqhttp:GroupMessage:群号 或 aiocqhttp:FriendMessage:QQ号

- 不建议直接输入纯数字ID，可能导致类型识别错误"""

        return event.plain_result(help_text)

    async def handle_cleanup_ids(self, event: AstrMessageEvent, days: int = 7):
        """
        清理过期的消息ID喵～ 🧹
        删除指定天数前的已处理消息记录！

        Args:
            event: 消息事件对象喵
            days: 清理天数，默认7天喵

        Returns:
            清理结果消息喵～

        Note:
            只有管理员可以执行此操作，帮助释放内存空间喵！ ✨
        """
        # 权限检查喵～ 👮
        is_admin, response = await self._check_admin(
            event, "只有管理员才能清理消息ID喵～ 🚫"
        )
        if not is_admin:
            return response

        if days <= 0:
            return event.plain_result("天数必须大于0喵～ ❌")

        cleaned_count = self.plugin.cleanup_expired_message_ids(days)
        return event.plain_result(
            f"已清理 {cleaned_count} 个超过 {days} 天的消息ID喵～ ✅"
        )

    # tr 简化命令组处理方法喵～ 🎯
    async def handle_tr_add_monitor(self, event: AstrMessageEvent, task_id: str = None):
        """
        将当前会话添加到监听列表喵～ 👂
        简化版监听添加命令，自动获取当前会话ID！

        Args:
            event: 消息事件对象喵
            task_id: 要添加到的任务ID喵

        Returns:
            操作结果消息喵～

        Note:
            无需手动输入会话ID，会自动使用当前对话喵！ ✨
        """
        # 权限检查喵～ 👮
        is_admin, response = await self._check_admin(
            event, "只有管理员才能添加监听源喵～ 🚫"
        )
        if not is_admin:
            return response

        if not task_id:
            return event.plain_result("请指定要添加到的任务ID喵～ 🆔")

        task = self.plugin.get_task_by_id(task_id)
        if not task:
            return event.plain_result(f"未找到ID为 {task_id} 的任务喵～ ❌")
        # 自动获取当前会话ID喵～ 📍
        current_session = event.unified_msg_origin

        # 根据会话类型更新监听列表（新的逻辑会自动判断群聊还是私聊）喵～ 🔄
        result = self._update_session_list(
            task, current_session, "monitor_sessions", "add", "当前会话"
        )

        return event.plain_result(result)

    async def handle_tr_remove_monitor(
        self, event: AstrMessageEvent, task_id: str = None
    ):
        """将当前会话从监听列表移除喵～"""
        # 权限检查
        is_admin, response = await self._check_admin(
            event, "只有管理员才能删除监听源喵～"
        )
        if not is_admin:
            return response

        if not task_id:
            return event.plain_result("请指定要移除的任务ID喵～")

        task = self.plugin.get_task_by_id(task_id)
        if not task:
            return event.plain_result(f"未找到ID为 {task_id} 的任务喵～")
        # 自动获取当前会话ID
        current_session = event.unified_msg_origin

        # 根据会话类型更新监听列表（新的逻辑会自动判断群聊还是私聊）
        result = self._update_session_list(
            task, current_session, "monitor_sessions", "remove", "当前会话"
        )

        return event.plain_result(result)

    async def handle_tr_add_target(self, event: AstrMessageEvent, task_id: str = None):
        """将当前会话添加为转发目标喵～"""
        # 权限检查
        is_admin, response = await self._check_admin(
            event, "只有管理员才能添加转发目标喵～"
        )
        if not is_admin:
            return response

        if not task_id:
            return event.plain_result("请指定要添加到的任务ID喵～")

        task = self.plugin.get_task_by_id(task_id)
        if not task:
            return event.plain_result(f"未找到ID为 {task_id} 的任务喵～")

        # 自动获取当前会话ID
        current_session = event.unified_msg_origin

        # 更新目标列表
        result = self._update_session_list(
            task, current_session, "target_sessions", "add", "当前会话"
        )
        return event.plain_result(result)

    async def handle_tr_remove_target(
        self, event: AstrMessageEvent, task_id: str = None
    ):
        """将当前会话从转发目标移除喵～"""
        # 权限检查
        is_admin, response = await self._check_admin(
            event, "只有管理员才能删除转发目标喵～"
        )
        if not is_admin:
            return response

        if not task_id:
            return event.plain_result("请指定要移除的任务ID喵～")

        task = self.plugin.get_task_by_id(task_id)
        if not task:
            return event.plain_result(f"未找到ID为 {task_id} 的任务喵～")

        # 自动获取当前会话ID
        current_session = event.unified_msg_origin

        # 更新目标列表
        result = self._update_session_list(
            task, current_session, "target_sessions", "remove", "当前会话"
        )
        return event.plain_result(result)

    async def handle_tr_list_tasks(self, event: AstrMessageEvent):
        """列出所有转发任务喵～(简化版)"""
        # 直接复用handle_list_tasks方法
        return await self.handle_list_tasks(event)

    async def handle_tr_help(self, event: AstrMessageEvent):
        """
        显示简化指令帮助喵～ 📖
        提供便捷的tr系列命令使用指南！

        Args:
            event: 消息事件对象喵

        Returns:
            详细的简化指令帮助信息喵～

        Note:
            tr系列命令无需手动输入会话ID，更加便捷喵！ ✨
        """
        # 使用三引号字符串确保换行符被正确保留
        help_text = """▽ 转发侦听简化指令帮助 ▽

【简化指令列表】

· /tr add <任务ID> - 将当前会话添加到监听列表

· /tr remove <任务ID> - 将当前会话从监听列表移除

· /tr target <任务ID> - 将当前会话添加为转发目标

· /tr untarget <任务ID> - 将当前会话从转发目标移除

· /tr adduser <任务ID> <QQ号> - 添加指定用户到当前群聊的监听列表(仅群聊可用)

· /tr removeuser <任务ID> <QQ号> - 从当前群聊的监听列表中移除指定用户(仅群聊可用)

· /tr list - 列出所有转发任务

· /tr help - 显示此帮助

会话相关指令不需要手动输入会话ID，会自动使用当前会话的ID喵～

如果需要更多完整功能，请使用 /turnrig help 查看完整指令列表喵～"""
        # 确保使用plain_result以保留换行符
        return event.plain_result(help_text)

    async def handle_add_user_in_group(
        self,
        event: AstrMessageEvent,
        task_id: str = None,
        group_id: str = None,
        user_id: str = None,
    ):
        """
        添加群聊内特定用户到监听列表喵～ 👥
        精确监听指定群内的特定用户消息！

        Args:
            event: 消息事件对象喵
            task_id: 任务ID喵
            group_id: 群号喵
            user_id: 用户QQ号喵

        Returns:
            操作结果消息喵～

        Note:
            可以只监听群内指定用户的消息，实现精准监听喵！ 🎯
        """
        # 权限检查
        is_admin, response = await self._check_admin(
            event, "只有管理员才能添加群内特定用户监听喵～"
        )
        if not is_admin:
            return response

        # 参数检查
        if not task_id or not group_id or not user_id:
            return event.plain_result(
                "请提供完整的参数喵～\n正确格式：/turnrig adduser <任务ID> <群号> <QQ号>"
            )

        # 获取并验证任务
        task, error_msg = self._get_validated_task(event, task_id)
        if error_msg:
            return event.plain_result(error_msg)

        # 确保group_id和user_id是字符串
        group_id_str = str(group_id)
        user_id_str = str(user_id)

        # 将群号转换为标准化的会话ID格式
        full_group_id = self._ensure_full_session_id(f"群聊 {group_id_str}")

        # 初始化monitored_users_in_groups字段
        if "monitored_users_in_groups" not in task:
            task["monitored_users_in_groups"] = {}

        # 初始化该群的监听用户列表
        if full_group_id not in task["monitored_users_in_groups"]:
            task["monitored_users_in_groups"][full_group_id] = []

        # 检查用户是否已经在监听列表中
        if user_id_str in task["monitored_users_in_groups"][full_group_id]:
            return event.plain_result(
                f"用户 {user_id_str} 已经在群 {group_id_str} 的监听列表中了喵～"
            )

        # 添加用户到监听列表
        task["monitored_users_in_groups"][full_group_id].append(user_id_str)
        self.plugin.save_config_file()

        return event.plain_result(
            f"已将用户 {user_id_str} 添加到任务 [{task.get('name')}] 在群 {group_id_str} 的监听列表喵～"
        )

    async def handle_remove_user_from_group(
        self,
        event: AstrMessageEvent,
        task_id: str = None,
        group_id: str = None,
        user_id: str = None,
    ):
        """从监听列表移除群聊内特定用户喵～"""
        # 权限检查
        is_admin, response = await self._check_admin(
            event, "只有管理员才能移除群内特定用户监听喵～"
        )
        if not is_admin:
            return response

        # 参数检查
        if not task_id or not group_id or not user_id:
            return event.plain_result(
                "请提供完整的参数喵～\n正确格式：/turnrig removeuser <任务ID> <群号> <QQ号>"
            )

        # 获取并验证任务
        task, error_msg = self._get_validated_task(event, task_id)
        if error_msg:
            return event.plain_result(error_msg)

        # 确保group_id和user_id是字符串
        group_id_str = str(group_id)
        user_id_str = str(user_id)

        # 将群号转换为标准化的会话ID格式
        full_group_id = self._ensure_full_session_id(f"群聊 {group_id_str}")

        # 检查该群的监听用户列表是否存在
        if (
            "monitored_users_in_groups" not in task
            or full_group_id not in task["monitored_users_in_groups"]
        ):
            return event.plain_result(
                f"任务 [{task.get('name')}] 在群 {group_id_str} 没有设置特定用户监听喵～"
            )

        # 检查用户是否在监听列表中
        if user_id_str not in task["monitored_users_in_groups"][full_group_id]:
            return event.plain_result(
                f"用户 {user_id_str} 不在任务 [{task.get('name')}] 群 {group_id_str} 的监听列表中喵～"
            )

        # 从监听列表移除用户
        task["monitored_users_in_groups"][full_group_id].remove(user_id_str)

        # 如果列表为空，可以考虑删除该群的记录
        if not task["monitored_users_in_groups"][full_group_id]:
            del task["monitored_users_in_groups"][full_group_id]

        self.plugin.save_config_file()

        return event.plain_result(
            f"已将用户 {user_id_str} 从任务 [{task.get('name')}] 群 {group_id_str} 的监听列表中移除喵～"
        )

    async def handle_tr_add_user_in_group(
        self, event: AstrMessageEvent, task_id: str = None, user_id: str = None
    ):
        """将指定用户添加到当前群聊的监听列表喵～"""
        # 权限检查
        is_admin, response = await self._check_admin(
            event, "只有管理员才能添加群内特定用户监听喵～"
        )
        if not is_admin:
            return response

        if not task_id or not user_id:
            return event.plain_result(
                "请提供完整的参数喵～\n正确格式：/tr adduser <任务ID> <QQ号>"
            )

        # 检查当前会话是否为群聊
        if "GroupMessage" not in event.unified_msg_origin:
            return event.plain_result("此命令只能在群聊中使用喵～")

        # 从会话ID中提取群号
        group_id = event.get_group_id()
        if not group_id:
            return event.plain_result(
                "无法获取当前群号，请使用完整命令 /turnrig adduser 喵～"
            )

        # 调用完整版命令处理方法
        result = await self.handle_add_user_in_group(event, task_id, group_id, user_id)
        return result

    async def handle_tr_remove_user_from_group(
        self, event: AstrMessageEvent, task_id: str = None, user_id: str = None
    ):
        """将指定用户从当前群聊的监听列表移除喵～"""
        # 权限检查
        is_admin, response = await self._check_admin(
            event, "只有管理员才能移除群内特定用户监听喵～"
        )
        if not is_admin:
            return response

        if not task_id or not user_id:
            return event.plain_result(
                "请提供完整的参数喵～\n正确格式：/tr removeuser <任务ID> <QQ号>"
            )

        # 检查当前会话是否为群聊
        if "GroupMessage" not in event.unified_msg_origin:
            return event.plain_result("此命令只能在群聊中使用喵～")

        # 从会话ID中提取群号
        group_id = event.get_group_id()
        if not group_id:
            return event.plain_result(
                "无法获取当前群号，请使用完整命令 /turnrig removeuser 喵～"
            )

        # 调用完整版命令处理方法
        result = await self.handle_remove_user_from_group(
            event, task_id, group_id, user_id
        )
        return result
