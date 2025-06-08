import time

from astrbot.api import logger


class RetryManager:
    """
    消息重试管理器喵～ 🔄
    负责重新发送失败的消息，不放弃任何一条重要消息！ ฅ(^•ω•^ฅ
    
    这个小助手会帮你：
    - 🔄 智能重试失败的消息
    - ⏰ 控制重试间隔时间
    - 📊 管理重试计数
    - 🚫 放弃无希望的消息
    
    Note:
        使用指数退避策略，避免频繁重试造成负担喵！ ⚠️
    """

    def __init__(self, plugin, cache_manager, message_builder, message_sender):
        """
        初始化重试管理器喵！(ฅ^•ω•^ฅ)
        
        Args:
            plugin: 插件实例喵
            cache_manager: 缓存管理器喵  
            message_builder: 消息构建器喵
            message_sender: 消息发送器喵
        """
        self.plugin = plugin
        self.cache_manager = cache_manager
        self.message_builder = message_builder
        self.message_sender = message_sender

    async def retry_failed_messages(self):
        """
        尝试重新发送缓存的失败消息喵～ 🔄
        这是重试的主要逻辑，会智能地处理所有失败消息！
        
        Note:
            使用指数退避算法，避免过于频繁的重试喵～ ⏰
        """
        # 获取所有失败消息喵～ 📋
        failed_messages_cache = self.cache_manager.get_all_failed_messages()
        if not failed_messages_cache:
            return

        logger.info(f"开始重试发送失败消息，共 {len(failed_messages_cache)} 个目标会话喵～ 🚀")

        # 一个一个会话地处理喵～ 🔄
        for target_session in list(failed_messages_cache.keys()):
            messages = failed_messages_cache[target_session]

            # 处理这个会话的所有失败消息喵～ 📤
            for i, msg in enumerate(list(messages)):
                try:
                    # 增加重试计数喵～ 📊
                    retry_count = self.cache_manager.increment_retry_count(
                        target_session, i
                    )

                    # 检查是否超过重试限制喵～ ⚠️
                    if retry_count > 5:
                        logger.warning(f"消息重试次数超过5次，放弃重试喵: {msg} 😿")
                        # 从失败缓存中永久删除喵～ 🗑️
                        self.cache_manager.remove_failed_message(
                            target_session, msg["task_id"], msg["source_session"]
                        )
                        continue

                    # 根据重试次数指数增加等待时间，避免频繁重试喵～ ⏰
                    # 第1次：立即，第2次：1小时，第3次：4小时，第4次：9小时...
                    # 判断上次重试时间是否足够长喵～ 🕐
                    last_retry_time = msg.get("last_retry_time", 0)
                    current_time = time.time()

                    # 计算需要等待的时间（小时）喵～ 📐
                    wait_hours = (retry_count - 1) ** 2
                    wait_seconds = wait_hours * 3600

                    time_since_last_retry = current_time - last_retry_time
                    if time_since_last_retry < wait_seconds:
                        # 还没到重试时间，跳过喵～ ⏭️
                        logger.debug(
                            f"消息重试冷却中，还需等待 {(wait_seconds - time_since_last_retry) / 3600:.1f} 小时喵: {msg} 😴"
                        )
                        continue

                    # 更新最后重试时间喵～ 🕐
                    msg["last_retry_time"] = current_time

                    task_id = msg["task_id"]
                    source_session = msg["source_session"]

                    # 检查任务是否存在、是否启用、消息缓存是否存在喵～ ✅
                    if not await self._validate_retry_prerequisites(
                        task_id, source_session
                    ):
                        continue

                    # 检查目标会话格式喵～ 🔍
                    target_parts = (
                        target_session.split(":", 2) if ":" in target_session else []
                    )
                    if len(target_parts) != 3:
                        logger.warning(f"目标会话格式无效喵: {target_session} ❌")
                        continue

                    target_platform, target_type, target_id = target_parts

                    logger.info(
                        f"重试发送任务 {task_id} 从 {source_session} 到 {target_session} 的消息喵～ 🔄"
                    )

                    # 获取有效消息喵～ 📥
                    valid_messages = self.plugin.message_cache.get(task_id, {}).get(
                        source_session, []
                    )

                    if not valid_messages:
                        logger.warning(
                            f"任务 {task_id} 会话 {source_session} 的消息缓存为空，无法重试喵～ 📭"
                        )
                        continue

                    # 根据平台选择发送方式喵～ 🎯
                    if target_platform == "aiocqhttp":
                        await self._retry_send_to_qq(target_session, valid_messages)
                        # 发送成功，删除失败缓存记录喵～ ✅
                        self.cache_manager.remove_failed_message(
                            target_session, task_id, source_session
                        )
                    else:
                        logger.warning(
                            f"目前重试功能只支持QQ平台，跳过 {target_session} 喵～ ⏭️"
                        )
                        # 对于非QQ平台，不再重试，直接删除缓存记录喵～ 🗑️
                        self.cache_manager.remove_failed_message(
                            target_session, task_id, source_session
                        )

                except Exception as e:
                    # 重试过程中出错了喵！ 😿
                    logger.error(f"重试发送消息到 {target_session} 失败喵: {e}")

    async def _validate_retry_prerequisites(
        self, task_id: str, source_session: str
    ) -> bool:
        """
        验证重试的前提条件喵～ ✅
        确保任务存在、启用且有消息可以重试！
        
        Args:
            task_id: 任务ID喵
            source_session: 源会话ID喵

        Returns:
            条件满足返回True，否则返回False喵
            
        Note:
            只有满足所有条件的消息才会被重试喵！ 🔍
        """
        # 检查任务是否存在喵～ 🔍
        task = self.plugin.get_task_by_id(task_id)
        if not task:
            logger.warning(f"任务 {task_id} 不存在，无法重试转发喵～ 😿")
            return False

        # 检查任务是否启用喵～ 🔍
        if not task.get("enabled", True):
            logger.warning(f"任务 {task_id} 已禁用，无法重试转发喵～ 🚫")
            return False

        # 检查消息缓存是否存在喵～ 🔍
        if (
            task_id not in self.plugin.message_cache
            or source_session not in self.plugin.message_cache[task_id]
            or not self.plugin.message_cache[task_id][source_session]
        ):
            logger.warning(
                f"任务 {task_id} 会话 {source_session} 的消息缓存已清空，无法重试转发喵～ 📭"
            )
            return False

        return True

    async def _retry_send_to_qq(self, target_session: str, valid_messages: list[dict]):
        """
        重试发送消息到QQ平台喵～ 📡
        专门处理QQ平台的重试发送逻辑！
        
        Args:
            target_session: 目标会话ID喵
            valid_messages: 有效的消息列表喵
            
        Note:
            会构建转发节点并使用原生API发送喵～ ✨
        """
        nodes_list = []

        # 构建消息节点喵～ 🏗️
        for msg_data in valid_messages:
            try:
                node = await self.message_builder.build_forward_node(msg_data)
                nodes_list.append(node)
            except Exception as e:
                # 构建节点失败了喵！ 😿
                logger.error(f"重试时构造转发消息节点失败喵: {e}")

        # 添加底部信息节点喵～ 📝
        footer_node = self.message_builder.build_footer_node(
            "", len(valid_messages), True
        )
        nodes_list.append(footer_node)

        # 直接使用原生API发送喵～ 📡
        await self.message_sender.send_forward_message_via_api(
            target_session, nodes_list
        )
        logger.info(f"成功重试发送消息到 {target_session} 喵～ ✅")
