"""
简化命令处理器喵～ 🎯
提供便捷的tr系列命令，自动使用当前会话ID！

包含：
- tr add/remove - 监听管理
- tr target/untarget - 目标管理
- tr adduser/removeuser - 群内用户管理
- tr list/help - 列表和帮助
"""

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent
from .base import BaseCommandHandler


class SimplifiedCommandHandler(BaseCommandHandler):
    """
    简化命令处理器类喵～ 🎯
    提供更便捷的命令接口，无需手动输入会话ID！
    
    这个处理器提供：
    - 🎯 自动使用当前会话ID的便捷命令
    - 👂 快速添加/删除监听
    - 🎯 快速设置转发目标
    - 👥 便捷的群内用户管理
    - 📋 任务列表查看
    - ❓ 简化命令帮助
    
    Note:
        tr系列命令会自动获取当前会话的ID，更加便捷喵！ ✨
    """
    
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
        
        # 调用MonitorCommandHandler的方法
        from .monitor import MonitorCommandHandler
        monitor_handler = MonitorCommandHandler(self.plugin)
        result = await monitor_handler.handle_add_user_in_group(event, task_id, group_id, user_id)
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
        
        # 调用MonitorCommandHandler的方法
        from .monitor import MonitorCommandHandler
        monitor_handler = MonitorCommandHandler(self.plugin)
        result = await monitor_handler.handle_remove_user_from_group(
            event, task_id, group_id, user_id
        )
        return result
    
    async def handle_tr_list_tasks(self, event: AstrMessageEvent):
        """列出所有转发任务喵～(简化版)"""
        # 调用TaskCommandHandler的方法
        from .task import TaskCommandHandler
        task_handler = TaskCommandHandler(self.plugin)
        return await task_handler.handle_list_tasks(event)
    
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
