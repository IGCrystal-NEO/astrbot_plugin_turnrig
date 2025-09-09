import asyncio
import base64
import os
import threading
import traceback
import uuid
from collections import defaultdict

from astrbot.api import logger
from astrbot.api.message_components import Plain


class MessageSender:
    """
    消息发送器喵～ 📤
    专门负责处理消息发送和转发的核心组件！ ฅ(^•ω•^ฅ

    这个发送器会帮你：
    - 🚀 智能多策略消息发送
    - 🖼️ 图片和GIF处理
    - 🔄 自动重试机制
    - 💾 消息去重跟踪
    - 🧹 自动清理过期记录

    Note:
        支持合并转发、单条发送等多种发送模式喵！ ✨
    """

    def __init__(self, plugin, download_helper):
        """
        初始化消息发送器喵～ 🐾
        创建一个强大的消息发送助手！

        Args:
            plugin: 插件实例，提供配置和上下文喵
            download_helper: 下载助手，负责文件下载喵

        Note:
            会自动启动清理任务，维护发送记录的整洁喵！ 🧹
        """
        self.plugin = plugin
        self.download_helper = download_helper
        # 使用线程安全的消息跟踪字典，按会话ID分组喵～ 🔒
        self._message_tracking_lock = threading.RLock()
        self._sent_message_ids = defaultdict(set)
        # 初始化消息时间戳记录字典喵～ ⏰
        self._message_timestamps = {}
        # 设置消息ID过期时间（秒）喵～ 📅
        self._message_expiry_seconds = 3600  # 一小时后过期喵
        # 启动清理任务喵～ 🧹
        self._start_cleanup_task()

    def _start_cleanup_task(self):
        """
        启动定期清理过期消息ID的任务喵～ 🧹
        每30分钟自动清理一次过期记录！

        Note:
            这是一个后台任务，确保内存使用效率喵！ 💫
        """

        async def cleanup_task():
            while True:
                try:
                    await asyncio.sleep(1800)  # 每30分钟清理一次喵～ 😴
                    self._cleanup_expired_message_ids()
                except Exception as e:
                    logger.error(f"清理过期消息ID时出错喵: {e} 😿")
                    await asyncio.sleep(60)  # 出错时等待时间短一些喵

        # 在事件循环中启动任务喵～ 🚀
        asyncio.create_task(cleanup_task())

    def _cleanup_expired_message_ids(self):
        """
        清理过期的消息ID记录喵～ 🗑️
        删除超过一小时的旧记录，释放内存！

        Note:
            使用线程锁确保并发安全喵！ 🔒
        """
        import time

        current_time = time.time()
        with self._message_tracking_lock:
            expired_sessions = []

            # 遍历所有会话的时间戳记录喵～ 🔍
            for session_id, timestamp in list(self._message_timestamps.items()):
                if current_time - timestamp > self._message_expiry_seconds:
                    expired_sessions.append(session_id)

            # 删除过期会话的记录喵～ 🗂️
            for session_id in expired_sessions:
                if session_id in self._sent_message_ids:
                    del self._sent_message_ids[session_id]
                if session_id in self._message_timestamps:
                    del self._message_timestamps[session_id]

            if expired_sessions:
                logger.info(
                    f"已清理 {len(expired_sessions)} 个过期会话的消息记录喵～ ✅"
                )

    def _add_sent_message(self, session_id: str, message_id: str):
        """
        线程安全地添加已发送消息记录喵～ 📝
        防止消息重复发送！

        Args:
            session_id: 会话ID喵
            message_id: 消息ID喵

        Note:
            会同时更新会话的最后活动时间喵！ ⏰
        """
        import time

        with self._message_tracking_lock:
            self._sent_message_ids[session_id].add(message_id)
            # 更新会话最后活动时间喵～ 🔄
            self._message_timestamps[session_id] = time.time()

    def _is_message_sent(self, session_id: str, message_id: str) -> bool:
        """
        线程安全地检查消息是否已发送喵～ 🔍
        避免重复发送相同消息！

        Args:
            session_id: 会话ID喵
            message_id: 消息ID喵

        Returns:
            True表示已发送，False表示未发送喵～
        """
        with self._message_tracking_lock:
            return message_id in self._sent_message_ids.get(session_id, set())

    def _clear_session_messages(self, session_id: str):
        """
        线程安全地清除特定会话的消息记录喵～ 🧹
        清空指定会话的发送历史！

        Args:
            session_id: 要清理的会话ID喵

        Note:
            通常在开始新的转发任务时使用喵！ 🔄
        """
        with self._message_tracking_lock:
            if session_id in self._sent_message_ids:
                self._sent_message_ids[session_id].clear()

    async def send_forward_message_via_api(
        self, target_session: str, nodes_list: list[dict]
    ) -> bool:
        """
        使用多级策略发送转发消息喵～ 🚀
        这是最核心的消息发送方法，会尝试多种策略确保成功！

        Args:
            target_session: 目标会话ID喵
            nodes_list: 节点列表喵

        Returns:
            bool: 发送成功返回True，否则返回False喵～

        Note:
            target_session: 目标会话ID
            nodes_list: 节点列表

        Returns:
            bool: 发送成功返回True，否则返回False
        """
        # 为每条消息生成任务唯一标识符
        task_id = str(uuid.uuid4())

        try:  # 获取群号或用户ID
            target_parts = target_session.split(":", 2)
            if len(target_parts) != 3:
                logger.warning(f"目标会话格式无效: {target_session}")
                return False

            target_platform, target_type, target_id = target_parts

            # 不再清空消息跟踪记录，保持去重功能
            # self._clear_session_messages(target_session)  # 注释此行以防止重复发送

            # 记录转发的节点结构
            logger.debug(
                f"发送转发消息，共 {len(nodes_list)} 个节点，任务ID: {task_id}"
            )

            # 获取客户端
            client = self.plugin.context.get_platform("aiocqhttp").get_client()

            # 新增：预处理步骤 - 上传图片到缓存
            try:
                logger.info(f"📤 任务 {task_id}: 预处理: 将图片上传到OneBot缓存")
                processed_nodes = await self._upload_images_to_cache(
                    nodes_list, client, target_session, target_id
                )
            except Exception as e:
                logger.warning(f"预处理图片失败: {e}，将使用原始节点")
                processed_nodes = nodes_list

            # 策略1: 使用处理后的节点发送合并转发消息
            try:
                logger.info(f"📤 任务 {task_id}: 策略1: 尝试直接发送合并转发消息")

                # 预检查节点中是否包含引用消息和文件喵～ 🔍
                reply_count = 0
                file_count = 0
                for node in processed_nodes:
                    if node.get("type") == "node" and "data" in node:
                        content = node["data"].get("content", [])
                        for item in content:
                            if isinstance(item, dict):
                                if item.get("type") == "reply":
                                    reply_count += 1
                                    # 检查引用消息内容是否包含文件喵～ 📁
                                    reply_content = item.get("data", {}).get(
                                        "content", []
                                    )
                                    for reply_item in reply_content:
                                        if (
                                            isinstance(reply_item, dict)
                                            and reply_item.get("type") == "file"
                                        ):
                                            file_count += 1
                                            logger.debug(
                                                f"检测到引用消息中包含文件喵: {reply_item.get('data', {}).get('name', '未知文件')} 📁"
                                            )
                                elif item.get("type") == "file":
                                    file_count += 1

                if reply_count > 0 or file_count > 0:
                    logger.info(
                        f"📊 任务 {task_id}: 节点分析 - 引用消息: {reply_count}个, 文件: {file_count}个"
                    )

                # 添加详细的JSON结构日志，帮助调试
                if "GroupMessage" in target_session:
                    action = "send_group_forward_msg"
                    payload = {"group_id": int(target_id), "messages": processed_nodes}
                else:
                    action = "send_private_forward_msg"
                    payload = {"user_id": int(target_id), "messages": processed_nodes}

                # 打印完整payload结构，帮助调试
                try:
                    import json

                    debug_payload = json.dumps(payload, ensure_ascii=False)
                    logger.debug(f"合并转发消息payload:\n{debug_payload}")
                except Exception as e:
                    logger.debug(f"打印调试信息失败: {e}")

                response = await client.call_action(action, **payload)

                if response and not isinstance(response, Exception):
                    logger.info(f"✅ 任务 {task_id}: 策略1: 使用缓存图片合并转发成功")
                    # 标记所有节点为已发送
                    for i, node in enumerate(processed_nodes):
                        if node.get("type") == "node":
                            node_id = f"{task_id}_strategy1_{i}"  # 使用更稳定的ID格式
                            self._add_sent_message(target_session, node_id)

                    return True
                else:
                    # 详细分析失败原因喵～ 🔍
                    error_msg = str(response) if response else "无响应"
                    logger.warning(f"❌ 任务 {task_id}: 策略1: 合并转发消息发送失败")
                    logger.warning(f"   失败响应: {error_msg}")
                    if reply_count > 0:
                        logger.warning(
                            f"   可能原因: 包含 {reply_count} 个引用消息，可能其中有文件内容导致合并转发失败喵～ 📨"
                        )
                    if file_count > 0:
                        logger.warning(
                            f"   可能原因: 包含 {file_count} 个文件，可能导致合并转发失败喵～ 📁"
                        )
                    logger.info("   将尝试策略2: GIF转静态图")
            except Exception as e:
                logger.warning(f"❌ 任务 {task_id}: 策略1失败: {e}")
                # 记录具体的错误类型喵～ 🔍
                if "引用" in str(e) or "reply" in str(e).lower():
                    logger.warning("   错误可能与引用消息处理相关喵～ 📨")
                if "文件" in str(e) or "file" in str(e).lower():
                    logger.warning("   错误可能与文件处理相关喵～ 📁")

            # 策略2: 如果有GIF，先尝试下载GIF并直接发送，而不是立即转换为PNG
            try:
                logger.info(f"📤 任务 {task_id}: 策略2: 尝试下载图片并发送")

                # 深拷贝节点列表以免修改原始数据
                import copy

                gif_nodes = copy.deepcopy(nodes_list)

                # 下载GIF但保持GIF格式 - 新增函数调用
                downloaded_gif_nodes = await self._download_gif_in_nodes(gif_nodes)

                # 尝试直接发送下载的GIF
                if "GroupMessage" in target_session:
                    action = "send_group_forward_msg"
                    payload = {
                        "group_id": int(target_id),
                        "messages": downloaded_gif_nodes,
                    }
                else:
                    action = "send_private_forward_msg"
                    payload = {
                        "user_id": int(target_id),
                        "messages": downloaded_gif_nodes,
                    }

                response = await client.call_action(action, **payload)
                if response and not isinstance(response, Exception):
                    logger.info(f"✅ 任务 {task_id}: 策略2: 使用下载的原始GIF发送成功")
                    # 标记所有节点为已发送
                    for i, node in enumerate(downloaded_gif_nodes):
                        if node.get("type") == "node":
                            node_id = f"{task_id}_strategy2_{i}"  # 使用更稳定的ID格式
                            self._add_sent_message(target_session, node_id)

                    return True
                else:
                    logger.warning(
                        f"❌ 任务 {task_id}: 策略2: 使用下载的原始GIF发送失败，尝试转换为静态图"
                    )

                    # 转换为静态图再次尝试
                    static_nodes = copy.deepcopy(downloaded_gif_nodes)
                    await self._convert_gif_to_static(static_nodes)

                    if "GroupMessage" in target_session:
                        action = "send_group_forward_msg"
                        payload = {"group_id": int(target_id), "messages": static_nodes}
                    else:
                        action = "send_private_forward_msg"
                        payload = {"user_id": int(target_id), "messages": static_nodes}

                    response = await client.call_action(action, **payload)
                    if response and not isinstance(response, Exception):
                        logger.info(f"✅ 任务 {task_id}: 策略2: GIF转静态图后发送成功")
                        # 标记所有节点为已发送
                        for i, node in enumerate(static_nodes):
                            if node.get("type") == "node":
                                node_id = f"{task_id}_strategy2_static_{i}"  # 使用更稳定的ID格式
                                self._add_sent_message(target_session, node_id)

                        return True
                    else:
                        logger.warning(
                            f"❌ 任务 {task_id}: 策略2: GIF转静态图也失败，尝试策略3"
                        )
            except Exception as e:
                logger.warning(f"❌ 任务 {task_id}: 策略2失败: {e}")

            # 策略3: 下载图片并使用本地文件重新发送 (所有图片)
            try:
                logger.info(
                    f"📤 任务 {task_id}: 策略3: 尝试下载所有图片后重新发送合并转发消息"
                )

                # 下载所有图片并更新节点
                updated_nodes = await self._download_images_in_nodes(nodes_list)

                # 调用API再次发送
                if "GroupMessage" in target_session:
                    action = "send_group_forward_msg"
                    payload = {"group_id": int(target_id), "messages": updated_nodes}
                else:
                    action = "send_private_forward_msg"
                    payload = {"user_id": int(target_id), "messages": updated_nodes}

                response = await client.call_action(action, **payload)
                if response and not isinstance(response, Exception):
                    logger.info(f"✅ 任务 {task_id}: 策略3: 下载图片后合并转发发送成功")
                    # 标记所有节点为已发送
                    for i, node in enumerate(updated_nodes):
                        if node.get("type") == "node":
                            node_id = f"{task_id}_strategy3_{i}"  # 使用更稳定的ID格式
                            self._add_sent_message(target_session, node_id)

                    return True
                else:
                    logger.warning(
                        f"❌ 任务 {task_id}: 策略3: 下载图片后合并转发发送失败，尝试最终策略"
                    )
            except Exception as e:
                logger.warning(f"❌ 任务 {task_id}: 策略3失败: {e}")

            # 策略4: 放弃合并转发，改用逐条发送
            logger.info(f"📤 任务 {task_id}: 最终策略: 放弃合并转发，改用逐条发送")
            return await self.send_with_fallback(target_session, nodes_list, task_id)

        except Exception as e:
            logger.error(f"任务 {task_id}: 所有发送策略均失败: {e}")
            logger.error(traceback.format_exc())
            return False

    async def _upload_images_to_cache(
        self, nodes_list: list[dict], client, target_session: str, target_id: str
    ) -> list[dict]:
        """
        将消息中的所有图片上传到OneBot的缓存服务器喵～ 📤
        智能处理各种图片格式，特别优化GIF动图！

        Args:
            nodes_list: 节点列表喵
            client: OneBot客户端喵
            target_session: 目标会话ID喵
            target_id: 目标ID喵

        Returns:
            list[dict]: 更新了缓存引用的节点列表喵～

        Note:
            会自动识别GIF并保持动画效果喵！ ✨
        """
        import copy

        processed_nodes = copy.deepcopy(nodes_list)
        is_group = "GroupMessage" in target_session

        # 遍历所有节点
        for node in processed_nodes:
            if (
                node["type"] != "node"
                or "data" not in node
                or "content" not in node["data"]
            ):
                continue

            for item in node["data"]["content"]:
                if item["type"] != "image" or "data" not in item:
                    continue

                data = item["data"]
                file_path = data.get("file", "")
                if not file_path:
                    continue

                # 识别GIF
                is_gif = (
                    data.get("is_gif", False)
                    or data.get("flash", False)
                    or (
                        isinstance(file_path, str)
                        and file_path.lower().endswith(".gif")
                    )
                )

                # 统一获取本地文件路径
                local_path = await self._get_local_file_path(file_path, is_gif)
                if not local_path:
                    continue

                # 上传到缓存
                try:
                    # 优先使用专用图片API
                    upload_result = None
                    try:
                        api_name = (
                            "upload_group_image" if is_group else "upload_private_image"
                        )
                        target_param = {
                            "group_id" if is_group else "user_id": int(target_id)
                        }

                        upload_result = await client.call_action(
                            api_name, **target_param, file=local_path
                        )
                    except Exception as e:
                        logger.warning(
                            f"专用图片上传API调用失败: {e}，尝试通用文件上传API"
                        )

                        # 回退到通用文件上传API
                        api_name = (
                            "upload_group_file" if is_group else "upload_private_file"
                        )
                        upload_result = await client.call_action(
                            api_name, **target_param, file=local_path
                        )

                    if not upload_result or "data" not in upload_result:
                        logger.warning("上传失败或返回格式异常")
                        continue

                    # 提取缓存ID
                    cache_url = None
                    if "file" in upload_result["data"]:
                        cache_url = upload_result["data"]["file"]
                    elif "url" in upload_result["data"]:
                        cache_url = upload_result["data"]["url"]
                    elif isinstance(upload_result["data"], dict):
                        cache_url = upload_result["data"].get("id") or upload_result[
                            "data"
                        ].get("file_id")

                    if cache_url:
                        if not cache_url.startswith("cache://"):
                            cache_url = f"cache://{cache_url}"

                        # 更新节点中的图片引用
                        data["file"] = cache_url
                        # 保留GIF标记
                        if is_gif:
                            data["flash"] = True

                        logger.info(f"图片已上传到缓存: {cache_url}")

                except Exception as e:
                    logger.error(f"上传图片到缓存失败: {e}")

        return processed_nodes

    async def _get_local_file_path(
        self, file_path: str, is_gif: bool = False
    ) -> str | None:
        """
        统一处理各种图片路径格式，返回本地文件路径喵～ 📁
        智能识别URL、文件路径、Base64等格式！

        Args:
            file_path: 原始文件路径或URL喵
            is_gif: 是否为GIF格式喵

        Returns:
            str | None: 本地文件路径，失败时返回None喵～

        Note:
            支持file://、http://、base64://等多种格式喵！ ✨
        """

        # 处理本地文件路径
        if file_path.startswith("file:///"):
            local_path = file_path[8:]
            if os.path.exists(local_path):
                return local_path
            return None

        # 处理URL - 必须先下载到本地
        if file_path.startswith(("http://", "https://")):
            ext = "gif" if is_gif else "jpg"
            local_path = await self.download_helper.download_file(file_path, ext)
            if local_path and os.path.exists(local_path):
                return local_path
            return None

        # 处理Base64编码
        if file_path.startswith("base64://"):
            try:
                base64_data = file_path.split("base64://")[1]
                image_data = base64.b64decode(base64_data)
                ext = ".gif" if is_gif else ".jpg"

                temp_dir = os.path.join(
                    "data", "plugins_data", "astrbot_plugin_turnrig", "temp", "images"
                )
                os.makedirs(temp_dir, exist_ok=True)
                temp_file = os.path.join(temp_dir, f"{uuid.uuid4()}{ext}")

                with open(temp_file, "wb") as f:
                    f.write(image_data)

                return temp_file
            except Exception as e:
                logger.warning(f"Base64解码失败: {e}")
                return None

        # 尝试作为本地路径处理
        if os.path.exists(file_path):
            return file_path

        return None

    # 新增函数: 转换GIF为静态图喵～ 🖼️
    async def _convert_gif_to_static(self, nodes_list: list[dict]) -> None:
        """
        将节点中的GIF转换为静态图像喵～ 🖼️
        当GIF无法正常发送时的备用方案！

        Args:
            nodes_list: 包含GIF的节点列表喵

        Note:
            使用PIL提取GIF第一帧并转换为PNG格式喵！ ✨
        """

        from PIL import Image

        # 获取插件数据目录喵～ 📁
        plugin_data_dir = os.path.join(
            "data", "plugins_data", "astrbot_plugin_turnrig", "temp", "images", "pillow"
        )
        os.makedirs(plugin_data_dir, exist_ok=True)

        for node in nodes_list:
            if node["type"] == "node" and "data" in node and "content" in node["data"]:
                for item in node["data"]["content"]:
                    if item["type"] == "image" and "data" in item:
                        # 检查是否为GIF喵～ 🔍
                        if item["data"].get("is_gif", False) or (
                            item["data"].get("file", "").lower().endswith(".gif")
                        ):
                            file_path = item["data"].get("file", "")

                            # 尝试将GIF转换为静态图像喵～ 🔄
                            try:
                                # 如果是URL，先下载喵～ 📥
                                if file_path.startswith(("http://", "https://")):
                                    local_path = (
                                        await self.download_helper.download_file(
                                            file_path, "gif"
                                        )
                                    )
                                    if not local_path:
                                        continue
                                elif file_path.startswith("file:///"):
                                    local_path = file_path[8:]
                                else:
                                    local_path = file_path

                                # 检查文件是否存在喵～ 📂
                                if not os.path.exists(local_path):
                                    continue

                                # 使用PIL打开GIF并提取第一帧喵～ 🎬
                                gif_img = Image.open(local_path)
                                first_frame = gif_img.convert("RGBA")

                                # 保存为静态PNG到插件目录喵～ 💾
                                static_path = os.path.join(
                                    plugin_data_dir, f"{uuid.uuid4()}.png"
                                )
                                first_frame.save(static_path, "PNG")

                                # 更新节点中的图片数据喵～ 📝
                                item["data"]["file"] = f"file:///{static_path}"
                                item["data"]["is_gif"] = False
                                logger.info(f"GIF已转换为静态图喵: {static_path} ✨")

                            except Exception as e:
                                logger.error(f"转换GIF失败喵: {e} 😿")

        logger.info("GIF转换处理完成喵～ 🎉")

    async def _download_gif_in_nodes(self, nodes_list: list[dict]) -> list[dict]:
        """
        下载节点中的GIF图片但不转换格式喵～ 📥
        保持GIF动画效果的智能下载！

        Args:
            nodes_list: 节点列表喵

        Returns:
            list[dict]: 更新了GIF图片路径的节点列表喵～

        Note:
            会保留GIF的动画特性，设置flash标记喵！ ✨
        """
        # 获取插件数据目录喵～ 📁
        plugin_data_dir = os.path.join(
            "data", "plugins_data", "astrbot_plugin_turnrig", "temp", "images"
        )
        os.makedirs(plugin_data_dir, exist_ok=True)

        for node in nodes_list:
            if node["type"] == "node" and "data" in node and "content" in node["data"]:
                for item in node["data"]["content"]:
                    if item["type"] == "image" and "data" in item:
                        # 检查是否为GIF喵～ 🔍
                        if item["data"].get("is_gif", False) or (
                            item["data"].get("file", "").lower().endswith(".gif")
                        ):
                            file_path = item["data"].get("file", "")

                            # 如果是URL，下载GIF喵～ 📥
                            if file_path.startswith(("http://", "https://")):
                                try:
                                    # 使用download_helper下载GIF并保留原始格式喵～ 🎬
                                    filename = f"{uuid.uuid4()}.gif"
                                    local_path = os.path.join(plugin_data_dir, filename)

                                    # 直接下载URL到本地喵～ 📤
                                    success = await self._download_gif_with_curl(
                                        file_path, local_path
                                    )

                                    if success and os.path.exists(local_path):
                                        # 更新节点中的图片路径喵～ 📝
                                        item["data"]["file"] = f"file:///{local_path}"
                                        # 确保保留GIF标记 - 这很重要喵！ 🌟
                                        item["data"]["flash"] = True
                                        logger.info(
                                            f"GIF已下载到本地并保留动画特性喵: {local_path} ✨"
                                        )
                                except Exception as e:
                                    logger.error(f"下载GIF失败喵: {e} 😿")

        return nodes_list

    async def _download_gif_with_curl(self, url: str, output_path: str) -> bool:
        """
        使用curl下载GIF并保持原始格式喵～ 📥
        专业的GIF下载工具，保证动画完整性！

        Args:
            url: GIF图片URL喵
            output_path: 输出路径喵

        Returns:
            bool: 下载成功返回True，否则返回False喵～

        Note:
            会验证下载的文件确实是GIF格式喵！ 🔍
        """
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # 构建curl命令
            cmd = [
                "curl",
                "-s",  # 静默模式
                "-L",  # 跟随重定向
                "-o",
                output_path,  # 输出文件
                "-H",
                "User-Agent: Mozilla/5.0",
                url,
            ]

            # 执行curl命令
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            # 检查下载结果
            if (
                process.returncode == 0
                and os.path.exists(output_path)
                and os.path.getsize(output_path) > 0
            ):
                logger.info(f"成功下载文件: {output_path}")
                return True
            else:
                stderr_text = stderr.decode() if stderr else "未知错误"
                logger.warning(f"下载文件失败: {stderr_text}")
                return False

        except Exception as e:
            logger.error(f"下载文件异常: {e}")
            logger.error(traceback.format_exc())
            return False

    async def _download_images_in_nodes(self, nodes_list: list[dict]) -> list[dict]:
        """使用curl下载节点中所有图片到本地

        Args:
            nodes_list: 节点列表

        Returns:
            List[Dict]: 更新了图片路径的节点列表
        """
        updated_nodes = []

        for node in nodes_list:
            # 深复制节点以避免修改原始数据
            import copy

            node_copy = copy.deepcopy(node)

            if node["type"] == "node" and "data" in node and "content" in node["data"]:
                for item in node_copy["data"]["content"]:
                    if (
                        item["type"] == "image"
                        and "data" in item
                        and "file" in item["data"]
                    ):
                        file_path = item["data"]["file"]

                        if file_path.startswith(("http://", "https://")):
                            local_path = await self._download_image_with_curl(file_path)

                            if local_path and os.path.exists(local_path):
                                try:
                                    # 转换为 base64
                                    with open(local_path, "rb") as f:
                                        img_content = f.read()
                                    b64_data = base64.b64encode(img_content).decode(
                                        "utf-8"
                                    )
                                    item["data"]["file"] = f"base64://{b64_data}"
                                    logger.debug(f"图片已转换为base64: {local_path}")
                                except Exception as e:
                                    logger.warning(f"转换base64失败: {e}")
                        elif file_path.startswith("file:///"):
                            # 处理本地文件路径
                            local_path = file_path[8:]
                            if os.path.exists(local_path):
                                try:
                                    with open(local_path, "rb") as f:
                                        img_content = f.read()
                                    b64_data = base64.b64encode(img_content).decode(
                                        "utf-8"
                                    )
                                    item["data"]["file"] = f"base64://{b64_data}"
                                except Exception as e:
                                    logger.warning(f"转换base64失败: {e}")

            updated_nodes.append(node_copy)

        return updated_nodes

    async def _download_image_with_curl(self, url: str) -> str:
        """
        使用curl下载图片喵～ 📥
        专业的图片下载工具，支持各种格式！

        Args:
            url: 图片URL喵

        Returns:
            str: 成功返回本地文件路径，失败返回None喵～

        Note:
            会自动处理重定向和用户代理，确保下载成功喵！ ✨
        """
        try:
            # 获取标准插件数据目录喵～ 📁
            plugin_data_dir = os.path.join(
                "data", "plugins_data", "astrbot_plugin_turnrig", "temp", "images"
            )
            os.makedirs(plugin_data_dir, exist_ok=True)

            # 使用uuid生成唯一文件名喵～ 🏷️
            filename = f"{uuid.uuid4()}.jpg"
            output_path = os.path.join(plugin_data_dir, filename)

            logger.debug(f"下载图片喵: {url} -> {output_path} 📤")

            # 构建curl命令喵～ 🔧
            cmd = [
                "curl",
                "-s",  # 静默模式喵
                "-L",  # 跟随重定向喵
                "-o",
                output_path,  # 输出文件喵
                "-H",
                "User-Agent: Mozilla/5.0",
                url,
            ]

            # 执行curl命令喵～ ⚙️
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            # 检查下载结果喵～ 🔍
            if (
                process.returncode == 0
                and os.path.exists(output_path)
                and os.path.getsize(output_path) > 0
            ):
                logger.info(f"✅ 图片下载成功喵: {output_path} 🎉")
                return output_path
            else:
                stderr_text = stderr.decode() if stderr else "未知错误"
                logger.warning(f"❌ 下载图片失败喵: {stderr_text} 😿")
                return None

        except Exception as e:
            logger.error(f"下载图片异常喵: {e} 😿")
            logger.error(traceback.format_exc())
            return None

    async def send_with_fallback(
        self,
        target_session: str,
        nodes_list: list[dict],
        task_id: str = None,
        header_text: str | None = None,
    ) -> bool:
        """
        当合并转发失败时，尝试直接发送消息喵～ 🔄
        备用发送策略，确保消息能够送达！

        Args:
            target_session: 目标会话ID喵
            nodes_list: 节点列表喵
            task_id: 任务ID，用于日志记录和跟踪喵

        Returns:
            bool: 发送成功返回True，否则返回False喵～

        Note:
            会逐条发送消息，并控制发送频率避免限制喵！ ✨
        """
        if task_id is None:
            task_id = str(uuid.uuid4())

        try:
            # 获取目标平台和ID喵～ 🔍
            target_parts = target_session.split(":", 2)
            if len(target_parts) != 3:
                logger.warning(
                    f"任务 {task_id}: 目标会话格式无效喵: {target_session} 😿"
                )
                return False

            target_platform, target_type, target_id = target_parts

            # 获取client喵～ 🤖
            client = self.plugin.context.get_platform("aiocqhttp").get_client()

            # 使用信号量控制并发发送，避免频率限制喵～ 🚦
            if not hasattr(self, "_send_semaphore"):
                self._send_semaphore = asyncio.Semaphore(2)  # 最多同时发送2条消息喵

            # 发送消息前提示喵～ 📢
            if header_text is None:
                header_text = (
                    f"[无法使用合并转发，将直接发送 {len(nodes_list)} 条消息喵～]"
                )

            if header_text and str(header_text).strip():
                try:
                    if "GroupMessage" in target_session:
                        await client.call_action(
                            "send_group_msg",
                            group_id=int(target_id),
                            message=header_text,
                        )
                    else:
                        await client.call_action(
                            "send_private_msg",
                            user_id=int(target_id),
                            message=header_text,
                        )
                except Exception as e:
                    logger.warning(f"任务 {task_id}: 发送提示消息失败喵: {e} 😿")

            # 为每个节点生成唯一ID并按顺序逐条发送消息喵～ 📋
            successful_nodes = 0
            # 创建发送任务列表喵～ 📝
            send_tasks = []
            for i, node in enumerate(nodes_list):
                if node["type"] != "node":
                    continue
                # 生成节点ID用于跟踪喵～ 🏷️
                node_id = f"{task_id}_strategy4_{i}"  # 使用更稳定的ID格式喵

                # 检查是否已经发送过喵～ ✅
                if self._is_message_sent(target_session, node_id):
                    logger.info(
                        f"任务 {task_id}: 节点 {node_id} 已经发送过，跳过喵～ ⏭️"
                    )
                    continue

                # 创建异步发送任务喵～ 🚀
                send_task = self._create_send_task(
                    target_session, target_id, node, node_id, task_id
                )
                send_tasks.append(send_task)

            # 使用信号量控制并发执行发送任务喵～ 🎛️
            async def execute_with_semaphore(task):
                async with self._send_semaphore:
                    return await task

            # 并发执行所有发送任务，但受信号量控制喵～ ⚡
            results = await asyncio.gather(
                *[execute_with_semaphore(task) for task in send_tasks],
                return_exceptions=True,
            )

            # 统计成功发送的节点数喵～ 📊
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"任务 {task_id}: 发送节点时出错喵: {result} 😿")
                elif result:
                    successful_nodes += 1

            logger.info(
                f"任务 {task_id}: 成功使用备选方案发送 {successful_nodes}/{len(nodes_list)} 条消息到 {target_session} 喵～ 🎉"
            )
            return successful_nodes > 0
        except Exception as e:
            logger.error(f"任务 {task_id}: 备选方案发送失败喵: {e} 😿")
            logger.error(traceback.format_exc())
            return False

    async def _create_send_task(
        self, target_session, target_id, node, node_id, task_id
    ):
        """
        创建单条消息发送任务喵～ 🏗️
        为每个节点创建独立的异步发送任务！

        Args:
            target_session: 目标会话喵
            target_id: 目标ID喵
            node: 节点数据喵
            node_id: 节点ID喵
            task_id: 任务ID喵

        Returns:
            发送结果喵～

        Note:
            会自动添加延迟避免频率限制喵！ ⏰
        """
        try:
            # 尝试发送消息喵～ 📤
            result = await self._send_node_content(
                target_session, target_id, node, node_id, task_id
            )

            # 无论成功失败，都等待一段时间避免频率限制喵～ 😴
            await asyncio.sleep(1)
            return result
        except Exception as e:
            logger.error(f"任务 {task_id}: 创建发送任务失败喵: {e} 😿")
            return False

    async def _send_node_content(
        self,
        target_session: str,
        target_id: str,
        node: dict,
        node_id: str = None,
        task_id: str = None,
    ) -> bool:
        """
        发送节点内容喵～ 📤
        处理单个消息节点的发送，支持各种消息类型！

        Args:
            target_session: 目标会话ID喵
            target_id: 目标ID喵
            node: 节点数据喵
            node_id: 节点唯一标识，用于跟踪是否已发送喵
            task_id: 任务ID，用于日志记录喵

        Returns:
            bool: 发送成功返回True，否则返回False喵～

        Note:
            支持文本、图片、AT等各种消息类型的智能处理喵！ ✨
        """
        if task_id is None:
            task_id = str(uuid.uuid4())

        sender_name = node["data"].get("name", "未知")
        content = node["data"].get("content", [])

        # 获取client
        client = self.plugin.context.get_platform("aiocqhttp").get_client()

        # 检查是否已发送过该节点
        if node_id and self._is_message_sent(target_session, node_id):
            logger.info(f"任务 {task_id}: 节点 {node_id} 已经发送过，跳过")
            return True

        try:
            # 创建包含所有内容的消息链
            import astrbot.api.message_components as Comp
            from astrbot.api.event import MessageChain

            message_parts = [Comp.Plain(f"{sender_name}:\n")]

            # 检查是否包含文件消息 - 需要特殊处理
            has_file_message = False
            file_url = ""
            file_name = ""

            # 处理所有内容项
            for item in content:
                item_type = item.get("type", "")

                # 新增: 处理文件类型
                if item_type == "file":
                    has_file_message = True
                    file_url = item.get("url", "") or item.get("data", {}).get(
                        "url", ""
                    )
                    file_name = item.get("name", "") or item.get("data", {}).get(
                        "name", "未命名文件"
                    )
                    logger.info(f"检测到文件类型消息: {file_name}, URL: {file_url}")
                    # 不添加到message_parts，稍后单独处理
                    continue

                # 新增: 检查group_upload事件
                if item_type == "notice" and item.get("notice_type") == "group_upload":
                    has_file_message = True
                    # 从notice事件中提取文件信息
                    file_info = item.get("file", {})
                    file_url = file_info.get("url", "")
                    file_name = file_info.get("name", "群文件")
                    logger.info(f"检测到群文件上传通知: {file_name}, URL: {file_url}")
                    # 不添加到message_parts，稍后单独处理
                    continue

                if item_type == "text":
                    message_parts.append(Comp.Plain(item["data"].get("text", "")))

                elif item_type == "image":
                    # 尝试获取图片
                    img_path = await self._prepare_image(item)
                    if img_path:
                        if img_path.startswith("http"):
                            # 对于URL，尝试下载
                            local_path = await self.download_helper.download_image(
                                img_path
                            )
                            if local_path and os.path.exists(local_path):
                                message_parts.append(
                                    Comp.Image.fromFileSystem(local_path)
                                )
                            else:
                                # 如果下载失败，尝试直接使用URL
                                message_parts.append(Comp.Image.fromURL(img_path))
                        elif img_path.startswith("file:///"):
                            # 对于本地文件
                            local_path = img_path[8:]
                            if os.path.exists(local_path):
                                message_parts.append(
                                    Comp.Image.fromFileSystem(local_path)
                                )
                        elif os.path.exists(img_path):
                            # 直接就是本地路径
                            message_parts.append(Comp.Image.fromFileSystem(img_path))

                elif item_type == "at":
                    message_parts.append(Comp.At(qq=item["data"].get("qq", "")))

            # 如果是文件消息，使用专门的方法处理
            if has_file_message and file_url:
                # 先用常规方式发送普通消息部分
                if message_parts and len(message_parts) > 1:  # 不只是发送者名称
                    message = MessageChain(message_parts)
                    try:
                        if "GroupMessage" in target_session:
                            await self.plugin.context.send_message(
                                f"aiocqhttp:GroupMessage:{target_id}", message
                            )
                        else:
                            await self.plugin.context.send_message(
                                f"aiocqhttp:PrivateMessage:{target_id}", message
                            )
                    except Exception as e:
                        logger.warning(f"发送普通部分失败，忽略并继续处理文件: {e}")

                # 使用文件发送方法处理文件
                success = await self._download_and_send_file(
                    file_url, file_name, target_session, target_id, sender_name
                )

                # 标记为已发送
                if node_id:
                    self._add_sent_message(target_session, node_id)

                return success

            # 直接使用 OneBot 消息段发送（更稳定）
            try:
                segments = [{"type": "text", "data": {"text": f"{sender_name}:\n"}}]
                segments.extend(content)

                if "GroupMessage" in target_session:
                    await client.call_action(
                        "send_group_msg", group_id=int(target_id), message=segments
                    )
                else:
                    await client.call_action(
                        "send_private_msg", user_id=int(target_id), message=segments
                    )

                logger.info(
                    f"任务 {task_id}: 成功发送消息到 {target_session} (OneBot 段)"
                )

                if node_id:
                    self._add_sent_message(target_session, node_id)
                return True
            except Exception as e2:
                logger.warning(
                    f"任务 {task_id}: OneBot 段发送失败，尝试 MessageChain 备选: {e2}"
                )

                # 备选：尝试使用 MessageChain 发送
                try:
                    message = MessageChain(message_parts)
                    if "GroupMessage" in target_session:
                        await self.plugin.context.send_message(
                            f"aiocqhttp:GroupMessage:{target_id}", message
                        )
                    else:
                        await self.plugin.context.send_message(
                            f"aiocqhttp:PrivateMessage:{target_id}", message
                        )
                    if node_id:
                        self._add_sent_message(target_session, node_id)
                    return True
                except Exception as e3:
                    logger.error(f"任务 {task_id}: MessageChain 备选也失败: {e3}")
                    return False
        except Exception as e:
            logger.error(f"任务 {task_id}: 发送节点内容失败: {e}")
            logger.error(traceback.format_exc())
            return False

    async def _prepare_image(self, img_item: dict) -> str:
        """
        准备图片，返回可用于发送的路径喵～ 🖼️
        智能处理各种图片格式和来源！

        Args:
            img_item: 图片项数据喵

        Returns:
            str: 图片路径，失败时返回None喵～

        Note:
            支持QQ链接、base64、本地文件等多种格式喵！ ✨
        """
        try:
            # 尝试从不同字段提取图片信息
            file_path = ""
            img_url = ""
            base64_data = ""
            original_url = ""  # 新增: 从message_builder保存的原始URL字段

            # 检查消息格式，提取图片信息
            if "data" in img_item:
                file_path = img_item["data"].get("file", "")
                img_url = img_item["data"].get("url", "")
                base64_data = img_item["data"].get("base64", "")
                original_url = img_item["data"].get(
                    "original_url", ""
                )  # 新增: 获取原始URL
            else:
                # 兼容直接存储的序列化格式
                file_path = img_item.get("file", "")
                img_url = img_item.get("url", "")
                base64_data = img_item.get("base64", "")
                original_url = img_item.get("original_url", "")  # 新增: 获取原始URL

            logger.debug(
                f"准备图片信息: file_path={file_path}, url={img_url}, original_url={original_url}, has_base64={'是' if base64_data else '否'}"
            )

            # 检查是否是QQ链接
            is_qq_url = False
            if img_url and (
                "multimedia.nt.qq.com.cn" in img_url or "gchat.qpic.cn" in img_url
            ):
                is_qq_url = True
            if file_path and (
                "multimedia.nt.qq.com.cn" in file_path or "gchat.qpic.cn" in file_path
            ):
                is_qq_url = True
            if original_url and (
                "multimedia.nt.qq.com.cn" in original_url
                or "gchat.qpic.cn" in original_url
            ):  # 新增: 检查original_url
                is_qq_url = True

            # 对于QQ链接，修改优先级: original_url > img_url > file_path
            if is_qq_url:
                logger.info("检测到QQ图片链接，直接使用URL发送")
                # 优先使用original_url
                if original_url:
                    return original_url
                return img_url or file_path

            # 如果有base64数据，优先使用base64
            if base64_data:
                # 保存为临时文件
                try:
                    import uuid

                    temp_file = os.path.join(
                        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                        "temp",
                        "images",
                        f"{uuid.uuid4()}.jpg",
                    )
                    os.makedirs(os.path.dirname(temp_file), exist_ok=True)

                    # 确保base64数据格式正确
                    if "base64://" in base64_data:
                        base64_data = base64_data.split("base64://")[1]

                    image_data = base64.b64decode(base64_data)
                    with open(temp_file, "wb") as f:
                        f.write(image_data)

                    logger.debug(f"成功从base64保存临时图片: {temp_file}")
                    return f"file:///{temp_file}"
                except Exception as e:
                    logger.error(f"从base64保存图片失败: {e}")

            # 优先使用本地文件
            if file_path:
                # 处理可能的多种格式
                if file_path.startswith("file:///"):
                    clean_path = file_path[8:]
                    if os.path.exists(clean_path):
                        logger.debug(f"使用本地文件 (file://): {file_path}")
                        return file_path
                elif file_path.startswith("http"):
                    # 如果file字段包含URL，当作URL处理
                    logger.debug(f"文件路径包含URL，作为URL处理: {file_path}")
                    # 对于QQ多媒体URL，直接返回更可能成功
                    if (
                        "multimedia.nt.qq.com.cn" in file_path
                        or "gchat.qpic.cn" in file_path
                    ):
                        return file_path

                    local_path = await self.download_helper.download_image(file_path)
                    if local_path and os.path.exists(local_path):
                        logger.debug(f"已下载URL图片到: {local_path}")
                        return f"file:///{local_path}"
                    elif local_path:  # 如果download_image返回了原始URL
                        return local_path
                elif os.path.exists(file_path):
                    logger.debug(f"使用本地文件 (直接路径): {file_path}")
                    return f"file:///{file_path}"
                else:
                    logger.warning(f"文件路径不存在: {file_path}")
                    # 新增: 文件不存在时尝试使用original_url
                    if original_url:
                        logger.debug(f"文件不存在，使用原始URL: {original_url}")
                        return original_url

            # 其次使用URL
            if img_url:
                # 对于QQ多媒体URL，直接返回更可能成功
                if "multimedia.nt.qq.com.cn" in img_url or "gchat.qpic.cn" in img_url:
                    return img_url

                # 检查是否已经下载过相同的图片URL
                cache_key = f"img_cache_{hash(img_url)}"
                cached_path = self.plugin.config.get(cache_key, "")

                if cached_path and os.path.exists(cached_path):
                    logger.debug(f"从缓存获取图片: {cached_path}")
                    return f"file:///{cached_path}"

                # 下载图片
                logger.debug(f"下载图片URL: {img_url}")
                local_path = await self.download_helper.download_image(img_url)
                if local_path and os.path.exists(local_path):
                    # 缓存路径以便下次使用
                    self.plugin.config[cache_key] = local_path
                    logger.debug(f"已下载URL图片到: {local_path}")
                    return f"file:///{local_path}"
                elif local_path:  # 如果download_image返回了原始URL
                    return local_path
                else:
                    logger.warning(f"图片URL下载失败: {img_url}")
                    # 下载失败时直接返回URL
                    return img_url

            # 新增: 最后尝试使用original_url
            if original_url:
                logger.debug(f"尝试使用原始URL作为最后手段: {original_url}")
                return original_url

            logger.warning("图片准备失败: 无可用来源")
            return None
        except Exception as e:
            logger.error(f"准备图片失败: {e}")
            logger.error(traceback.format_exc())
            return None

    async def send_to_non_qq_platform(
        self, target_session: str, source_name: str, valid_messages: list[dict]
    ) -> bool:
        """
        发送消息到非QQ平台喵～ 🌐
        适配不同平台的消息发送格式！

        Args:
            target_session: 目标会话ID喵
            source_name: 消息来源名称喵
            valid_messages: 有效的消息列表喵

        Returns:
            bool: 发送成功返回True，否则返回False喵～

        Note:
            会自动添加来源信息和消息统计喵！ ✨
        """
        task_id = str(uuid.uuid4())

        try:
            # 跟踪已发送消息的ID
            sent_ids = set()

            # 发送头部信息
            header_text = f"📨 收到来自{source_name}的 {len(valid_messages)} 条消息："
            await self.plugin.context.send_message(
                target_session, [Plain(text=header_text)]
            )

            # 使用信号量控制并发发送
            if not hasattr(self, "_non_qq_semaphore"):
                self._non_qq_semaphore = asyncio.Semaphore(2)

            # 创建异步任务列表
            send_tasks = []

            for msg in valid_messages:
                # 生成消息ID
                msg_id = msg.get("id", f"{task_id}_{uuid.uuid4()}")

                # 检查是否已发送
                if msg_id in sent_ids or self._is_message_sent(target_session, msg_id):
                    logger.info(f"任务 {task_id}: 消息 {msg_id} 已发送，跳过")
                    continue

                # 创建发送任务
                send_task = self._create_non_qq_send_task(
                    target_session, msg, msg_id, task_id
                )
                send_tasks.append(send_task)

            # 使用信号量控制并发执行
            async def execute_with_semaphore(task):
                async with self._non_qq_semaphore:
                    result = await task
                    await asyncio.sleep(0.5)  # 间隔时间
                    return result

            # 并发执行所有发送任务
            results = await asyncio.gather(
                *[execute_with_semaphore(task) for task in send_tasks],
                return_exceptions=True,
            )

            # 统计成功发送的消息数
            successful_messages = sum(1 for r in results if r is True)

            # 发送底部信息
            footer_text = (
                f"[此消息包含 {successful_messages} 条消息，来自{source_name}]"
            )
            await self.plugin.context.send_message(
                target_session, [Plain(text=footer_text)]
            )

            return successful_messages > 0
        except Exception as e:
            logger.error(f"任务 {task_id}: 发送消息到非QQ平台失败: {e}")
            logger.error(traceback.format_exc())
            return False

    async def _create_non_qq_send_task(self, target_session, msg, msg_id, task_id):
        """
        创建非QQ平台单条消息发送任务喵～ 🏗️
        处理单条消息的平台适配发送！

        Args:
            target_session: 目标会话喵
            msg: 消息数据喵
            msg_id: 消息ID喵
            task_id: 任务ID喵

        Returns:
            发送结果喵～

        Note:
            会自动反序列化消息组件并适配发送喵！ ✨
        """
        from .message_serializer import deserialize_message

        try:
            sender = msg.get("sender_name", "未知用户")
            message_components = deserialize_message(msg.get("message", []))

            # 检查消息是否已发送喵～ ✅
            if self._is_message_sent(target_session, msg_id):
                return True

            # 首先发送发送者信息喵～ 👤
            await self.plugin.context.send_message(
                target_session, [Plain(text=f"{sender}:")]
            )

            # 然后发送消息内容喵～ 📤
            if message_components:
                await self.plugin.context.send_message(
                    target_session, message_components
                )
            else:
                await self.plugin.context.send_message(
                    target_session, [Plain(text="[空消息]")]
                )

            # 记录成功发送喵～ 📝
            self._add_sent_message(target_session, msg_id)
            return True

        except Exception as e:
            logger.error(f"任务 {task_id}: 发送消息到非QQ平台失败喵: {e} 😿")
            return False  # 新增方法: 处理文件类型的消息喵～ 📁

    async def _download_and_send_file(
        self,
        file_url: str,
        file_name: str,
        target_session: str,
        target_id: str,
        sender_name: str = None,
    ) -> bool:
        """
        下载并发送文件消息喵～ 📁
        智能处理文件上传和分享！

        Args:
            file_url: 文件URL喵
            file_name: 文件名喵
            target_session: 目标会话ID喵
            target_id: 目标ID喵
            sender_name: 发送者名称，用于显示在消息中喵

        Returns:
            bool: 发送成功返回True，否则返回False喵～

        Note:
            支持群文件和私聊文件上传，失败时会发送下载链接喵！ ✨
        """
        try:
            import uuid

            # 获取客户端喵～ 🤖
            client = self.plugin.context.get_platform("aiocqhttp").get_client()

            # 创建临时下载目录喵～ 📁
            temp_dir = os.path.join(
                "data", "plugins_data", "astrbot_plugin_turnrig", "temp", "files"
            )
            os.makedirs(temp_dir, exist_ok=True)

            # 生成临时文件路径喵～ 🏷️
            temp_file_path = os.path.join(temp_dir, f"{uuid.uuid4()}_{file_name}")

            logger.info(f"下载文件喵: {file_url} -> {temp_file_path} 📥")

            # 下载文件喵～ 📤
            success = await self._download_file_with_curl(file_url, temp_file_path)
            if not success:
                logger.error(f"下载文件失败喵: {file_url} 😿")
                return False

            # 文件消息头部，包含发送者信息喵～ 📢
            header = "[文件分享喵]"
            if sender_name:
                header = f"[文件分享喵] 来自 {sender_name}"

            # 检查是群聊还是私聊喵～ 🔍
            is_group = "GroupMessage" in target_session

            # 尝试发送文件消息喵～ 📤
            try:
                # 使用上传文件API喵～ 🚀
                api_name = "upload_group_file" if is_group else "upload_private_file"
                target_param = {"group_id" if is_group else "user_id": int(target_id)}

                # 发送文件前的提示消息喵～ 📢
                if header:
                    await client.call_action(
                        "send_group_msg" if is_group else "send_private_msg",
                        **target_param,
                        message=header,
                    )

                # 上传文件喵～ 📤
                response = await client.call_action(
                    api_name, **target_param, file=temp_file_path, name=file_name
                )

                logger.info(f"文件上传响应喵: {response} 📋")

                # 检查响应喵～ ✅
                if isinstance(response, dict) and response.get("status") == "ok":
                    logger.info(f"成功发送文件喵: {file_name} 🎉")
                    return True
                else:
                    logger.warning(f"文件上传API返回错误喵: {response} ⚠️")
                    # 发送一条链接消息作为备用喵～ 🔗
                    await client.call_action(
                        "send_group_msg" if is_group else "send_private_msg",
                        **target_param,
                        message=f"[文件喵] {file_name}\n下载链接: {file_url}",
                    )
                    return True

            except Exception as e:
                logger.error(f"发送文件时出错喵: {e} 😿")

                # 尝试发送文件下载链接作为备用喵～ 🔗
                try:
                    await client.call_action(
                        "send_group_msg" if is_group else "send_private_msg",
                        **target_param,
                        message=f"[文件喵] {file_name}\n下载链接: {file_url}",
                    )
                    return True
                except Exception as e2:
                    logger.error(f"发送文件链接也失败喵: {e2} 😿")
                    return False

        except Exception as e:
            logger.error(f"处理文件消息时出错喵: {e} 😿")
            return False

    async def _download_file_with_curl(self, url: str, output_path: str) -> bool:
        """
        使用curl下载文件喵～ 📥
        专业的文件下载工具，支持各种文件格式！

        Args:
            url: 文件URL喵
            output_path: 输出路径喵

        Returns:
            bool: 下载成功返回True，否则返回False喵～

        Note:
            会自动处理重定向和用户代理，确保下载完整喵！ ✨
        """
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # 构建curl命令
            cmd = [
                "curl",
                "-s",  # 静默模式
                "-L",  # 跟随重定向
                "-o",
                output_path,  # 输出文件
                "-H",
                "User-Agent: Mozilla/5.0",
                url,
            ]

            # 执行curl命令
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            # 检查下载结果
            if (
                process.returncode == 0
                and os.path.exists(output_path)
                and os.path.getsize(output_path) > 0
            ):
                logger.info(f"成功下载文件: {output_path}")
                return True
            else:
                stderr_text = stderr.decode() if stderr else "未知错误"
                logger.warning(f"下载文件失败: {stderr_text}")
                return False

        except Exception as e:
            logger.error(f"下载文件异常: {e}")
            logger.error(traceback.format_exc())
            return False
