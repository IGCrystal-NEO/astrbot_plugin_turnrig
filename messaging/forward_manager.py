import asyncio
import os
import time
import traceback

from astrbot.api import logger

# 修改导入路径，使用forward子目录喵～ 📦
from .forward import (
    CacheManager,
    DownloadHelper,
    MessageBuilder,
    MessageSender,
    RetryManager,
)


class ForwardManager:
    """
    消息转发管理器喵～ ฅ(^•ω•^ฅ)
    负责协调各个组件，让消息能够安全地转发到目标会话喵！

    这个小可爱会帮你：
    - 📨 构建转发节点
    - 🎯 发送到各个平台
    - 🔄 重试失败的消息
    - 💾 管理消息缓存

    Note:
        所有转发操作都会经过这里喵！⚠️
    """

    def __init__(self, plugin):
        """
        初始化转发管理器喵！(ฅ^•ω•^ฅ)

        Args:
            plugin: 插件实例，提供各种配置和服务喵～
        """
        self.plugin = plugin

        # 创建媒体下载目录喵～ 📁
        self.image_dir = os.path.join(self.plugin.data_dir, "temp")
        os.makedirs(self.image_dir, exist_ok=True)

        # 初始化各个可爱的子组件喵～ ✨
        self.download_helper = DownloadHelper(self.image_dir)
        self.message_builder = MessageBuilder(self.download_helper, self.plugin)
        self.cache_manager = CacheManager(plugin)
        self.message_sender = MessageSender(plugin, self.download_helper)
        self.retry_manager = RetryManager(
            plugin, self.cache_manager, self.message_builder, self.message_sender
        )

        # 启动定期重试任务喵～ 🔄
        asyncio.create_task(self.periodic_retry_operations())

    async def periodic_retry_operations(self):
        """
        定期重试发送失败的消息喵～ 🔄
        每小时检查一次失败的消息，然后重新尝试发送喵！

        Note:
            这是一个后台任务，会一直运行直到程序停止喵～ ⏰
        """
        while True:
            try:
                # 睡眠一小时喵～ 😴
                await asyncio.sleep(3600)  # 每小时重试一次（原来是15分钟）
                await self.retry_manager.retry_failed_messages()
            except Exception as e:
                # 重试操作失败了喵！记录错误 😿
                logger.error(f"定期重试操作失败喵: {e}")

    def save_failed_messages_cache(self):
        """
        将失败消息缓存保存到文件喵～ 💾
        让重要的消息不会丢失喵！
        """
        self.cache_manager.save_failed_messages_cache()

    async def build_forward_node(self, msg_data: dict) -> dict:
        """
        构建单个转发节点喵～ 🏗️
        委托给MessageBuilder处理具体的构建逻辑！

        Args:
            msg_data: 消息数据字典喵

        Returns:
            构建好的转发节点字典喵～
        """
        return await self.message_builder.build_forward_node(msg_data)

    async def send_forward_message_via_api(
        self, target_session: str, nodes_list: list[dict]
    ) -> bool:
        """
        使用原生API发送转发消息喵～ 📡
        委托给MessageSender处理具体的发送逻辑！

        Args:
            target_session: 目标会话ID喵
            nodes_list: 转发节点列表喵

        Returns:
            发送成功返回True，失败返回False喵
        """
        return await self.message_sender.send_forward_message_via_api(
            target_session, nodes_list
        )

    async def send_with_fallback(
        self, target_session: str, nodes_list: list[dict]
    ) -> bool:
        """
        使用备选方案发送消息喵～ 🔄
        委托给MessageSender处理备选发送逻辑！

        Args:
            target_session: 目标会话ID喵
            nodes_list: 转发节点列表喵

        Returns:
            发送成功返回True，失败返回False喵
        """
        return await self.message_sender.send_with_fallback(target_session, nodes_list)

    async def retry_failed_messages(self):
        """
        重试发送失败消息喵～ 🔄
        委托给RetryManager处理重试逻辑！

        Note:
            会自动重试所有失败的消息喵～ ✨
        """
        await self.retry_manager.retry_failed_messages()

    async def forward_messages(self, task_id: str, session_id: str):
        """
        转发消息到目标会话喵～ 📬
        这是主要的转发逻辑，会处理所有的转发流程！

        Args:
            task_id: 任务ID喵
            session_id: 会话ID喵

        Note:
            会自动处理消息构建、发送和错误处理喵～ ⚡
        """
        try:
            # 获取任务信息喵～ 🔍
            task = self.plugin.get_task_by_id(task_id)
            if not task:
                logger.error(f"未找到ID为 {task_id} 的任务喵～ 😿")
                return

            # 检查目标会话喵～ 🎯
            target_sessions = task.get("target_sessions", [])
            if not target_sessions:
                logger.warning(f"任务 {task_id}: 没有设置任何转发目标，跳过转发喵～ ⏭️")
                return

            # 获取消息缓存喵～ 💾
            messages = self.plugin.message_cache.get(task_id, {}).get(session_id, [])
            if not messages:
                logger.warning(
                    f"任务 {task_id}: 会话 {session_id} 没有缓存的消息，跳过转发喵～ 📭"
                )
                return

            # 先筛选有效消息喵～ 🔍
            valid_messages = []
            for msg in messages:
                message_components = msg.get("messages", [])  # 修复：使用正确的字段名喵

                if message_components:
                    valid_messages.append(msg)
                else:
                    logger.warning(f"跳过空消息喵: {msg} 🚫")

            # 检查有效消息阈值喵～ 📊
            max_messages = task.get("max_messages", self.plugin.config.get("default_max_messages", 20))
            if len(valid_messages) < max_messages:
                logger.debug(
                    f"任务 {task_id}: 会话 {session_id} 有效消息数量 ({len(valid_messages)}) 未达到阈值 ({max_messages})，暂不转发喵～ ⏳"
                )
                return

            if not valid_messages:
                logger.warning(
                    f"任务 {task_id}: 会话 {session_id} 没有有效消息，跳过转发喵～ 📭"
                )
                return

            logger.info(
                f"任务 {task_id}: 将 {len(valid_messages)} 条有效消息从 {session_id} 转发到 {len(target_sessions)} 个目标喵～ 🚀"
            )

            # 获取来源信息喵～ 📍
            source_type = (
                session_id.split(":", 2)[1] if ":" in session_id else "Unknown"
            )
            source_id = (
                session_id.split(":", 2)[2]
                if ":" in session_id and len(session_id.split(":", 2)) > 2
                else "Unknown"
            )
            is_group = "Group" in source_type
            source_name = f"群 {source_id}" if is_group else f"用户 {source_id}"

            # 构建节点列表喵～ 🏗️
            nodes_list = []

            for msg in valid_messages:
                # 检查消息是否包含转发组件喵～ 🔍
                message_components = msg.get("messages", [])
                has_forward = False

                for comp in message_components:
                    if isinstance(comp, dict) and comp.get("type") == "forward":
                        if "nodes" in comp and isinstance(comp["nodes"], list):
                            # 创建嵌套转发消息的节点，使用原始转发ID喵～ 📤
                            forward_id = comp.get('id', '未知ID')
                            forward_node_count = len(comp['nodes'])

                            logger.info(f"创建嵌套转发消息节点喵: {forward_id} (包含 {forward_node_count} 条消息) 📨")

                            # 构建包含嵌套转发的节点，使用原始ID而不是重构节点喵～ 🏗️
                            nested_forward_node = {
                                "type": "node",
                                "data": {
                                    "name": msg.get("sender_name", "未知用户"),
                                    "uin": str(msg.get("sender_id", "0")),
                                    "content": [
                                        {
                                            "type": "forward",
                                            "data": {
                                                "id": forward_id
                                            }
                                        }
                                    ],
                                    "time": msg.get("timestamp", int(time.time()))
                                }
                            }

                            nodes_list.append(nested_forward_node)
                            has_forward = True
                            break

                # 如果没有转发组件，使用普通的节点构建方式喵～ 🏗️
                if not has_forward:
                    node = await self.build_forward_node(msg)
                    nodes_list.append(node)

            # 添加底部信息节点喵～ 📝
            footer_node = self.message_builder.build_footer_node(
                source_name, len(valid_messages)
            )
            nodes_list.append(footer_node)

            # 生成这批消息的防重复标识符喵～ 🛡️
            import hashlib
            message_batch_content = str([msg.get("message_outline", "") + str(msg.get("timestamp", 0)) for msg in valid_messages])
            batch_hash = hashlib.md5(message_batch_content.encode()).hexdigest()[:8]
            
            # 向每个目标会话发送消息喵～ 📤
            for target_session in target_sessions:
                try:
                    # 解析目标会话信息喵～ 🔍
                    target_parts = (
                        target_session.split(":", 2) if ":" in target_session else []
                    )
                    if len(target_parts) != 3:
                        logger.warning(f"目标会话格式无效喵: {target_session} ❌")
                        continue

                    target_platform, target_type, target_id = target_parts

                    # 检查平台适配器是否存在喵～ 🔍
                    platform = self.plugin.context.get_platform(target_platform)
                    if not platform:
                        logger.warning(f"未找到平台适配器喵: {target_platform} 😿")
                        continue

                    # 生成这次转发的批次ID喵～ 🆔
                    batch_id = f"forward_{target_session}_{batch_hash}"

                    # 根据平台选择发送方式喵～ 🎯
                    if target_platform == "aiocqhttp":
                        logger.debug(
                            f"开始尝试发送QQ合并转发消息到 {target_session} 喵～ 📡"
                        )
                        api_result = await self.send_forward_message_via_api(
                            target_session, nodes_list
                        )

                        if api_result:
                            # 发送成功，标记批次ID防止重复喵～ ✅
                            self.message_sender._add_sent_message(target_session, batch_id)
                        elif not api_result:
                            logger.warning(
                                "使用原生API发送转发消息失败，但已通过备选方案处理喵～ 🔄"
                            )
                            # 备选方案可能也成功了，为安全起见也标记一下喵～ 🛡️
                            self.message_sender._add_sent_message(target_session, batch_id)

                        # 清除失败缓存喵～ 🧹
                        self.cache_manager.remove_failed_message(
                            target_session, task_id, session_id
                        )
                    else:
                        # 非QQ平台使用常规方式发送喵～ 📱
                        await self.message_sender.send_to_non_qq_platform(
                            target_session, source_name, valid_messages
                        )
                        # 非QQ平台发送后也标记批次ID喵～ 🆔
                        self.message_sender._add_sent_message(target_session, batch_id)

                    logger.info(f"成功将消息转发到 {target_session} 喵～ ✅")

                except Exception as e:
                    # 转发失败了喵，记录错误 😿
                    logger.error(f"转发消息到 {target_session} 失败喵: {e}")
                    logger.error(traceback.format_exc())

                    # 记录失败消息到缓存喵～ 💾
                    self.cache_manager.add_failed_message(
                        target_session, task_id, session_id
                    )

            # 清除已处理的消息缓存喵～ 🧹
            if task_id in self.plugin.message_cache and session_id in self.plugin.message_cache[task_id]:
                self.plugin.message_cache[task_id][session_id] = []
                logger.info(f"任务 {task_id}: 已清除会话 {session_id} 的消息缓存喵～ ✨")

            self.plugin.save_message_cache()

        except Exception as e:
            # 转发过程中出错了喵！ 😿
            logger.error(f"转发消息时出错喵: {e}")
            logger.error(traceback.format_exc())
