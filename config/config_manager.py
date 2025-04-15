import os
import json
from astrbot.api import logger
from typing import Dict

class ConfigManager:
    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.config_path = os.path.join(self.data_dir, "config.json")
        self.cache_path = os.path.join(self.data_dir, "message_cache.json")
    
    def load_config(self):
        """从文件加载配置"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, "r", encoding="utf-8") as f:
                    logger.debug(f"已从 {self.config_path} 加载配置")
                    return json.load(f)
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
        return None
    
    def save_config(self, config):
        """保存配置到文件"""
        try:
            # 备份当前配置文件（如果存在）
            if os.path.exists(self.config_path):
                backup_path = f"{self.config_path}.bak"
                import shutil
                shutil.copy2(self.config_path, backup_path)
            
            # 保存新配置
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            logger.info(f"配置已保存到 {self.config_path}")
            return True
        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")
            return False
    
    def load_message_cache(self):
        """加载缓存的消息"""
        try:
            if os.path.exists(self.cache_path):
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    cache_data = json.load(f)
                    logger.debug(f"已从 {self.cache_path} 加载消息缓存")
                    
                    # 显示每个任务的缓存状态
                    for task_id, sessions in cache_data.items():
                        session_count = len(sessions)
                        total_msgs = sum(len(msgs) for msgs in sessions.values())
                        logger.debug(f"任务 {task_id} 缓存: {session_count} 个会话, 共 {total_msgs} 条消息")
                    
                    return cache_data
            else:
                logger.debug(f"消息缓存文件不存在，将在需要时创建: {self.cache_path}")
                return {}
        except Exception as e:
            logger.error(f"加载消息缓存失败: {e}")
            return {}
    
    def save_message_cache(self, message_cache: Dict):
        """保存消息缓存"""
        try:
            # 获取所有有效的任务ID
            valid_task_ids = set()
            config = self.load_config()
            if config and 'tasks' in config:
                valid_task_ids = {str(task.get('id', '')) for task in config['tasks']}
            
            # 清理缓存中不存在的任务
            cleaned_cache = {}
            for task_id, sessions in message_cache.items():
                if str(task_id) in valid_task_ids:
                    cleaned_cache[task_id] = sessions
                else:
                    logger.info(f"从缓存中移除已删除的任务 {task_id}")
            
            # 保存清理后的缓存
            cache_path = os.path.join(self.data_dir, "message_cache.json")
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(cleaned_cache, f, ensure_ascii=False, indent=4)
            logger.debug(f"已将消息缓存保存到 {cache_path}")
            return True
        except Exception as e:
            logger.error(f"保存消息缓存失败: {e}")
            return False