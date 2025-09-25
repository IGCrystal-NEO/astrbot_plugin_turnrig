"""
监听管理命令处理器喵～ 👂
负责处理所有监听和转发目标相关的命令！

包含：
- 添加/删除监听源
- 添加/删除转发目标
- 群内特定用户监听
"""

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent
from .base import BaseCommandHandler


class MonitorCommandHandler(BaseCommandHandler):
    """
    监听管理命令处理器类喵～ 👂
    专门负责处理监听源和转发目标的管理！
    
    这个处理器管理：
    - 👂 监听源的添加和删除
    - 🎯 转发目标的添加和删除
    - 👥 群内特定用户的监听管理
    
    Note:
        支持群聊、私聊以及群内特定用户的精准监听喵！ ✨
    """
    
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
