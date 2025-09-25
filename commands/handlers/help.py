"""
帮助信息处理器喵～ 📖
负责显示各种帮助信息！

包含：
- 完整的turnrig帮助
- 简化的tr帮助
"""

from astrbot.api.event import AstrMessageEvent
from .base import BaseCommandHandler


class HelpCommandHandler(BaseCommandHandler):
    """
    帮助信息处理器类喵～ 📖
    显示详细的命令使用指南！
    
    这个处理器提供：
    - 📖 完整的命令帮助文档
    - 🎯 简化命令的使用说明
    - 💡 使用示例和注意事项
    
    Note:
        帮助用户快速了解和使用插件功能喵！ ✨
    """
    
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

【机器人ID管理】

· /turnrig addbot <机器人QQ号> - 添加机器人ID到过滤列表

· /turnrig removebot <机器人QQ号> - 从过滤列表移除机器人ID

· /turnrig listbots - 列出所有过滤的机器人ID

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
