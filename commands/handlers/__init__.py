"""
命令处理器模块喵～ 🎯
包含各种功能的解耦处理器！

这个包将原本庞大的CommandHandlers类拆分成多个专注的模块：
- base: 基础处理器类和通用方法
- task: 任务管理相关命令
- monitor: 监听管理相关命令
- bot: 机器人ID管理相关命令
- simplified: 简化命令(tr)相关
- utils: 工具函数和辅助方法
"""

from .base import BaseCommandHandler
from .task import TaskCommandHandler
from .monitor import MonitorCommandHandler
from .bot import BotCommandHandler
from .simplified import SimplifiedCommandHandler

__all__ = [
    "BaseCommandHandler",
    "TaskCommandHandler", 
    "MonitorCommandHandler",
    "BotCommandHandler",
    "SimplifiedCommandHandler",
]
