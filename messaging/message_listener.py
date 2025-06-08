import re
import time
from typing import Any

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent
from astrbot.api.message_components import Plain

# 更新导入路径
from .message_serializer import async_serialize_message


class MessageListener:
    """处理消息监听和缓存的类喵～"""

    def __init__(self, plugin):
        self.plugin = plugin
        # 调试计数器
        self.message_count = 0
    def _extract_onebot_fields(self, event: AstrMessageEvent) -> dict:
        """从 aiocqhttp_platform_adapter 的原始事件中提取 OneBot V11 协议字段

        Returns:
            dict: 包含 message_type, sub_type 等原始字段的字典
        """
        onebot_fields = {
            "message_type": None,
            "sub_type": None,
            "platform": event.get_platform_name(),
        }

        try:
            logger.debug(f"开始提取 OneBot 字段，平台: {event.get_platform_name()}")

            # 检查 message_obj 是否有 raw_message 属性
            if not hasattr(event.message_obj, "raw_message"):
                logger.warning("event.message_obj 没有 raw_message 属性")
                raise AttributeError("No raw_message attribute")

            raw_event = event.message_obj.raw_message
            if not raw_event:
                logger.warning("raw_message 为空")
                raise ValueError("raw_message is None")

            logger.info(f"获取到原始事件对象: {type(raw_event)}")

            # 优先从 aiocqhttp_platform_adapter 传递的 raw_message 中获取原始 OneBot 字段
            if event.get_platform_name() == "aiocqhttp":
                logger.debug("处理 aiocqhttp 平台的原始事件")

                # 方法1: 直接从 OneBot Event 对象访问字段
                if hasattr(raw_event, "message_type"):
                    onebot_fields["message_type"] = getattr(raw_event, "message_type", None)
                    onebot_fields["sub_type"] = getattr(raw_event, "sub_type", "normal")
                    logger.info(f"✅ 从 OneBot Event 对象提取字段成功: message_type={onebot_fields['message_type']}, sub_type={onebot_fields['sub_type']}")

                # 方法2: 如果是字典格式（某些适配器可能传递字典）
                elif isinstance(raw_event, dict):
                    onebot_fields["message_type"] = raw_event.get("message_type", None)
                    onebot_fields["sub_type"] = raw_event.get("sub_type", "normal")
                    logger.info(f"✅ 从字典格式提取字段成功: message_type={onebot_fields['message_type']}, sub_type={onebot_fields['sub_type']}")

                # 方法3: 通过索引访问（OneBot Event 也支持字典式访问）
                elif hasattr(raw_event, "__getitem__"):
                    try:
                        onebot_fields["message_type"] = raw_event["message_type"]
                        onebot_fields["sub_type"] = raw_event.get("sub_type", "normal")
                        logger.info(f"✅ 通过索引访问提取字段成功: message_type={onebot_fields['message_type']}, sub_type={onebot_fields['sub_type']}")
                    except (KeyError, TypeError) as e:
                        logger.debug(f"通过索引访问失败: {e}，继续尝试其他方法")

                # 方法4: 详细检查原始事件的结构
                if onebot_fields["message_type"] is None:
                    logger.warning("所有常规方法都未能提取到 OneBot 字段，进行详细分析")
                    logger.debug(f"raw_event 可用属性: {dir(raw_event)}")
                    if hasattr(raw_event, "__dict__"):
                        logger.debug(f"raw_event.__dict__: {raw_event.__dict__}")

                    # 尝试强制转换为字符串查看内容
                    raw_str = str(raw_event)
                    logger.debug(f"raw_event 字符串表示: {raw_str[:200]}...")

                    # 查找可能的 message_type 字段
                    if "message_type" in raw_str:
                        logger.debug("在字符串表示中找到 message_type 字段")

            # 如果上游没有提供原始字段，则从 AstrBot 的 message_type 推断
            if onebot_fields["message_type"] is None:
                astr_message_type = event.get_message_type()
                if astr_message_type.name == "GROUP_MESSAGE":
                    onebot_fields["message_type"] = "group"
                elif astr_message_type.name == "FRIEND_MESSAGE":
                    onebot_fields["message_type"] = "private"
                else:
                    onebot_fields["message_type"] = "unknown"
                logger.warning(f"⚠️ 从 AstrBot MessageType 推断: {onebot_fields['message_type']}")

            # 确保 sub_type 有默认值
            if onebot_fields["sub_type"] is None:
                onebot_fields["sub_type"] = "normal"

            logger.info(f"🎯 最终提取的 OneBot 字段: {onebot_fields}")

        except Exception as e:
            logger.error(f"❌ 提取 OneBot 字段时出错: {e}", exc_info=True)
            # 发生错误时使用推断值
            astr_message_type = event.get_message_type()
            if astr_message_type.name == "GROUP_MESSAGE":
                onebot_fields["message_type"] = "group"
            elif astr_message_type.name == "FRIEND_MESSAGE":
                onebot_fields["message_type"] = "private"
            onebot_fields["sub_type"] = "normal"
            logger.warning(f"⚠️ 错误恢复: 使用推断值 {onebot_fields}")

        return onebot_fields
    async def on_all_message(self, event: AstrMessageEvent):
        """监听所有消息并进行处理喵～"""
        try:
            # 获取消息ID，避免重复处理
            message_id = event.message_obj.message_id

            # 提取 OneBot V11 协议的原始字段
            onebot_fields = self._extract_onebot_fields(event)
            logger.info(f"🎯 提取到的 OneBot 字段: {onebot_fields}")

            # 初始化关键变量
            has_mface = False
            serialized_messages = []

            # 检查消息是否已经处理过
            if self._is_message_processed(message_id):
                logger.debug(f"消息 {message_id} 已经处理过，跳过")
                return

            # 检查是否为插件指令，如果是则跳过监听
            plain_text = event.message_str
            if plain_text:
                # 检查是否为插件的指令前缀
                if (
                    plain_text.startswith("/tr ")
                    or plain_text.startswith("/turnrig ")
                    or plain_text == "/tr"
                    or plain_text == "/turnrig"
                ):
                    logger.debug(f"消息 {message_id} 是插件指令，跳过监听")
                    return
                # 检查是否为转发指令
                if plain_text.startswith("/fn ") or plain_text == "/fn":
                    logger.debug(f"消息 {message_id} 是转发指令，跳过监听")
                    return

            logger.info(
                f"MessageListener.on_all_message 被调用，处理消息: {event.message_str}"
            )

            # 获取消息平台名称，判断是否为 aiocqhttp
            # platform_name = event.get_platform_name()
            self.message_count += 1  # 获取已启用的任务
            enabled_tasks = self.plugin.get_all_enabled_tasks()
            logger.debug(f"获取到 {len(enabled_tasks)} 个已启用任务")

            # 优先使用事件的message_str属性
            if not plain_text and hasattr(event.message_obj, "message_str"):
                plain_text = event.message_obj.message_str

            logger.debug(
                f'收到消息 [{event.get_sender_name()}]: "{plain_text}" (长度: {len(plain_text) if plain_text else 0})'
            )

            # 如果还是没有文本内容，尝试从raw_message中获取
            if (
                not plain_text
                and hasattr(event.message_obj, "raw_message")
                and event.message_obj.raw_message
            ):
                # 尝试从raw_message中获取内容

                try:
                    logger.debug(
                        f"从raw_message找到内容: {event.message_obj.raw_message}"
                    )
                except Exception:
                    pass

            # 获取消息组件
            messages = event.get_messages()
            if (
                not messages
                and hasattr(event.message_obj, "message")
                and isinstance(event.message_obj.message, list)
            ):
                logger.warning("框架未处理message列表，直接进行处理")
                # 简单处理为文本消息
                for msg_part in event.message_obj.message:
                    if (
                        msg_part.get("type") == "text"
                        and "data" in msg_part
                        and "text" in msg_part["data"]
                    ):
                        messages.append(Plain(text=msg_part["data"]["text"]))
                    elif msg_part.get("type") == "mface":
                        # 检测到特殊表情
                        has_mface = True

            # 输出组件详情
            if messages:
                components_info = []
                for i, comp in enumerate(messages):
                    comp_type = type(comp).__name__
                    text_content = (
                        comp.text if hasattr(comp, "text") else str(comp)[:30]
                    )
                    if len(text_content) > 30:
                        text_content = text_content[:30] + "..."
                    if hasattr(comp, "text"):
                        components_info.append(
                            f'[{i}] [{comp_type}] "{text_content}" (长度: {len(text_content)})'
                        )
                    else:
                        components_info.append(f"[{i}] [{comp_type}] {text_content}")
                logger.debug(f"消息组件: {' | '.join(components_info)}")

            # 强制检查消息原始数据 - 直接处理aicqhttp适配器转发的原始事件
            if hasattr(event.message_obj, "__dict__"):
                raw_obj = event.message_obj.__dict__
                # 直接检查是否有特殊表情相关结构
                if "message" in raw_obj and isinstance(raw_obj["message"], list):
                    for msg in raw_obj["message"]:
                        if isinstance(msg, dict) and msg.get("type") == "mface":
                            has_mface = True
                            logger.warning(f"直接从__dict__找到mface: {msg}")
                            # 提取数据
                            data = msg.get("data", {})
                            url = data.get("url", "")
                            summary = data.get("summary", "[表情]")
                            emoji_id = data.get("emoji_id", "")
                            package_id = data.get("emoji_package_id", "")
                            key = data.get("key", "")
                            mface_data = {
                                "type": "image",
                                "url": url,
                                "summary": summary,
                                "emoji_id": emoji_id,
                                "emoji_package_id": package_id,
                                "key": key,
                                "is_mface": True,
                                "is_gif": True,
                                "flash": True,
                            }
                            serialized_messages.append(mface_data)

            # 开始激进检测模式，查找所有可能的mface内容
            for attr_name in dir(event.message_obj):
                if not attr_name.startswith("_"):
                    try:
                        attr_value = getattr(event.message_obj, attr_name)
                        if "mface" in str(attr_value).lower():
                            has_mface = True
                            logger.warning(
                                f"从属性 {attr_name} 中发现mface内容: {attr_value}"
                            )
                    except Exception:
                        pass

            # 开始针对每个任务进行处理
            task_matched = False
            for task in enabled_tasks:
                task_id = task.get("id")

                # 检查是否应该监听此消息
                should_monitor = self._should_monitor_message(task, event)
                should_monitor_user = self._should_monitor_user(task, event)

                if should_monitor or should_monitor_user:
                    task_matched = True
                    # 确保消息非空 - 优先使用各种方式确保获取到内容
                    session_id = event.unified_msg_origin

                    # 重置特殊表情标记，单独检测每个任务
                    task_has_mface = has_mface

                    # 初始化缓存
                    if task_id not in self.plugin.message_cache:
                        self.plugin.message_cache[task_id] = {}
                    if session_id not in self.plugin.message_cache[task_id]:
                        self.plugin.message_cache[task_id][session_id] = []

                    # 获取消息详情
                    timestamp = int(time.time())
                    mface_components = [
                        msg for msg in serialized_messages if msg.get("is_mface")
                    ]

                    logger.debug(
                        f"详细消息对象: {event.message_obj.__dict__ if hasattr(event.message_obj, '__dict__') else 'No __dict__'}"
                    )

                    # 序列化消息 - 保存之前已探测到的特殊表情
                    task_serialized_messages = await async_serialize_message(
                        messages if messages else []
                    )

                    # 合并普通消息和特殊表情消息
                    for mface_msg in mface_components:
                        task_serialized_messages.append(mface_msg)

                    serialized_messages = task_serialized_messages

                    # 方法1: 直接从message属性获取
                    if (
                        not task_has_mface
                        and hasattr(event.message_obj, "message")
                        and isinstance(event.message_obj.message, list)
                    ):
                        for msg in event.message_obj.message:
                            if isinstance(msg, dict) and msg.get("type") == "mface":
                                task_has_mface = True
                                logger.warning(f"从message列表找到mface: {msg}")
                                # 提取数据
                                data = msg.get("data", {})
                                url = data.get("url", "")
                                summary = data.get("summary", "[表情]")
                                emoji_id = data.get("emoji_id", "")
                                package_id = data.get("emoji_package_id", "")
                                key = data.get("key", "")
                                mface_as_image = {
                                    "type": "image",
                                    "url": url,
                                    "summary": summary,
                                    "emoji_id": emoji_id,
                                    "emoji_package_id": package_id,
                                    "key": key,
                                    "is_mface": True,
                                    "is_gif": True,
                                    "flash": True,
                                }
                                serialized_messages.append(mface_as_image)

                    # 方法2: 检查raw_message对象结构
                    if (
                        not task_has_mface
                        and hasattr(event.message_obj, "raw_message")
                        and event.message_obj.raw_message
                    ):
                        try:
                            raw_message = event.message_obj.raw_message
                            logger.warning(f"原始消息类型: {type(raw_message)}")

                            if hasattr(raw_message, "message") and isinstance(
                                raw_message.message, list
                            ):
                                msg_list = raw_message.message
                            # 再尝试从raw_message字典中获取message列表
                            elif (
                                isinstance(raw_message, dict)
                                and "message" in raw_message
                            ):
                                msg_list = raw_message["message"]
                            else:
                                msg_list = []

                            # 处理获取到的消息列表
                            for raw_msg in msg_list:
                                # 处理图片消息并提取filename
                                if (
                                    isinstance(raw_msg, dict)
                                    and raw_msg.get("type") == "image"
                                    and "data" in raw_msg
                                ):
                                    extracted_filename = raw_msg["data"].get("filename")
                                    if extracted_filename:
                                        logger.debug(
                                            f"从原始消息提取到filename: {extracted_filename}"
                                        )
                                        # 在序列化消息中找到对应的图片并添加filename
                                        for i, msg in enumerate(serialized_messages):
                                            if msg.get("type") == "image":
                                                serialized_messages[i]["filename"] = (
                                                    extracted_filename
                                                )
                                                logger.debug(
                                                    f"已将filename {extracted_filename} 添加到图片消息"
                                                )
                                                break

                                # 处理特殊表情(mface)
                                elif (
                                    isinstance(raw_msg, dict)
                                    and raw_msg.get("type") == "mface"
                                ):
                                    task_has_mface = True
                                    logger.warning(
                                        f"从raw_message列表找到mface: {raw_msg}"
                                    )
                                    # 提取表情数据
                                    data = raw_msg.get("data", {})
                                    url = raw_msg.get("url", "") or data.get("url", "")
                                    summary = raw_msg.get("summary", "") or data.get(
                                        "summary", "[表情]"
                                    )
                                    emoji_id = raw_msg.get("emoji_id", "") or data.get(
                                        "emoji_id", ""
                                    )
                                    package_id = raw_msg.get(
                                        "emoji_package_id", ""
                                    ) or data.get("emoji_package_id", "")
                                    key = raw_msg.get("key", "") or data.get("key", "")

                                    mface_as_image = {
                                        "type": "image",
                                        "url": url,
                                        "summary": summary,
                                        "emoji_id": emoji_id,
                                        "emoji_package_id": package_id,
                                        "key": key,
                                        "is_mface": True,
                                        "is_gif": True,
                                        "flash": True,
                                    }
                                    serialized_messages.append(mface_as_image)
                        except Exception as e:
                            logger.error(f"处理原始消息时出错: {e}", exc_info=True)

                        # 方法3: 尝试从raw_message字符串中解析mface
                        if not task_has_mface and hasattr(
                            event.message_obj, "raw_message"
                        ):
                            raw_str = str(event.message_obj.raw_message)
                            if "[CQ:mface" in raw_str or "mface" in raw_str.lower():
                                task_has_mface = True
                                # 尝试提取mface参数
                                url_match = re.search(
                                    r"url=(https?://[^,\]]+)", raw_str
                                )
                                summary_match = re.search(r"summary=([^,\]]+)", raw_str)
                                url = url_match.group(1) if url_match else ""
                                summary = (
                                    summary_match.group(1)
                                    if summary_match
                                    else "[表情]"
                                )

                                mface_as_image = {
                                    "type": "image",
                                    "url": url,
                                    "summary": summary,
                                    "is_mface": True,
                                    "is_gif": True,
                                    "flash": True,
                                }
                                serialized_messages.append(mface_as_image)

                    # 如果序列化后没有内容，但原始消息有内容，则直接创建一个纯文本组件
                    if (
                        not serialized_messages
                        or (
                            len(serialized_messages) == 1
                            and serialized_messages[0].get("type") == "plain"
                            and not serialized_messages[0].get("text")
                        )
                    ) and plain_text:
                        serialized_messages = [{"type": "plain", "text": plain_text}]
                        # 检查是否应该从原始消息中提取更多信息
                        if (
                            hasattr(event.message_obj, "raw_message")
                            and event.message_obj.raw_message
                        ):
                            raw_text = str(event.message_obj.raw_message)
                            if len(raw_text) > len(plain_text):
                                serialized_messages[0]["text"] = raw_text

                    # 生成消息概要
                    message_outline = (
                        plain_text[:30] + ("..." if len(plain_text) > 30 else "")
                        if plain_text
                        else ""
                    )
                    if not message_outline and serialized_messages:
                        # 尝试从序列化消息中生成概要
                        has_content = False
                        for msg in serialized_messages:
                            if msg.get("type") == "plain" and msg.get("text"):
                                text = msg.get("text", "")
                                message_outline = text[:30] + (
                                    "..." if len(text) > 30 else ""
                                )
                                has_content = True
                                break
                            elif (
                                msg.get("type") == "image"
                                and msg.get("is_mface")
                                and msg.get("summary")
                            ):
                                # 新增: 为特殊表情添加专门的概要
                                message_outline = msg.get("summary", "[表情]")
                                has_content = True
                                break

                        if not has_content and not serialized_messages:
                            # 如果仍然没有概要，使用通用消息类型描述
                            non_text_types = []
                            for msg in serialized_messages:
                                if msg.get("type") != "plain" or not msg.get("text"):
                                    msg_type = msg.get("type", "unknown")
                                    if msg.get("is_mface"):
                                        non_text_types.append("特殊表情")
                                    else:
                                        non_text_types.append(msg_type)

                            message_outline = (
                                f"[{', '.join(non_text_types)}]"
                                if non_text_types
                                else "[消息]"
                            )

                    # 处理特殊表情的标记
                    if task_has_mface or has_mface:
                        # 添加特殊标记
                        for msg in serialized_messages:
                            if msg.get("is_mface"):
                                # 确保所有必要的字段都存在
                                if not msg.get("summary"):
                                    msg["summary"] = "[表情]"
                                if not msg.get("is_gif"):
                                    msg["is_gif"] = True
                                if not msg.get("flash"):
                                    msg["flash"] = True

                    # 检查消息长度限制
                    max_messages = task.get(
                        "max_messages",
                        self.plugin.config.get("default_max_messages", 20),
                    )
                    if (
                        len(self.plugin.message_cache[task_id][session_id])
                        >= max_messages
                    ):
                        self.plugin.message_cache[task_id][session_id].pop(
                            0
                        )  # 缓存消息
                    cached_message = {
                        "id": message_id,
                        "timestamp": timestamp,
                        "sender_name": event.get_sender_name(),
                        "sender_id": event.get_sender_id(),  # 添加发送者ID
                        "messages": serialized_messages,
                        "message_outline": message_outline,
                        "onebot_fields": onebot_fields,  # 添加 OneBot 原始字段
                    }

                    self.plugin.message_cache[task_id][session_id].append(
                        cached_message
                    )
                    logger.info(
                        f"已缓存消息到任务 {task_id}, 会话 {session_id}, 缓存大小: {len(self.plugin.message_cache[task_id][session_id])}"
                    )

                    # 立即保存缓存，确保不丢失数据
                    self.plugin.save_message_cache()

                    # 检查是否达到转发条件
                    if self.plugin.forward_manager:
                        await self.plugin.forward_manager.forward_messages(
                            task_id, session_id
                        )

            if not task_matched:
                logger.debug("没有任务匹配当前消息，消息未被缓存")

        except Exception as e:
            logger.error(f"处理消息时发生错误: {e}", exc_info=True)

    async def on_group_upload_notice(self, event):
        """处理群文件上传通知"""
        try:
            # 获取文件信息
            file_info = event.file
            session_id = event.unified_msg_origin

            # 构造文件消息
            file_message = {
                "type": "notice",
                "notice_type": "group_upload",
                "file": file_info,
            }  # 获取启用的任务并缓存
            enabled_tasks = self.plugin.get_all_enabled_tasks()
            for task in enabled_tasks:
                task_id = task.get("id")
                if task_id not in self.plugin.message_cache:
                    self.plugin.message_cache[task_id] = {}
                if session_id not in self.plugin.message_cache[task_id]:
                    self.plugin.message_cache[task_id][session_id] = []

                # 缓存文件上传通知
                cached_message = {
                    "id": f"upload_{int(time.time())}",
                    "timestamp": int(time.time()),
                    "sender_name": event.get_sender_name(),
                    "messages": [file_message],
                    "message_outline": f"[群文件] {file_info.get('name', '')}",
                }

                self.plugin.message_cache[task_id][session_id].append(cached_message)
                logger.info(f"已缓存文件上传通知到任务 {task_id}")

        except Exception as e:
            logger.error(f"处理群文件上传时发生错误: {e}", exc_info=True)

    def _is_message_processed(self, message_id: str) -> bool:
        """检查消息是否已经被处理过"""
        # 检查所有任务的已处理消息ID列表
        for key in self.plugin.config:
            if key.startswith("processed_message_ids_"):
                processed_list = self.plugin.config.get(key, [])
                for processed_msg in processed_list:
                    if (
                        isinstance(processed_msg, dict)
                        and processed_msg.get("id") == message_id
                    ):
                        return True
        return False

    def _mark_message_processed(self, message_id: str, task_id: str):
        """标记消息为已处理
        Args:
            message_id: 消息ID
        """
        key = f"processed_message_ids_{task_id}"
        if key not in self.plugin.config:
            self.plugin.config[key] = []

        timestamp = int(time.time())
        self.plugin.config[key].append({"id": message_id, "timestamp": timestamp})

        # 保持列表大小，只保留最近的100条记录
        if len(self.plugin.config[key]) > 100:
            self.plugin.config[key] = self.plugin.config[key][-100:]

    def _should_monitor_user(
        self, task: dict[str, Any], event: AstrMessageEvent
    ) -> bool:
        """检查是否应该监听特定用户的消息"""
        session_id = event.unified_msg_origin
        logger.debug(f"判断会话 {session_id} 是否应被监听")

        # 获取群组ID和用户ID
        group_id = event.get_group_id()

        # 检查群内特定用户监听
        if group_id:
            group_id_str = str(group_id)
            # 处理monitored_users_in_groups中使用完整会话ID作为键的情况
            if group_id_str and group_id_str in task.get(
                "monitored_users_in_groups", {}
            ):
                logger.debug(f"群 {group_id} 已配置特定用户监听，应监听此会话")
                return True

            # 检查纯群号格式
            if session_id in task.get("monitored_users_in_groups", {}):
                logger.debug(
                    f"会话ID {session_id} 直接存在于群内用户监听配置中，应监听此会话"
                )
                return True

        # 最重要的修复：直接检查会话ID是否存在于任务的monitor_groups中
        if session_id in task.get("monitor_groups", []):
            logger.debug(f"会话ID {session_id} 直接存在于群组监听列表中，应监听此会话")
            return True

        # 检查会话ID是否存在于私聊监听列表中
        if session_id in task.get("monitor_private_users", []):
            logger.debug(f"会话ID {session_id} 直接存在于私聊监听列表中，应监听此会话")
            return True

        # 最后检查完整的session_id是否直接匹配monitor_sessions
        if session_id in task.get("monitor_sessions", []):
            return True

        # 检查群组监听 - 使用多种格式尝试匹配
        if group_id:
            group_id_str = str(group_id) if group_id else ""
            if group_id_str and any(
                str(g) == group_id_str for g in task.get("monitor_groups", [])
            ):
                logger.debug(f"群号 {group_id} 在监听列表中，应监听此会话")
                return True

            # 检查完整会话ID格式 - 关键修改！
            for g in task.get("monitor_groups", []):
                expected_id = f"aiocqhttp:GroupMessage:{g}"
                if session_id == expected_id:
                    return True

            # 尝试其他可能的格式
            possible_formats = [
                f"aiocqhttp:GroupMessage:{group_id}",
                f"aiocqhttp:group_message:{group_id}",
                group_id_str,
            ]
            for fmt in possible_formats:
                if fmt in task.get("monitor_groups", []):
                    return True

        # 检查私聊用户监听
        user_id = event.get_sender_id()
        if user_id:
            user_id_str = str(user_id) if user_id else ""
            if user_id_str and any(
                str(u) == user_id_str for u in task.get("monitor_private_users", [])
            ):
                logger.debug(f"用户ID {user_id} 在私聊监听列表中，应监听此会话")
                return True

            # 检查会话完整ID是否在监听列表中
            if any(
                session_id == f"aiocqhttp:FriendMessage:{u}"
                for u in task.get("monitor_private_users", [])
            ):
                return True

            # 尝试其他可能的格式
            possible_formats = [
                f"aiocqhttp:FriendMessage:{user_id}",
                f"aiocqhttp:friend_message:{user_id}",
                user_id_str,
            ]
            for fmt in possible_formats:
                if fmt in task.get("monitor_private_users", []):
                    logger.debug(f"会话ID格式 {fmt} 在私聊监听列表中，应监听此会话")
                    return True

        # 最后再检查一次完整的session_id是否直接匹配
        if session_id in task.get("monitor_sessions", []):
            return True

        return False

    def _should_monitor_group_user(
        self, task: dict[str, Any], event: AstrMessageEvent
    ) -> bool:
        """检查是否监听群内特定用户"""
        message_type_name = event.get_message_type().name
        group_id = event.get_group_id()
        session_id = event.unified_msg_origin
        sender_id = event.get_sender_id()

        # 只处理群消息
        if message_type_name != "GROUP":
            return False

        group_id_str = str(group_id)
        # 重要修改：同时检查纯群号和完整会话ID两种格式
        monitored_users = task.get("monitored_users_in_groups", {}).get(
            group_id_str, []
        )
        if not monitored_users and session_id in task.get(
            "monitored_users_in_groups", {}
        ):
            monitored_users = task.get("monitored_users_in_groups", {}).get(
                session_id, []
            )

        # 如果没有指定用户列表，则监听所有人
        if not monitored_users:
            return False

        sender_id_str = str(sender_id)
        for user_id_str in monitored_users:
            if user_id_str == sender_id_str:
                return True

        is_monitored = sender_id_str in [str(uid) for uid in monitored_users]
        if is_monitored:
            logger.debug(f"群 {group_id} 中的用户 {sender_id} 在监听列表中")

        return is_monitored

    def _should_monitor_message(
        self, task: dict[str, Any], event: AstrMessageEvent
    ) -> bool:
        """检查是否应该监听此消息喵～（新的统一逻辑）"""
        session_id = event.unified_msg_origin
        # sender_id = event.get_sender_id()

        # 解析会话ID信息
        parsed_info = self._parse_session_id_info(session_id)
        if not parsed_info:
            logger.debug(f"无法解析会话ID: {session_id}")
            return False

        # 根据会话类型检查对应的监听列表
        if parsed_info["is_group"]:
            group_id = parsed_info["id"]
            if group_id in task.get("monitor_groups", []):
                logger.debug(f"群聊 {group_id} 在监听列表中，应监听此会话")
                return True

            # 检查是否在群内用户监听配置中
            if session_id in task.get("monitored_users_in_groups", {}):
                logger.debug(
                    f"会话ID {session_id} 直接存在于群内用户监听配置中，应监听此会话"
                )
                return True
            if group_id in task.get("monitored_users_in_groups", {}):
                logger.debug(f"群ID {group_id} 存在于群内用户监听配置中，应监听此会话")
                return True
        else:
            user_id = parsed_info["id"]
            if user_id in task.get("monitor_private_users", []):
                logger.debug(f"私聊用户 {user_id} 在监听列表中，应监听此会话")
                return True

        # 向后兼容：检查旧的 monitor_sessions 列表
        if session_id in task.get("monitor_sessions", []):
            return True

        return False

    def _parse_session_id_info(self, session_id: str) -> dict[str, Any]:
        """解析完整会话ID，提取平台、类型和ID信息

        Args:
            session_id: 形如 "aiocqhttp:GroupMessage:123456" 的会话ID

        Returns:
            包含解析信息的字典，格式为:
            {
                "platform": "aiocqhttp",
                "message_type": "GroupMessage",
                "id": "123456",
                "is_group": True,
                "full_id": "aiocqhttp:GroupMessage:123456"
            }
            如果解析失败则返回None"""
        if not session_id or not isinstance(session_id, str):
            return None

        parts = session_id.split(":")
        if len(parts) != 3:
            logger.debug(f"会话ID格式不正确: {session_id}，期望格式: platform:type:id")
            return None

        platform, message_type, id_part = parts

        # 判断是否为群聊
        is_group = "group" in message_type.lower()

        return {
            "platform": platform,
            "message_type": message_type,
            "id": id_part,
            "is_group": is_group,
            "full_id": session_id,
        }
