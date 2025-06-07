import os
import json
import asyncio
from astrbot.api import logger
from typing import Dict, List, Any

class CacheManager:
    """处理消息缓存功能的类"""
    
    def __init__(self, plugin):
        self.plugin = plugin
        self.failed_messages_cache = {}
        self.cache_path = os.path.join(self.plugin.data_dir, "failed_messages_cache.json")
        # 加载缓存
        self.load_failed_messages_cache()
        # 启动定期保存任务
        asyncio.create_task(self.periodic_cache_operations())
    
    def load_failed_messages_cache(self):
        """从文件加载失败消息缓存"""
        try:
            if os.path.exists(self.cache_path):
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    cache_data = json.load(f)
                    
                    self.failed_messages_cache = {}
                    for target_session, messages in cache_data.items():
                        self.failed_messages_cache[target_session] = []
                        for msg in messages:
                            self.failed_messages_cache[target_session].append({
                                "task_id": msg["task_id"],
                                "source_session": msg["source_session"],
                                "timestamp": msg["timestamp"],
                                "retry_count": msg["retry_count"]
                            })
                    
                    logger.info(f"已从文件加载 {len(self.failed_messages_cache)} 个失败会话的缓存")
        except Exception as e:
            logger.error(f"加载失败消息缓存时出错: {e}")
            self.failed_messages_cache = {}
    
    def save_failed_messages_cache(self):
        """将失败消息缓存保存到文件"""
        try:
            serialized_cache = {}
            for target_session, messages in self.failed_messages_cache.items():
                serialized_cache[target_session] = []
                for msg in messages:
                    serialized_cache[target_session].append({
                        "task_id": msg["task_id"],
                        "source_session": msg["source_session"],
                        "timestamp": msg["timestamp"],
                        "retry_count": msg["retry_count"]
                    })
            
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(serialized_cache, f, ensure_ascii=False, indent=2)
                
            logger.debug(f"已将失败消息缓存保存到 {self.cache_path}")
        except Exception as e:
            logger.error(f"保存失败消息缓存时出错: {e}")
    async def periodic_cache_operations(self):
        """定期保存缓存"""
        while True:
            try:
                await asyncio.sleep(1800)  # 每30分钟保存一次（原来是15分钟）
                self.save_failed_messages_cache()
            except Exception as e:
                logger.error(f"定期缓存操作失败: {e}")
    
    def add_failed_message(self, target_session: str, task_id: str, source_session: str):
        """添加失败消息到缓存"""
        if target_session not in self.failed_messages_cache:
            self.failed_messages_cache[target_session] = []
        
        # 检查是否已经有相同的失败记录
        is_duplicate = False
        for existing_item in self.failed_messages_cache[target_session]:
            if (existing_item["task_id"] == task_id and 
                existing_item["source_session"] == source_session):
                is_duplicate = True
                break
        
        if not is_duplicate:
            cache_item = {
                "task_id": task_id,
                "source_session": source_session,
                "timestamp": int(asyncio.get_event_loop().time()),
                "retry_count": 0
            }
            self.failed_messages_cache[target_session].append(cache_item)
            logger.info(f"已将消息添加到失败缓存，将在稍后重试发送到 {target_session}")
            self.save_failed_messages_cache()
        
        return not is_duplicate
    
    def remove_failed_message(self, target_session: str, task_id: str, source_session: str):
        """从缓存中移除失败消息"""
        if target_session in self.failed_messages_cache:
            for cached_msg in list(self.failed_messages_cache[target_session]):
                if cached_msg["task_id"] == task_id and cached_msg["source_session"] == source_session:
                    self.failed_messages_cache[target_session].remove(cached_msg)
            
            if not self.failed_messages_cache[target_session]:
                del self.failed_messages_cache[target_session]
            
            self.save_failed_messages_cache()
            return True
        return False
    
    def get_all_failed_messages(self):
        """获取所有失败消息"""
        return self.failed_messages_cache
    
    def increment_retry_count(self, target_session: str, message_index: int):
        """增加重试计数"""
        if target_session in self.failed_messages_cache and message_index < len(self.failed_messages_cache[target_session]):
            self.failed_messages_cache[target_session][message_index]["retry_count"] += 1
            return self.failed_messages_cache[target_session][message_index]["retry_count"]
        return 0
