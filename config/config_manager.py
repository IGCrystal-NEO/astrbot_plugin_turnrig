import json
import os

from astrbot.api import logger


class ConfigManager:
    """
    配置管理器喵～
    负责管理插件配置和消息缓存的可爱小助手！ ฅ(^•ω•^ฅ
    """

    def __init__(self, data_dir):
        """
        初始化配置管理器喵！

        Args:
            data_dir: 数据存储目录喵～
        """
        self.data_dir = data_dir  # 数据存储的小窝喵～ 🏠
        self.config_path = os.path.join(
            self.data_dir, "config.json"
        )  # 配置文件的路径喵 📄
        self.cache_path = os.path.join(
            self.data_dir, "message_cache.json"
        )  # 缓存文件路径喵 💾

    def load_config(self):
        """
        从文件加载配置喵～
        把保存的配置文件读取出来！ ✨

        Returns:
            加载的配置字典，如果失败则返回None喵
        """
        try:
            # 检查配置文件是否存在喵～ 🔍
            if os.path.exists(self.config_path):
                with open(self.config_path, encoding="utf-8") as f:
                    logger.debug(f"已从 {self.config_path} 加载配置喵～ ✅")
                    return json.load(f)
        except Exception as e:
            # 出错了喵！好难过 😿
            logger.error(f"加载配置失败喵: {e}")
        return None

    def save_config(self, config):
        """
        保存配置到文件喵～
        把配置安全地保存起来！ 💾

        Args:
            config: 要保存的配置字典喵

        Returns:
            保存成功返回True，失败返回False喵
        """
        try:
            # 备份当前配置文件（如果存在）喵～ 🛡️
            if os.path.exists(self.config_path):
                backup_path = f"{self.config_path}.bak"
                import shutil

                shutil.copy2(self.config_path, backup_path)

            # 保存新配置喵！ ✨
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)

            logger.info(f"配置已保存到 {self.config_path} 喵～ 💫")
            return True
        except Exception as e:
            # 保存失败了喵，好伤心 😿
            logger.error(f"保存配置文件失败喵: {e}")
            return False

    def load_message_cache(self):
        """
        加载缓存的消息喵～
        把之前存储的消息缓存都读取出来！ 📮

        Returns:
            消息缓存字典喵～
        """
        try:
            # 检查缓存文件是否存在喵～ 🔍
            if os.path.exists(self.cache_path):
                with open(self.cache_path, encoding="utf-8") as f:
                    cache_data = json.load(f)
                    logger.debug(f"已从 {self.cache_path} 加载消息缓存喵～ ✅")

                    # 显示每个任务的缓存状态喵～ 📊
                    for task_id, sessions in cache_data.items():
                        session_count = len(sessions)
                        total_msgs = sum(len(msgs) for msgs in sessions.values())
                        logger.debug(
                            f"任务 {task_id} 缓存: {session_count} 个会话, 共 {total_msgs} 条消息喵～ 📋"
                        )

                    return cache_data
            else:
                logger.debug(
                    f"消息缓存文件不存在，将在需要时创建喵: {self.cache_path} 📝"
                )
                return {}
        except Exception as e:
            # 加载缓存失败了喵 😿
            logger.error(f"加载消息缓存失败喵: {e}")
            return {}

    def save_message_cache(self, message_cache: dict, current_config: dict = None):
        """
        保存消息缓存喵～
        把最新的消息缓存安全地存储起来！ 💾

        Args:
            message_cache: 要保存的消息缓存字典喵
            current_config: 当前配置字典，如果提供则使用它来验证任务ID喵

        Returns:
            保存成功返回True，失败返回False喵

        Note:
            修复：现在使用当前配置而不是从文件重新加载，避免任务被意外删除喵！ 🔧
        """
        try:
            # 获取所有有效的任务ID喵～ 🎯
            valid_task_ids = set()

            # 优先使用传入的当前配置，否则从文件加载喵～ ✨
            config = current_config
            if not config:
                config = self.load_config()
                logger.warning(
                    "save_message_cache: 没有提供当前配置，从文件加载（可能导致数据不一致）喵～ ⚠️"
                )

            if config and "tasks" in config:
                valid_task_ids = {str(task.get("id", "")) for task in config["tasks"]}

            # 清理缓存中不存在的任务喵～ 🧹
            cleaned_cache = {}
            for task_id, sessions in message_cache.items():
                if str(task_id) in valid_task_ids:
                    cleaned_cache[task_id] = sessions
                else:
                    logger.info(f"从缓存中移除已删除的任务 {task_id} 喵～ 🗑️")

            # 保存清理后的缓存喵！ ✨
            cache_path = os.path.join(self.data_dir, "message_cache.json")
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(cleaned_cache, f, ensure_ascii=False, indent=4)
            logger.debug(f"已将消息缓存保存到 {cache_path} 喵～ 💫")
            return True
        except Exception as e:
            # 保存缓存失败了喵，好可惜 😿
            logger.error(f"保存消息缓存失败喵: {e}")
            return False
