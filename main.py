import asyncio
import os
import time

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, MessageEventResult, filter
from astrbot.api.star import Context, Star, register

from .commands.command_handlers import CommandHandlers

# 导入解耦后的模块 - 更新导入路径
from .config.config_manager import ConfigManager
from .messaging.forward_manager import ForwardManager
from .messaging.message_listener import MessageListener


@register("astrbot_plugin_turnrig", "IGCrystal", "监听并转发消息的插件", "1.0.0", "https://github.com/IGCrystal/astrbot_plugin_turnrig")
class TurnRigPlugin(Star):
    def __init__(self, context: Context, config=None):
        super().__init__(context)

        # 数据存储路径 - 修改为正确的持久化数据存储路径
        self.data_dir = os.path.join("data", "plugins_data", "astrbot_plugin_turnrig")
        os.makedirs(self.data_dir, exist_ok=True)

        # 创建临时目录用于存储图片
        self.temp_dir = os.path.join(self.data_dir, "temp")
        os.makedirs(self.temp_dir, exist_ok=True)

        # 确保下载助手可以访问临时目录
        from .messaging.forward.download_helper import DownloadHelper
        self.download_helper = DownloadHelper(self.temp_dir)
        self.download_helper.plugin = self  # 添加对插件的引用，用于访问配置

        # 创建配置管理器
        self.config_manager = ConfigManager(self.data_dir)

        # 从配置文件加载或使用默认配置
        self.config = self.config_manager.load_config() or {"tasks": [], "default_max_messages": 20}

        # 如果收到了 AstrBot 的配置，且当前配置为空，才使用 AstrBot 配置
        if config and not self.config:
            # 尝试将旧格式配置转换为新格式
            if isinstance(config, dict) and not config.get('tasks'):
                default_task = {
                    "id": "1",  # 使用"1"作为第一个任务的ID
                    "name": "默认任务",
                    "monitor_groups": config.get('monitor_groups', []),
                    "monitor_private_users": config.get('monitor_private_users', []),
                    "monitored_users_in_groups": config.get('monitored_users_in_groups', {}),
                    "target_sessions": config.get('target_sessions', []),
                    "max_messages": config.get('max_messages', 20),
                    "enabled": True
                }
                self.config = {
                    "tasks": [default_task],
                    "default_max_messages": 20
                }
            else:
                self.config = config

        # 确保配置有tasks字段
        if 'tasks' not in self.config:
            self.config['tasks'] = []

        # 确保配置有default_max_messages字段
        if 'default_max_messages' not in self.config:
            self.config['default_max_messages'] = 20

        # 如果没有任何任务，创建一个自动捕获所有消息的测试任务
        if not self.config['tasks']:
            logger.info("没有找到任何转发任务，创建一个测试任务")
            test_task = {
                "id": "test",
                "name": "测试任务",
                "monitor_groups": [], # 这里留空以便后续手动添加
                "monitor_private_users": [],
                "monitored_users_in_groups": {},
                "target_sessions": [], # 这里留空以便后续手动添加
                "max_messages": 20,
                "enabled": True,
                "monitor_sessions": [] # 新增字段，用于直接匹配session_id
            }
            self.config['tasks'].append(test_task)
            self.save_config_file()

        # 消息缓存
        self.message_cache = self.config_manager.load_message_cache() or {}

        # 清理缓存中的无效任务
        self._cleanup_invalid_tasks_in_cache()

        # 保存一次配置确保文件存在
        self.save_config_file()
        logger.info(f"转发侦听器插件初始化完成，数据存储在 {self.data_dir} 目录下")
        logger.info(f"已加载 {len(self.config.get('tasks', []))} 个转发任务")

        # 打印所有任务的详细信息，便于调试
        for task in self.config.get('tasks', []):
            logger.info(f"任务ID: {task.get('id')}, 名称: {task.get('name')}, 启用状态: {task.get('enabled')}")
            logger.info(f"  监听群组: {task.get('monitor_groups', [])}")
            logger.info(f"  监听私聊: {task.get('monitor_private_users', [])}")
            logger.info(f"  群内特定用户: {task.get('monitored_users_in_groups', {})}")
            logger.info(f"  转发目标: {task.get('target_sessions', [])}")

        # 创建模块实例
        self.forward_manager = ForwardManager(self)
        self.message_listener = MessageListener(self)
        self.command_handlers = CommandHandlers(self)

        # 启动定期保存任务
        asyncio.create_task(self.periodic_save())

        # 添加一个新的循环监听任务
        asyncio.create_task(self.message_monitor_loop())

        # 添加消息ID清理任务
        self.cleanup_task = None
        self.start_cleanup_task()

        # 添加清理临时文件任务
        asyncio.create_task(self.cleanup_temp_files())

    def _cleanup_invalid_tasks_in_cache(self):
        """清理缓存中不存在的任务"""
        valid_task_ids = {str(task.get('id', '')) for task in self.config.get('tasks', [])}
        invalid_tasks = []

        # 检查消息缓存中的任务
        for task_id in list(self.message_cache.keys()):
            if str(task_id) not in valid_task_ids:
                invalid_tasks.append(task_id)
                del self.message_cache[task_id]

        if invalid_tasks:
            logger.info(f"已清理 {len(invalid_tasks)} 个无效任务的缓存: {', '.join(invalid_tasks)}")
            self.save_message_cache()

    def save_config_file(self):
        """将配置保存到文件"""
        self.config_manager.save_config(self.config)

    def save_message_cache(self):
        """保存消息缓存"""
        # 添加更详细的日志
        cache_stats = {}
        total_messages = 0

        for task_id, sessions in self.message_cache.items():
            session_count = len(sessions)
            messages_in_task = sum(len(msgs) for msgs in sessions.values())
            total_messages += messages_in_task
            cache_stats[task_id] = {
                "sessions": session_count,
                "messages": messages_in_task
            }

        logger.info(f"保存消息缓存，共 {len(cache_stats)} 个任务，{total_messages} 条消息")
        for task_id, stats in cache_stats.items():
            logger.info(f"  任务 {task_id}: {stats['sessions']} 个会话，共 {stats['messages']} 条消息")

        self.config_manager.save_message_cache(self.message_cache)

    async def periodic_save(self):
        """定期保存数据"""
        while True:
            await asyncio.sleep(300)  # 每5分钟保存一次
            self.save_message_cache()
            self.save_config_file()  # 也保存配置
            logger.debug("已完成定期保存")

    async def message_monitor_loop(self):
        """定期检查消息监听状态，但不主动获取历史消息"""
        while True:
            try:
                # 检查长时间未活跃会话
                for task_id, sessions in self.message_cache.items():
                    for session_id, messages in sessions.items():
                        # 检查长时间未活跃的会话
                        if messages and time.time() - messages[-1]["timestamp"] > 3600:
                            logger.debug(f"会话 {session_id} 在任务 {task_id} 中超过1小时未活动")

                # 移除主动获取历史消息的功能
                # 只依赖消息监听器来记录新消息

            except Exception as e:
                logger.error(f"消息监听循环错误: {e}")

            await asyncio.sleep(60)  # 每60秒检查一次，因为不再主动获取消息，可以降低频率

    async def _fetch_latest_messages(self, platform, msg_type, chat_id):
        """禁用从指定平台获取最新消息的功能"""
        # 该方法已禁用，不再主动获取历史消息
        logger.debug("主动获取消息功能已禁用")
        return []

    async def _process_fetched_messages(self, task_id, session_id, messages):
        """禁用处理主动获取消息的功能"""
        # 该方法已禁用，不再处理主动获取的历史消息
        logger.debug("处理主动获取消息功能已禁用")
        return

    def get_task_by_id(self, task_id):
        """通过ID获取任务配置"""
        # 确保转换为字符串进行比较，避免类型不匹配问题
        task_id_str = str(task_id)
        for task in self.config['tasks']:
            if str(task.get('id', '')) == task_id_str:
                return task
        return None

    def get_all_enabled_tasks(self):
        """获取所有启用的任务"""
        return [task for task in self.config['tasks'] if task.get('enabled', True)]

    def get_max_task_id(self):
        """获取当前最大任务ID"""
        max_id = 0
        for task in self.config['tasks']:
            try:
                task_id = int(task.get('id', '0'))
                if task_id > max_id:
                    max_id = task_id
            except ValueError:
                # 如果任务ID不是整数，忽略
                pass
        return max_id

    # 添加新方法，用于启动定期清理任务
    def start_cleanup_task(self):
        """启动定期清理过期消息ID的任务"""
        self.cleanup_task = asyncio.create_task(self.periodic_message_ids_cleanup())
        logger.debug("已启动消息ID定期清理任务")

    async def periodic_message_ids_cleanup(self):
        """定期清理过期的processed_message_ids"""
        while True:
            try:
                # 默认清理7天前的消息ID
                cleaned_count = self.cleanup_expired_message_ids(7)
                if cleaned_count > 0:
                    logger.info(f"定期清理: 已删除 {cleaned_count} 个过期消息ID")
            except Exception as e:
                logger.error(f"清理过期消息ID时出错: {e}")            # 每天运行一次
            await asyncio.sleep(86400)  # 24小时 = 86400秒

    def cleanup_expired_message_ids(self, days: int = 7) -> int:
        """清理超过指定天数的processed_message_ids

        Args:
            days: 清理超过多少天的消息ID

        Returns:
            int: 清理的消息ID数量
        """
        current_time = int(time.time())
        cutoff_time = current_time - (days * 86400)  # days转换为秒
        total_cleaned = 0

        # 查找所有任务的processed_message_ids
        for key in list(self.config.keys()):
            if key.startswith('processed_message_ids_'):
                if not isinstance(self.config[key], list):
                    continue

                original_count = len(self.config[key])
                # 过滤掉过期的消息ID
                self.config[key] = [
                    msg for msg in self.config[key]
                    if isinstance(msg, dict) and msg.get('timestamp', 0) > cutoff_time
                ]

                cleaned_count = original_count - len(self.config[key])
                total_cleaned += cleaned_count

                if cleaned_count > 0:
                    logger.debug(f"从 {key} 中清理了 {cleaned_count} 个消息ID")

        # 如果有清理，保存配置
        if total_cleaned > 0:
            self.save_config_file()

        return total_cleaned

    async def cleanup_temp_files(self):
        """定期清理临时文件夹中的文件"""
        while True:
            try:
                await asyncio.sleep(3600)  # 每小时执行一次

                if not os.path.exists(self.temp_dir):
                    continue

                current_time = time.time()
                deleted = 0

                for filename in os.listdir(self.temp_dir):
                    file_path = os.path.join(self.temp_dir, filename)

                    # 跳过目录
                    if os.path.isdir(file_path):
                        continue

                    # 24小时前的文件将被删除
                    if os.path.getmtime(file_path) < current_time - 86400:
                        try:
                            os.remove(file_path)
                            deleted += 1
                        except Exception as e:
                            logger.error(f"删除临时文件失败: {file_path}, {e}")

                if deleted > 0:
                    logger.info(f"已清理 {deleted} 个临时文件")

            except Exception as e:
                logger.error(f"清理临时文件任务出错: {e}")

    async def terminate(self):
        """插件被卸载/停用时调用"""
        # 保存消息缓存和配置
        self.save_message_cache()
        self.save_config_file()

        # 保存失败消息缓存
        if hasattr(self, 'forward_manager') and hasattr(self.forward_manager, 'save_failed_messages_cache'):
            self.forward_manager.save_failed_messages_cache()

        # 取消清理任务
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
            logger.debug("已取消消息ID清理任务")

        logger.debug("插件已终止，数据已保存")

    # 消息监听器，委托给MessageListener类处理
    # 修改装饰器的顺序，并确保正确使用filter模块    @filter.event_message_type(filter.EventMessageType.ALL)
    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    async def on_all_message(self, event: AstrMessageEvent):
        """监听所有消息并委托给message_listener处理"""
        logger.info(f"TurnRigPlugin 收到消息: {event.message_str} 从 {event.get_sender_name()}")
        try:
            # 检查是否为群文件上传通知
            if hasattr(event.message_obj, "notice_type") and event.message_obj.notice_type == "group_upload":
                logger.info("拦截到群文件上传通知事件")
                await self.message_listener.on_group_upload_notice(event)
                return MessageEventResult.PASS            # 检查是否为文件类型消息
            if hasattr(event.message_obj, "message") and isinstance(event.message_obj.message, list):
                for msg_part in event.message_obj.message:
                    if isinstance(msg_part, dict) and msg_part.get('type') == 'file':
                        logger.info(f"检测到文件类型消息: {msg_part}")
                        break

            # 添加简单的直接响应来测试监听器是否被触发
            logger.info(f"消息平台: {event.get_platform_name()}, 消息类型: {event.get_message_type()}")
            logger.info(f"统一消息来源: {event.unified_msg_origin}")

            # 委托给message_listener处理
            await self.message_listener.on_all_message(event)
            logger.info("消息处理完成")
        except Exception as e:
            logger.error(f"处理消息时出错: {e}")
            import traceback
            logger.error(traceback.format_exc())
      # 新增方法，用于处理群文件上传事件
    @filter.event_message_type(filter.EventMessageType.ALL)
    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    async def on_group_notice(self, event):
        """处理群通知事件"""
        try:
            # 检查是否为文件上传通知
            if hasattr(event.message_obj, "notice_type") and event.message_obj.notice_type == "group_upload":
                logger.info(f"收到群文件上传通知: {event}")
                await self.message_listener.on_group_upload_notice(event)
        except Exception as e:
            logger.error(f"处理群通知事件出错: {e}")
            import traceback
            logger.error(traceback.format_exc())
        return MessageEventResult().continue_event()

    # 命令组定义必须保留在主类中，但实际处理逻辑委托给CommandHandlers类
    @filter.command_group("turnrig")
    async def turnrig(self, event: AstrMessageEvent):
        """转发侦听插件指令组"""
        pass

    @turnrig.command("list")
    async def list_tasks(self, event: AstrMessageEvent):
        """列出所有转发任务"""
        result = await self.command_handlers.handle_list_tasks(event)
        yield result

    @turnrig.command("status")
    async def status(self, event: AstrMessageEvent, task_id: str = None):
        """查看特定任务的缓存状态"""
        result = await self.command_handlers.handle_status(event, task_id)
        yield result

    @turnrig.command("create")
    async def create_task(self, event: AstrMessageEvent, task_name: str = None):
        """创建新的转发任务"""
        result = await self.command_handlers.handle_create_task(event, task_name)
        yield result

    @turnrig.command("delete")
    async def delete_task(self, event: AstrMessageEvent, task_id: str = None):
        """删除转发任务"""
        result = await self.command_handlers.handle_delete_task(event, task_id)
        yield result

    @turnrig.command("enable")
    async def enable_task(self, event: AstrMessageEvent, task_id: str = None):
        """启用转发任务"""
        result = await self.command_handlers.handle_enable_task(event, task_id)
        yield result

    @turnrig.command("disable")
    async def disable_task(self, event: AstrMessageEvent, task_id: str = None):
        """禁用转发任务"""
        result = await self.command_handlers.handle_disable_task(event, task_id)
        yield result

    @turnrig.command("monitor")
    async def add_monitor(self, event: AstrMessageEvent, task_id: str = None, session_id: str = None):
        """添加监听源"""
        result = await self.command_handlers.handle_add_monitor(event, task_id, session_id)
        yield result

    @turnrig.command("unmonitor")
    async def remove_monitor(self, event: AstrMessageEvent, task_id: str = None, session_id: str = None):
        """删除监听源"""
        result = await self.command_handlers.handle_remove_monitor(event, task_id, session_id)
        yield result

    @turnrig.command("target")
    async def add_target(self, event: AstrMessageEvent, task_id: str = None, target_session: str = None):
        """添加转发目标"""
        result = await self.command_handlers.handle_add_target(event, task_id, target_session)
        yield result

    @turnrig.command("untarget")
    async def remove_target(self, event: AstrMessageEvent, task_id: str = None, target_session: str = None):
        """删除转发目标"""
        result = await self.command_handlers.handle_remove_target(event, task_id, target_session)
        yield result

    @turnrig.command("threshold")
    async def set_threshold(self, event: AstrMessageEvent, task_id: str = None, threshold: int = None):
        """设置消息阈值"""
        result = await self.command_handlers.handle_set_threshold(event, task_id, threshold)
        yield result

    @turnrig.command("rename")
    async def rename_task(self, event: AstrMessageEvent, task_id: str = None, new_name: str = None):
        """重命名任务"""
        result = await self.command_handlers.handle_rename_task(event, task_id, new_name)
        yield result

    @turnrig.command("forward")
    async def manual_forward(self, event: AstrMessageEvent, task_id: str = None, session_id: str = None):
        """手动触发转发"""
        result = await self.command_handlers.handle_manual_forward(event, task_id, session_id)
        yield result

    @turnrig.command("cleanup")
    async def cleanup_ids(self, event: AstrMessageEvent, days: int = 7):
        """清理过期的消息ID"""
        result = await self.command_handlers.handle_cleanup_ids(event, days)
        yield result

    @turnrig.command("adduser")
    async def add_user_in_group(self, event: AstrMessageEvent, task_id: str = None, group_id: str = None, user_id: str = None):
        """添加群聊内特定用户到监听列表"""
        result = await self.command_handlers.handle_add_user_in_group(event, task_id, group_id, user_id)
        yield result

    @turnrig.command("removeuser")
    async def remove_user_from_group(self, event: AstrMessageEvent, task_id: str = None, group_id: str = None, user_id: str = None):
        """从监听列表移除群聊内特定用户"""
        result = await self.command_handlers.handle_remove_user_from_group(event, task_id, group_id, user_id)
        yield result

    @turnrig.command("help")
    async def turnrig_help(self, event: AstrMessageEvent):
        """显示帮助信息"""
        result = await self.command_handlers.handle_turnrig_help(event)
        yield result

    # tr 简化命令组
    @filter.command_group("tr")
    async def tr(self, event: AstrMessageEvent):
        """转发侦听插件简化指令组"""
        pass

    @tr.command("add")
    async def tr_add_monitor(self, event: AstrMessageEvent, task_id: str = None):
        """将当前会话添加到监听列表"""
        result = await self.command_handlers.handle_tr_add_monitor(event, task_id)
        yield result

    @tr.command("remove")
    async def tr_remove_monitor(self, event: AstrMessageEvent, task_id: str = None):
        """将当前会话从监听列表移除"""
        result = await self.command_handlers.handle_tr_remove_monitor(event, task_id)
        yield result

    @tr.command("target")
    async def tr_add_target(self, event: AstrMessageEvent, task_id: str = None):
        """将当前会话添加为转发目标"""
        result = await self.command_handlers.handle_tr_add_target(event, task_id)
        yield result

    @tr.command("untarget")
    async def tr_remove_target(self, event: AstrMessageEvent, task_id: str = None):
        """将当前会话从转发目标移除"""
        result = await self.command_handlers.handle_tr_remove_target(event, task_id)
        yield result

    @tr.command("list")
    async def tr_list_tasks(self, event: AstrMessageEvent):
        """列出所有转发任务"""
        result = await self.command_handlers.handle_tr_list_tasks(event)
        yield result

    @tr.command("adduser")
    async def tr_add_user_in_group(self, event: AstrMessageEvent, task_id: str = None, user_id: str = None):
        """将指定用户添加到当前群聊的监听列表"""
        result = await self.command_handlers.handle_tr_add_user_in_group(event, task_id, user_id)
        yield result

    @tr.command("removeuser")
    async def tr_remove_user_from_group(self, event: AstrMessageEvent, task_id: str = None, user_id: str = None):
        """将指定用户从当前群聊的监听列表移除"""
        result = await self.command_handlers.handle_tr_remove_user_from_group(event, task_id, user_id)
        yield result

    @tr.command("help")
    async def tr_help(self, event: AstrMessageEvent):
        """显示简化指令帮助"""
        result = await self.command_handlers.handle_tr_help(event)
        yield result
