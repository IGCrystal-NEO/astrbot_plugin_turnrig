from astrbot.api.event import AstrMessageEvent

# 导入所有解耦的处理器模块喵～ 📦
from .handlers.task import TaskCommandHandler
from .handlers.monitor import MonitorCommandHandler
from .handlers.bot import BotCommandHandler
from .handlers.simplified import SimplifiedCommandHandler
from .handlers.help import HelpCommandHandler


class CommandHandlers:
    """
    命令处理器聚合类喵～ 🎯
    整合所有解耦的命令处理器，提供统一的接口！ ฅ(^•ω•^ฅ

    这个类将所有功能模块整合在一起：
    - 📋 任务管理命令（TaskCommandHandler）
    - 👂 监听管理命令（MonitorCommandHandler）
    - 🤖 机器人ID管理（BotCommandHandler）
    - 🎯 简化命令（SimplifiedCommandHandler）
    - 📖 帮助信息（HelpCommandHandler）

    Note:
        这是一个聚合类，实际功能由各个专门的处理器实现喵！ 💫
    """

    def __init__(self, plugin_instance):
        """
        初始化命令处理器聚合类喵～ 🎮
        创建所有子处理器的实例！

        Args:
            plugin_instance: TurnRigPlugin的实例，提供配置和服务喵～
        """
        self.plugin = plugin_instance

        # 初始化所有子处理器喵～ 🔧
        self.task_handler = TaskCommandHandler(plugin_instance)
        self.monitor_handler = MonitorCommandHandler(plugin_instance)
        self.bot_handler = BotCommandHandler(plugin_instance)
        self.simplified_handler = SimplifiedCommandHandler(plugin_instance)
        self.help_handler = HelpCommandHandler(plugin_instance)

    # ============ 任务管理相关命令 ============
    async def handle_list_tasks(self, event: AstrMessageEvent):
        """列出所有转发任务喵～ 📋"""
        return await self.task_handler.handle_list_tasks(event)
    async def handle_status(self, event: AstrMessageEvent, task_id: str = None):
        """查看特定任务的缓存状态喵～"""
        return await self.task_handler.handle_status(event, task_id)
    async def handle_create_task(self, event: AstrMessageEvent, task_name: str = None):
        """创建新的转发任务喵～"""
        return await self.task_handler.handle_create_task(event, task_name)
    async def handle_delete_task(self, event: AstrMessageEvent, task_id: str = None):
        """处理删除任务的指令"""
        return await self.task_handler.handle_delete_task(event, task_id)
    async def handle_enable_task(self, event: AstrMessageEvent, task_id: str = None):
        """启用转发任务喵～"""
        return await self.task_handler.handle_enable_task(event, task_id)
    async def handle_disable_task(self, event: AstrMessageEvent, task_id: str = None):
        """禁用转发任务喵～"""
        return await self.task_handler.handle_disable_task(event, task_id)
    async def handle_set_threshold(self, event: AstrMessageEvent, task_id: str = None, threshold: int = None):
        """设置消息阈值喵～"""
        return await self.task_handler.handle_set_threshold(event, task_id, threshold)
    async def handle_rename_task(self, event: AstrMessageEvent, task_id: str = None, new_name: str = None):
        """重命名任务喵～"""
        return await self.task_handler.handle_rename_task(event, task_id, new_name)
    async def handle_manual_forward(self, event: AstrMessageEvent, task_id: str = None, chat_type: str = None, chat_id: str = None, *args):
        """手动触发转发喵～"""
        return await self.task_handler.handle_manual_forward(event, task_id, chat_type, chat_id, *args)
    async def handle_cleanup_ids(self, event: AstrMessageEvent, days: int = 7):
        """清理过期的消息ID喵～ 🧹"""
        return await self.task_handler.handle_cleanup_ids(event, days)

    # ============ 监听管理相关命令 ============
    async def handle_add_monitor(self, event: AstrMessageEvent, task_id: str = None, chat_type: str = None, chat_id: str = None, *args):
        """添加监听源喵～"""
        return await self.monitor_handler.handle_add_monitor(event, task_id, chat_type, chat_id, *args)
    async def handle_remove_monitor(self, event: AstrMessageEvent, task_id: str = None, chat_type: str = None, chat_id: str = None, *args):
        """删除监听源喵～"""
        return await self.monitor_handler.handle_remove_monitor(event, task_id, chat_type, chat_id, *args)
    async def handle_add_target(self, event: AstrMessageEvent, task_id: str = None, chat_type: str = None, chat_id: str = None, *args):
        """添加转发目标喵～"""
        return await self.monitor_handler.handle_add_target(event, task_id, chat_type, chat_id, *args)
    async def handle_remove_target(self, event: AstrMessageEvent, task_id: str = None, chat_type: str = None, chat_id: str = None, *args):
        """删除转发目标喵～"""
        return await self.monitor_handler.handle_remove_target(event, task_id, chat_type, chat_id, *args)
    async def handle_add_user_in_group(self, event: AstrMessageEvent, task_id: str = None, group_id: str = None, user_id: str = None):
        """添加群聊内特定用户到监听列表喵～ 👥"""
        return await self.monitor_handler.handle_add_user_in_group(event, task_id, group_id, user_id)
    async def handle_remove_user_from_group(self, event: AstrMessageEvent, task_id: str = None, group_id: str = None, user_id: str = None):
        """从监听列表移除群聊内特定用户喵～"""
        return await self.monitor_handler.handle_remove_user_from_group(event, task_id, group_id, user_id)

    # ============ 机器人ID管理相关命令 ============
    async def handle_add_bot_id(self, event: AstrMessageEvent, bot_id: str = None):
        """添加机器人ID到过滤列表喵～ 🤖"""
        return await self.bot_handler.handle_add_bot_id(event, bot_id)
    async def handle_remove_bot_id(self, event: AstrMessageEvent, bot_id: str = None):
        """从过滤列表移除机器人ID喵～ 🗑️"""
        return await self.bot_handler.handle_remove_bot_id(event, bot_id)
    async def handle_list_bot_ids(self, event: AstrMessageEvent):
        """列出所有过滤的机器人ID喵～ 📋"""
        return await self.bot_handler.handle_list_bot_ids(event)

    # ============ 简化命令(tr)相关 ============
    async def handle_tr_add_monitor(self, event: AstrMessageEvent, task_id: str = None):
        """将当前会话添加到监听列表喵～ 👂"""
        return await self.simplified_handler.handle_tr_add_monitor(event, task_id)
    async def handle_tr_remove_monitor(self, event: AstrMessageEvent, task_id: str = None):
        """将当前会话从监听列表移除喵～"""
        return await self.simplified_handler.handle_tr_remove_monitor(event, task_id)
    async def handle_tr_add_target(self, event: AstrMessageEvent, task_id: str = None):
        """将当前会话添加为转发目标喵～"""
        return await self.simplified_handler.handle_tr_add_target(event, task_id)
    async def handle_tr_remove_target(self, event: AstrMessageEvent, task_id: str = None):
        """将当前会话从转发目标移除喵～"""
        return await self.simplified_handler.handle_tr_remove_target(event, task_id)
    async def handle_tr_add_user_in_group(self, event: AstrMessageEvent, task_id: str = None, user_id: str = None):
        """将指定用户添加到当前群聊的监听列表喵～"""
        return await self.simplified_handler.handle_tr_add_user_in_group(event, task_id, user_id)
    async def handle_tr_remove_user_from_group(self, event: AstrMessageEvent, task_id: str = None, user_id: str = None):
        """将指定用户从当前群聊的监听列表移除喵～"""
        return await self.simplified_handler.handle_tr_remove_user_from_group(event, task_id, user_id)
    async def handle_tr_list_tasks(self, event: AstrMessageEvent):
        """列出所有转发任务喵～(简化版)"""
        return await self.simplified_handler.handle_tr_list_tasks(event)
    async def handle_tr_help(self, event: AstrMessageEvent):
        """显示简化指令帮助喵～ 📖"""
        return await self.simplified_handler.handle_tr_help(event)

    # ============ 帮助信息相关 ============
    async def handle_turnrig_help(self, event: AstrMessageEvent):
        """显示帮助信息喵～"""
        return await self.help_handler.handle_turnrig_help(event)


