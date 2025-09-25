"""
机器人ID管理命令处理器喵～ 🤖
负责处理机器人ID过滤列表的管理！

包含：
- 添加机器人ID到过滤列表
- 从过滤列表移除机器人ID
- 列出所有过滤的机器人ID
"""

from astrbot.api.event import AstrMessageEvent
from .base import BaseCommandHandler


class BotCommandHandler(BaseCommandHandler):
    """
    机器人ID管理命令处理器类喵～ 🤖
    专门负责管理机器人ID过滤列表！

    这个处理器管理：
    - ➕ 添加机器人ID到过滤列表
    - ➖ 从过滤列表移除机器人ID
    - 📋 查看所有过滤的机器人ID

    Note:
        防止机器人监听自己的消息导致循环发送喵！ 🛡️
    """

    async def handle_add_bot_id(self, event: AstrMessageEvent, bot_id: str = None):
        """
        添加机器人ID到过滤列表喵～ 🤖
        防止机器人监听自己的消息导致循环发送！
    
        Args:
            event: 消息事件对象喵
            bot_id: 机器人QQ号喵
    
        Returns:
            操作结果消息喵～
    
        Note:
            添加的机器人ID会被自动过滤，不会被监听喵！ 🛡️
        """
        # 权限检查
        is_admin, response = await self._check_admin(
            event, "只有管理员才能管理机器人ID列表喵～"
        )
        if not is_admin:
            return response
    
        if not bot_id:
            return event.plain_result(
                "请提供机器人QQ号喵～\n正确格式：/turnrig addbot <机器人QQ号>"
            )
    
        # 确保bot_id是字符串
        bot_id_str = str(bot_id)
    
        # 检查是否已经在列表中
        if bot_id_str in self.plugin.config.get("bot_self_ids", []):
            return event.plain_result(f"机器人ID {bot_id_str} 已经在过滤列表中了喵～")
    
        # 添加到过滤列表
        if "bot_self_ids" not in self.plugin.config:
            self.plugin.config["bot_self_ids"] = []
    
        self.plugin.config["bot_self_ids"].append(bot_id_str)
        self.plugin.save_config_file()
    
        return event.plain_result(
            f"已将机器人ID {bot_id_str} 添加到过滤列表喵～ 现在不会监听此ID的消息了！🤖"
        )

    async def handle_remove_bot_id(self, event: AstrMessageEvent, bot_id: str = None):
        """
        从过滤列表移除机器人ID喵～ 🗑️
        移除后此ID的消息将可以被正常监听！
    
        Args:
            event: 消息事件对象喵
            bot_id: 要移除的机器人QQ号喵
    
        Returns:
            操作结果消息喵～
        """
        # 权限检查
        is_admin, response = await self._check_admin(
            event, "只有管理员才能管理机器人ID列表喵～"
        )
        if not is_admin:
            return response
    
        if not bot_id:
            return event.plain_result(
                "请提供要移除的机器人QQ号喵～\n正确格式：/turnrig removebot <机器人QQ号>"
            )
    
        # 确保bot_id是字符串
        bot_id_str = str(bot_id)
    
        # 检查列表是否存在
        bot_ids = self.plugin.config.get("bot_self_ids", [])
        if not bot_ids:
            return event.plain_result("机器人ID过滤列表为空喵～")
    
        # 检查是否在列表中
        if bot_id_str not in bot_ids:
            return event.plain_result(f"机器人ID {bot_id_str} 不在过滤列表中喵～")
    
        # 从列表中移除
        self.plugin.config["bot_self_ids"].remove(bot_id_str)
        self.plugin.save_config_file()
    
        return event.plain_result(
            f"已将机器人ID {bot_id_str} 从过滤列表中移除喵～ 现在可以监听此ID的消息了！✅"
        )

    async def handle_list_bot_ids(self, event: AstrMessageEvent):
        """
        列出所有过滤的机器人ID喵～ 📋
        显示当前配置中的所有机器人ID过滤列表！
    
        Args:
            event: 消息事件对象喵
    
        Returns:
            机器人ID列表信息喵～
        """
        # 权限检查
        is_admin, response = await self._check_admin(
            event, "只有管理员才能查看机器人ID列表喵～"
        )
        if not is_admin:
            return response
    
        bot_ids = self.plugin.config.get("bot_self_ids", [])
    
        if not bot_ids:
            return event.plain_result(
                "当前没有配置任何机器人ID过滤喵～\n"
                + "使用 /turnrig addbot <QQ号> 添加机器人ID到过滤列表！"
            )
    
        result = "🤖 机器人ID过滤列表喵～\n"
        result += "=" * 30 + "\n\n"
    
        for i, bot_id in enumerate(bot_ids, 1):
            result += f"{i}. {bot_id}\n"
    
        result += "\n" + "=" * 30 + "\n"
        result += f"共 {len(bot_ids)} 个机器人ID在过滤列表中喵～\n"
        result += "这些ID的消息不会被插件监听，避免循环发送！"
    
        return event.plain_result(result)
