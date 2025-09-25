"""
任务管理命令处理器喵～ 📋
负责处理所有任务相关的命令！

包含：
- 任务列表查看
- 任务创建和删除
- 任务启用和禁用
- 任务重命名
- 消息阈值设置
- 手动触发转发
"""

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent
from .base import BaseCommandHandler


class TaskCommandHandler(BaseCommandHandler):
    """
    任务管理命令处理器类喵～ 📋
    专门负责处理任务的增删改查等操作！
    
    这个处理器管理：
    - 📋 任务列表和状态查看
    - ➕ 任务的创建和删除
    - ⚙️ 任务的启用和禁用
    - ✏️ 任务重命名
    - 📊 消息阈值设置
    - 🔄 手动触发转发
    
    Note:
        所有任务相关的命令都在这里处理喵！ ✨
    """
    
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
