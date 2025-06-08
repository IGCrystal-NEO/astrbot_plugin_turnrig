import asyncio
import json
import os

from astrbot.api import logger


class CacheManager:
    """
    消息缓存管理器喵～ 💾
    负责管理失败消息的缓存，确保重要消息不会丢失！ ฅ(^•ω•^ฅ
    
    这个小助手会帮你：
    - 📝 记录发送失败的消息
    - 🔄 管理重试计数
    - 💾 持久化缓存到文件
    - 🧹 定期清理过期数据
    
    Note:
        所有失败的消息都会被可爱地保存起来，等待重试喵！ ✨
    """

    def __init__(self, plugin):
        """
        初始化缓存管理器喵！(ฅ^•ω•^ฅ)
        
        Args:
            plugin: 插件实例，提供配置和数据路径喵～
        """
        self.plugin = plugin
        self.failed_messages_cache = {}  # 失败消息的小仓库喵～ 📦
        self.cache_path = os.path.join(
            self.plugin.data_dir, "failed_messages_cache.json"
        )
        
        # 加载缓存喵～ 📖
        self.load_failed_messages_cache()
        
        # 启动定期保存任务喵～ ⏰
        asyncio.create_task(self.periodic_cache_operations())

    def load_failed_messages_cache(self):
        """
        从文件加载失败消息缓存喵～ 📥
        把之前保存的失败消息都读取出来！
        
        Note:
            如果文件不存在或损坏，会创建新的空缓存喵～ 🆕
        """
        try:
            # 检查缓存文件是否存在喵～ 🔍
            if os.path.exists(self.cache_path):
                with open(self.cache_path, encoding="utf-8") as f:
                    cache_data = json.load(f)

                    self.failed_messages_cache = {}
                    # 一个一个重建缓存条目喵～ 🔧
                    for target_session, messages in cache_data.items():
                        self.failed_messages_cache[target_session] = []
                        for msg in messages:
                            self.failed_messages_cache[target_session].append(
                                {
                                    "task_id": msg["task_id"],
                                    "source_session": msg["source_session"],
                                    "timestamp": msg["timestamp"],
                                    "retry_count": msg["retry_count"],
                                }
                            )

                    logger.info(
                        f"已从文件加载 {len(self.failed_messages_cache)} 个失败会话的缓存喵～ ✅"
                    )
        except Exception as e:
            # 加载缓存失败了喵，创建空缓存 😿
            logger.error(f"加载失败消息缓存时出错喵: {e}")
            self.failed_messages_cache = {}

    def save_failed_messages_cache(self):
        """
        将失败消息缓存保存到文件喵～ 💾
        把所有的失败消息安全地存储起来！
        
        Note:
            会自动处理序列化和文件写入喵～ ✨
        """
        try:
            # 序列化缓存数据喵～ 📋
            serialized_cache = {}
            for target_session, messages in self.failed_messages_cache.items():
                serialized_cache[target_session] = []
                for msg in messages:
                    serialized_cache[target_session].append(
                        {
                            "task_id": msg["task_id"],
                            "source_session": msg["source_session"],
                            "timestamp": msg["timestamp"],
                            "retry_count": msg["retry_count"],
                        }
                    )

            # 写入文件喵～ 📝
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(serialized_cache, f, ensure_ascii=False, indent=2)

            logger.debug(f"已将失败消息缓存保存到 {self.cache_path} 喵～ 💫")
        except Exception as e:
            # 保存失败了喵！好可惜 😿
            logger.error(f"保存失败消息缓存时出错喵: {e}")

    async def periodic_cache_operations(self):
        """
        定期保存缓存喵～ ⏰
        每30分钟自动保存一次，确保数据不丢失！
        
        Note:
            这是一个后台任务，会一直运行喵～ 🔄
        """
        while True:
            try:
                # 睡眠30分钟喵～ 😴
                await asyncio.sleep(1800)  # 每30分钟保存一次（原来是15分钟）
                self.save_failed_messages_cache()
            except Exception as e:
                # 定期操作失败了喵 😿
                logger.error(f"定期缓存操作失败喵: {e}")

    def add_failed_message(
        self, target_session: str, task_id: str, source_session: str
    ):
        """
        添加失败消息到缓存喵～ 📝
        把发送失败的消息记录下来，准备重试！
        
        Args:
            target_session: 目标会话ID喵
            task_id: 任务ID喵
            source_session: 源会话ID喵
            
        Returns:
            如果是新记录返回True，重复记录返回False喵
            
        Note:
            会自动避免重复添加相同的失败记录喵！ 🔍
        """
        # 确保目标会话有缓存列表喵～ 📋
        if target_session not in self.failed_messages_cache:
            self.failed_messages_cache[target_session] = []

        # 检查是否已经有相同的失败记录喵～ 🔍
        is_duplicate = False
        for existing_item in self.failed_messages_cache[target_session]:
            if (
                existing_item["task_id"] == task_id
                and existing_item["source_session"] == source_session
            ):
                is_duplicate = True
                break

        # 如果不是重复记录，就添加到缓存喵～ ✨
        if not is_duplicate:
            cache_item = {
                "task_id": task_id,
                "source_session": source_session,
                "timestamp": int(asyncio.get_event_loop().time()),
                "retry_count": 0,
            }
            self.failed_messages_cache[target_session].append(cache_item)
            logger.info(f"已将消息添加到失败缓存，将在稍后重试发送到 {target_session} 喵～ 🔄")
            self.save_failed_messages_cache()

        return not is_duplicate

    def remove_failed_message(
        self, target_session: str, task_id: str, source_session: str
    ):
        """
        从缓存中移除失败消息喵～ 🗑️
        当消息成功发送后，就把它从失败缓存中移除！
        
        Args:
            target_session: 目标会话ID喵
            task_id: 任务ID喵
            source_session: 源会话ID喵
            
        Returns:
            成功移除返回True，未找到返回False喵
            
        Note:
            如果会话的所有失败消息都被移除，会删除整个会话缓存喵～ 🧹
        """
        if target_session in self.failed_messages_cache:
            # 查找并移除匹配的消息喵～ 🔍
            for cached_msg in list(self.failed_messages_cache[target_session]):
                if (
                    cached_msg["task_id"] == task_id
                    and cached_msg["source_session"] == source_session
                ):
                    self.failed_messages_cache[target_session].remove(cached_msg)

            # 如果会话没有失败消息了，就删除整个会话缓存喵～ 🧹
            if not self.failed_messages_cache[target_session]:
                del self.failed_messages_cache[target_session]

            self.save_failed_messages_cache()
            return True
        return False

    def get_all_failed_messages(self):
        """
        获取所有失败消息喵～ 📋
        返回完整的失败消息缓存！
        
        Returns:
            失败消息缓存字典喵～
            
        Note:
            可以用来查看当前有多少失败消息等待重试喵！ 📊
        """
        return self.failed_messages_cache

    def increment_retry_count(self, target_session: str, message_index: int):
        """
        增加重试计数喵～ 🔢
        每次重试失败后，都会增加重试计数！
        
        Args:
            target_session: 目标会话ID喵
            message_index: 消息在缓存中的索引喵
            
        Returns:
            更新后的重试计数喵
            
        Note:
            重试次数太多的消息可能会被放弃喵～ ⚠️
        """
        if target_session in self.failed_messages_cache and message_index < len(
            self.failed_messages_cache[target_session]
        ):
            # 增加重试计数喵～ ➕
            self.failed_messages_cache[target_session][message_index][
                "retry_count"
            ] += 1
            return self.failed_messages_cache[target_session][message_index][
                "retry_count"
            ]
        return 0
