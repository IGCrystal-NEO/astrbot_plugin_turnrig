from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star
from astrbot.api import logger

# 更新导入路径
from ..utils.session_formatter import normalize_session_id

class CommandHandlers:
    """命令处理逻辑的实现类，但不直接处理指令注册"""
    def __init__(self, plugin_instance):
        """
        初始化命令处理器
        
        Args:
            plugin_instance: TurnRigPlugin的实例，用于访问其方法和属性
        """
        self.plugin = plugin_instance

    def _ensure_full_session_id(self, session_id):
        """确保会话ID是完整格式喵～"""
        normalized_id = normalize_session_id(session_id)
        
        # 检查是否包含两个冒号，表示是完整会话ID
        if normalized_id.count(':') == 2:
            return normalized_id
        else:
            logger.warning(f"会话ID '{session_id}' 不是有效的完整会话ID格式，已转换为 '{normalized_id}' 但可能仍然无效")
            return normalized_id
    
    # turnrig 命令组处理方法
    async def handle_list_tasks(self, event: AstrMessageEvent):
        """列出所有转发任务喵～"""
        tasks = self.plugin.config.get('tasks', [])
        
        if not tasks:
            return event.plain_result("当前没有配置任何转发任务喵～")
            
        result = "当前配置的转发任务列表喵～：\n"
        for i, task in enumerate(tasks):
            status = "启用" if task.get('enabled', True) else "禁用"
            result += f"{i+1}. [{status}] {task.get('name', '未命名')} (ID: {task.get('id')})\n"
            result += f"  监听: {len(task.get('monitor_groups', []))} 个群, {len(task.get('monitor_private_users', []))} 个私聊用户\n"
            
            # 显示群内监听的用户数
            total_group_users = sum(len(users) for users in task.get('monitored_users_in_groups', {}).values())
            result += f"  监听群内用户: {total_group_users} 个\n"
            
            result += f"  目标: {', '.join(task.get('target_sessions', ['无']))}\n"
            result += f"  消息阈值: {task.get('max_messages', self.plugin.config.get('default_max_messages', 20))}\n"
        
        return event.plain_result(result)

    async def handle_status(self, event: AstrMessageEvent, task_id: str = None):
        """查看特定任务的缓存状态喵～"""
        if task_id is None:
            # 显示所有任务的状态统计
            if not self.plugin.message_cache:
                return event.plain_result("当前没有任何消息缓存喵～")
                
            result = "消息缓存状态喵～：\n"
            for tid, sessions in self.plugin.message_cache.items():
                task = self.plugin.get_task_by_id(tid)
                task_name = task.get('name', '未知任务') if task else f"ID: {tid}"
                session_count = len(sessions)
                total_msgs = sum(len(msgs) for msgs in sessions.values())
                
                result += f"- {task_name}: {session_count} 个会话, 共 {total_msgs} 条消息\n"
                
            return event.plain_result(result)
        else:
            # 显示指定任务的详细缓存
            if task_id not in self.plugin.message_cache:
                return event.plain_result(f"未找到任务 {task_id} 的消息缓存喵～")
                
            task = self.plugin.get_task_by_id(task_id)
            task_name = task.get('name', '未知任务') if task else f"ID: {task_id}"
            
            result = f"任务 {task_name} 的消息缓存状态喵～：\n"
            for session_id, messages in self.plugin.message_cache[task_id].items():
                result += f"- 会话 {session_id}: {len(messages)} 条消息\n"
                
            return event.plain_result(result)

    async def handle_create_task(self, event: AstrMessageEvent, task_name: str = None):
        """创建新的转发任务喵～"""
        if not event.is_admin():
            return event.plain_result("只有管理员才能创建转发任务喵～")
            
        if not task_name:
            task_name = f"新任务_{len(self.plugin.config['tasks']) + 1}"
            
        # 生成顺序ID，从当前最大ID+1开始
        task_id = str(self.plugin.get_max_task_id() + 1)
        new_task = {
            "id": task_id,
            "name": task_name,
            "monitor_groups": [],
            "monitor_private_users": [],
            "monitored_users_in_groups": {},
            "target_sessions": [],
            "max_messages": self.plugin.config.get('default_max_messages', 20),
            "enabled": True
        }
        
        self.plugin.config['tasks'].append(new_task)
        self.plugin.save_config_file()
        
        # 确保消息中的换行符正确显示
        return event.plain_result(f"已创建新的转发任务 [{task_name}]，ID: {task_id}\n\n"
                            f"请使用以下命令添加监听源和目标：\n"
                            f"/turnrig monitor {task_id} 群聊/私聊 <会话ID>\n"
                            f"/turnrig target {task_id} 群聊/私聊 <会话ID>")

    async def handle_delete_task(self, event: AstrMessageEvent, task_id: str = None):
        """删除转发任务喵～"""
        if not event.is_admin():
            return event.plain_result("只有管理员才能删除转发任务喵～")
            
        if not task_id:
            return event.plain_result("请指定要删除的任务ID喵～")
            
        task = self.plugin.get_task_by_id(task_id)
        if not task:
            return event.plain_result(f"未找到ID为 {task_id} 的任务喵～")
            
        # 从配置中删除任务
        self.plugin.config['tasks'] = [t for t in self.plugin.config['tasks'] if t.get('id') != task_id]
        
        # 如果有缓存，也一并删除
        if task_id in self.plugin.message_cache:
            del self.plugin.message_cache[task_id]
            
        self.plugin.save_config_file()
        self.plugin.save_message_cache()
        
        return event.plain_result(f"已删除任务 [{task.get('name')}]，ID: {task_id}")

    async def handle_enable_task(self, event: AstrMessageEvent, task_id: str = None):
        """启用转发任务喵～"""
        if not event.is_admin():
            return event.plain_result("只有管理员才能启用转发任务喵～")
            
        if not task_id:
            return event.plain_result("请指定要启用的任务ID喵～")
            
        task = self.plugin.get_task_by_id(task_id)
        if not task:
            return event.plain_result(f"未找到ID为 {task_id} 的任务喵～")
            
        task['enabled'] = True
        self.plugin.save_config_file()
        
        return event.plain_result(f"已启用任务 [{task.get('name')}]，ID: {task_id}")

    async def handle_disable_task(self, event: AstrMessageEvent, task_id: str = None):
        """禁用转发任务喵～"""
        if not event.is_admin():
            return event.plain_result("只有管理员才能禁用转发任务喵～")
            
        if not task_id:
            return event.plain_result("请指定要禁用的任务ID喵～")
            
        task = self.plugin.get_task_by_id(task_id)
        if not task:
            return event.plain_result(f"未找到ID为 {task_id} 的任务喵～")
            
        task['enabled'] = False
        self.plugin.save_config_file()
        
        return event.plain_result(f"已禁用任务 [{task.get('name')}]，ID: {task_id}")

    async def handle_add_monitor(self, event: AstrMessageEvent, task_id: str = None, session_id: str = None):
        """添加监听源喵～"""
        if not event.is_admin():
            return event.plain_result("只有管理员才能添加监听源喵～")
            
        if not task_id or not session_id:
            return event.plain_result("请同时指定任务ID和要监听的会话ID喵～\n正确格式：/turnrig monitor <任务ID> 群聊/私聊 <会话ID>")
            
        task = self.plugin.get_task_by_id(task_id)
        if not task:
            return event.plain_result(f"未找到ID为 {task_id} 的任务喵～")
        
        # 确保使用完整会话ID格式
        full_session_id = self._ensure_full_session_id(session_id)
        
        # 判断是群聊还是私聊
        if "GroupMessage" in full_session_id:
            if full_session_id not in task.get('monitor_groups', []):
                task.setdefault('monitor_groups', []).append(full_session_id)
                self.plugin.save_config_file()
                return event.plain_result(f"已将群聊 {full_session_id} 添加到任务 [{task.get('name')}] 的监听列表喵～")
            else:
                return event.plain_result(f"群聊 {full_session_id} 已经在监听列表中了喵～")
        elif "FriendMessage" in full_session_id:
            if full_session_id not in task.get('monitor_private_users', []):
                task.setdefault('monitor_private_users', []).append(full_session_id)
                self.plugin.save_config_file()
                return event.plain_result(f"已将用户 {full_session_id} 添加到任务 [{task.get('name')}] 的私聊监听列表喵～")
            else:
                return event.plain_result(f"用户 {full_session_id} 已经在私聊监听列表中了喵～")
        else:
            return event.plain_result(f"无法识别会话ID格式: {full_session_id}，请检查输入喵～")

    async def handle_remove_monitor(self, event: AstrMessageEvent, task_id: str = None, session_id: str = None):
        """删除监听源喵～"""
        if not event.is_admin():
            return event.plain_result("只有管理员才能删除监听源喵～")
            
        if not task_id or not session_id:
            return event.plain_result("请同时指定任务ID和要删除的会话ID喵～")
            
        task = self.plugin.get_task_by_id(task_id)
        if not task:
            return event.plain_result(f"未找到ID为 {task_id} 的任务喵～")
        
        # 确保使用完整会话ID格式
        full_session_id = self._ensure_full_session_id(session_id)
        
        # 判断是群聊还是私聊
        if "GroupMessage" in full_session_id:
            if full_session_id in task.get('monitor_groups', []):
                task['monitor_groups'].remove(full_session_id)
                self.plugin.save_config_file()
                return event.plain_result(f"已将群聊 {full_session_id} 从任务 [{task.get('name')}] 的监听列表中删除喵～")
            else:
                return event.plain_result(f"群聊 {full_session_id} 不在监听列表中喵～")
        elif "FriendMessage" in full_session_id:
            if full_session_id in task.get('monitor_private_users', []):
                task['monitor_private_users'].remove(full_session_id)
                self.plugin.save_config_file()
                return event.plain_result(f"已将用户 {full_session_id} 从任务 [{task.get('name')}] 的私聊监听列表中删除喵～")
            else:
                return event.plain_result(f"用户 {full_session_id} 不在私聊监听列表中喵～")
        else:
            return event.plain_result(f"无法识别会话ID格式: {full_session_id}，请检查输入喵～")

    async def handle_add_target(self, event: AstrMessageEvent, task_id: str = None, target_session: str = None):
        """添加转发目标喵～"""
        if not event.is_admin():
            return event.plain_result("只有管理员才能添加转发目标喵～")
            
        if not task_id or not target_session:
            return event.plain_result("请同时指定任务ID和目标会话ID喵～")
            
        task = self.plugin.get_task_by_id(task_id)
        if not task:
            return event.plain_result(f"未找到ID为 {task_id} 的任务喵～")
        
        # 确保使用完整会话ID格式
        full_target_session = self._ensure_full_session_id(target_session)
        
        if full_target_session not in task.get('target_sessions', []):
            task.setdefault('target_sessions', []).append(full_target_session)
            self.plugin.save_config_file()
            return event.plain_result(f"已将 {full_target_session} 添加到任务 [{task.get('name')}] 的转发目标列表喵～")
        else:
            return event.plain_result(f"会话 {full_target_session} 已经在转发目标列表中了喵～")

    async def handle_remove_target(self, event: AstrMessageEvent, task_id: str = None, target_session: str = None):
        """删除转发目标喵～"""
        if not event.is_admin():
            return event.plain_result("只有管理员才能删除转发目标喵～")
            
        if not task_id or not target_session:
            return event.plain_result("请同时指定任务ID和要删除的目标会话ID喵～")
            
        task = self.plugin.get_task_by_id(task_id)
        if not task:
            return event.plain_result(f"未找到ID为 {task_id} 的任务喵～")
        
        # 确保使用完整会话ID格式
        full_target_session = self._ensure_full_session_id(target_session)
        
        if full_target_session in task.get('target_sessions', []):
            task['target_sessions'].remove(full_target_session)
            self.plugin.save_config_file()
            return event.plain_result(f"已将 {full_target_session} 从任务 [{task.get('name')}] 的转发目标列表中删除喵～")
        else:
            return event.plain_result(f"会话 {full_target_session} 不在转发目标列表中喵～")

    async def handle_set_threshold(self, event: AstrMessageEvent, task_id: str = None, threshold: int = None):
        """设置消息阈值喵～"""
        if not event.is_admin():
            return event.plain_result("只有管理员才能设置消息阈值喵～")
            
        if not task_id or threshold is None:
            return event.plain_result("请同时指定任务ID和消息阈值喵～")
            
        if threshold <= 0:
            return event.plain_result("消息阈值必须大于0喵～")
            
        task = self.plugin.get_task_by_id(task_id)
        if not task:
            return event.plain_result(f"未找到ID为 {task_id} 的任务喵～")
        
        task['max_messages'] = threshold
        self.plugin.save_config_file()
        return event.plain_result(f"已将任务 [{task.get('name')}] 的消息阈值设为 {threshold} 喵～")

    async def handle_rename_task(self, event: AstrMessageEvent, task_id: str = None, new_name: str = None):
        """重命名任务喵～"""
        if not event.is_admin():
            return event.plain_result("只有管理员才能重命名任务喵～")
            
        if not task_id or not new_name:
            return event.plain_result("请同时指定任务ID和新名称喵～")
            
        task = self.plugin.get_task_by_id(task_id)
        if not task:
            return event.plain_result(f"未找到ID为 {task_id} 的任务喵～")
        
        old_name = task.get('name', '未命名')
        task['name'] = new_name
        self.plugin.save_config_file()
        return event.plain_result(f"已将任务 [{old_name}] 重命名为 [{new_name}] 喵～")

    async def handle_manual_forward(self, event: AstrMessageEvent, task_id: str = None, session_id: str = None):
        """手动触发转发喵～"""
        if not event.is_admin():
            return event.plain_result("只有管理员才能手动触发转发喵～")
            
        if not task_id:
            return event.plain_result("请指定任务ID喵～")
            
        task = self.plugin.get_task_by_id(task_id)
        if not task:
            return event.plain_result(f"未找到ID为 {task_id} 的任务喵～")
        
        if not session_id:
            # 没有指定会话ID，转发所有会话
            if task_id not in self.plugin.message_cache:
                return event.plain_result("该任务没有任何缓存消息喵～")
                
            if not self.plugin.message_cache[task_id]:
                return event.plain_result("该任务没有任何缓存消息喵～")
                
            session_count = len(self.plugin.message_cache[task_id])
            total_msgs = sum(len(msgs) for msgs in self.plugin.message_cache[task_id].values())
            
            result = event.plain_result(f"正在转发任务 [{task.get('name')}] 的 {session_count} 个会话，共 {total_msgs} 条消息喵～")
            
            for session in list(self.plugin.message_cache[task_id].keys()):
                await self.plugin.forward_manager.forward_messages(task_id, session)
                
            return event.plain_result(f"已完成任务 [{task.get('name')}] 的所有消息转发喵～")
        else:
            # 确保使用完整会话ID格式
            full_session_id = self._ensure_full_session_id(session_id)
            
            # 只转发指定会话
            if task_id not in self.plugin.message_cache or full_session_id not in self.plugin.message_cache[task_id]:
                return event.plain_result(f"未找到任务 {task_id} 在会话 {full_session_id} 的缓存消息喵～")
                
            msg_count = len(self.plugin.message_cache[task_id][full_session_id])
            result = event.plain_result(f"正在转发任务 [{task.get('name')}] 在会话 {full_session_id} 的 {msg_count} 条消息喵～")
            
            await self.plugin.forward_manager.forward_messages(task_id, full_session_id)
            
            return event.plain_result(f"已完成任务 [{task.get('name')}] 在会话 {full_session_id} 的消息转发喵～")

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

· /turnrig target <任务ID> 群聊/私聊 <会话ID> - 添加转发目标

· /turnrig untarget <任务ID> 群聊/私聊 <会话ID> - 删除转发目标

· /turnrig threshold <任务ID> <数量> - 设置消息阈值

【其他功能】

· /turnrig rename <任务ID> <名称> - 重命名任务

· /turnrig forward <任务ID> [群聊/私聊 <会话ID>] - 手动触发转发

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

    # tr 简化命令组处理方法
    async def handle_tr_add_monitor(self, event: AstrMessageEvent, task_id: str = None):
        """将当前会话添加到监听列表喵～"""
        if not event.is_admin():
            return event.plain_result("只有管理员才能添加监听源喵～")
            
        if not task_id:
            return event.plain_result("请指定要添加到的任务ID喵～")
            
        task = self.plugin.get_task_by_id(task_id)
        if not task:
            return event.plain_result(f"未找到ID为 {task_id} 的任务喵～")
        
        # 自动获取当前会话ID
        current_session = event.unified_msg_origin
        
        # 判断是群聊还是私聊
        if "GroupMessage" in current_session:
            if current_session not in task.get('monitor_groups', []):
                task.setdefault('monitor_groups', []).append(current_session)
                self.plugin.save_config_file()
                return event.plain_result(f"已将当前群聊添加到任务 [{task.get('name')}] 的监听列表喵～")
            else:
                return event.plain_result(f"当前群聊已经在监听列表中了喵～")
        elif "FriendMessage" in current_session:
            if current_session not in task.get('monitor_private_users', []):
                task.setdefault('monitor_private_users', []).append(current_session)
                self.plugin.save_config_file()
                return event.plain_result(f"已将当前私聊用户添加到任务 [{task.get('name')}] 的监听列表喵～")
            else:
                return event.plain_result(f"当前私聊用户已经在监听列表中了喵～")
        else:
            return event.plain_result(f"当前会话类型不支持添加到监听列表喵～")

    async def handle_tr_remove_monitor(self, event: AstrMessageEvent, task_id: str = None):
        """将当前会话从监听列表移除喵～"""
        if not event.is_admin():
            return event.plain_result("只有管理员才能删除监听源喵～")
            
        if not task_id:
            return event.plain_result("请指定要移除的任务ID喵～")
            
        task = self.plugin.get_task_by_id(task_id)
        if not task:
            return event.plain_result(f"未找到ID为 {task_id} 的任务喵～")
        
        # 自动获取当前会话ID
        current_session = event.unified_msg_origin
        
        # 判断是群聊还是私聊
        if "GroupMessage" in current_session:
            if current_session in task.get('monitor_groups', []):
                task['monitor_groups'].remove(current_session)
                self.plugin.save_config_file()
                return event.plain_result(f"已将当前群聊从任务 [{task.get('name')}] 的监听列表中移除喵～")
            else:
                return event.plain_result(f"当前群聊不在监听列表中喵～")
        elif "FriendMessage" in current_session:
            if current_session in task.get('monitor_private_users', []):
                task['monitor_private_users'].remove(current_session)
                self.plugin.save_config_file()
                return event.plain_result(f"已将当前私聊用户从任务 [{task.get('name')}] 的监听列表中移除喵～")
            else:
                return event.plain_result(f"当前私聊用户不在监听列表中喵～")
        else:
            return event.plain_result(f"当前会话类型不支持从监听列表移除喵～")

    async def handle_tr_add_target(self, event: AstrMessageEvent, task_id: str = None):
        """将当前会话添加为转发目标喵～"""
        if not event.is_admin():
            return event.plain_result("只有管理员才能添加转发目标喵～")
            
        if not task_id:
            return event.plain_result("请指定要添加到的任务ID喵～")
            
        task = self.plugin.get_task_by_id(task_id)
        if not task:
            return event.plain_result(f"未找到ID为 {task_id} 的任务喵～")
        
        # 自动获取当前会话ID
        current_session = event.unified_msg_origin
        
        if current_session not in task.get('target_sessions', []):
            task.setdefault('target_sessions', []).append(current_session)
            self.plugin.save_config_file()
            return event.plain_result(f"已将当前会话添加到任务 [{task.get('name')}] 的转发目标列表喵～")
        else:
            return event.plain_result(f"当前会话已经在转发目标列表中了喵～")

    async def handle_tr_remove_target(self, event: AstrMessageEvent, task_id: str = None):
        """将当前会话从转发目标移除喵～"""
        if not event.is_admin():
            return event.plain_result("只有管理员才能删除转发目标喵～")
            
        if not task_id:
            return event.plain_result("请指定要移除的任务ID喵～")
            
        task = self.plugin.get_task_by_id(task_id)
        if not task:
            return event.plain_result(f"未找到ID为 {task_id} 的任务喵～")
        
        # 自动获取当前会话ID
        current_session = event.unified_msg_origin
        
        if current_session in task.get('target_sessions', []):
            task['target_sessions'].remove(current_session)
            self.plugin.save_config_file()
            return event.plain_result(f"已将当前会话从任务 [{task.get('name')}] 的转发目标列表中移除喵～")
        else:
            return event.plain_result(f"当前会话不在转发目标列表中喵～")

    async def handle_tr_list_tasks(self, event: AstrMessageEvent):
        """列出所有转发任务喵～(简化版)"""
        # 直接复用handle_list_tasks方法
        return await self.handle_list_tasks(event)

    async def handle_tr_help(self, event: AstrMessageEvent):
        """显示简化指令帮助喵～"""
        # 使用三引号字符串确保换行符被正确保留
        help_text = """▽ 转发侦听简化指令帮助 ▽

【简化指令列表】

· /tr add <任务ID> - 将当前会话添加到监听列表

· /tr remove <任务ID> - 将当前会话从监听列表移除

· /tr target <任务ID> - 将当前会话添加为转发目标

· /tr untarget <任务ID> - 将当前会话从转发目标移除

· /tr list - 列出所有转发任务

· /tr help - 显示此帮助

这些简化指令不需要手动输入会话ID，会自动使用当前会话的ID喵～

如果需要更多完整功能，请使用 /turnrig help 查看完整指令列表喵～"""
        # 确保使用plain_result以保留换行符
        return event.plain_result(help_text)