import re
import time
from typing import Any

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent
from astrbot.api.message_components import Plain

# 更新导入路径喵～ 📦
from .message_serializer import async_serialize_message


class MessageListener:
    """
    消息监听器喵～ 👂
    专门负责监听和处理各种消息的可爱小助手！ ฅ(^•ω•^)ฅ

    这个小监听器会帮你：
    - 👂 监听所有消息事件
    - 🔍 检测消息内容和特殊格式
    - 💾 缓存符合条件的消息
    - 📤 触发消息转发操作
    - 🎯 智能过滤和匹配规则

    Note:
        所有的消息都会经过这里进行精心筛选喵！ ✨
    """

    def __init__(self, plugin):
        """
        初始化消息监听器喵～ 🐾

        Args:
            plugin: 插件实例，提供配置和服务喵～
        """
        self.plugin = plugin
        # 调试计数器喵～ 🔢
        self.message_count = 0

    def _extract_onebot_fields(self, event: AstrMessageEvent) -> dict:
        """
        从 aiocqhttp_platform_adapter 的原始事件中提取 OneBot V11 协议字段喵～ 🔍

        Args:
            event: 消息事件对象喵

        Returns:
            包含 message_type, sub_type 等原始字段的字典喵～

        Note:
            用于获取更准确的消息类型信息喵！ 📋
        """
        onebot_fields = {
            "message_type": None,
            "sub_type": None,
            "platform": event.get_platform_name(),
        }

        try:
            logger.debug(
                f"开始提取 OneBot 字段，平台: {event.get_platform_name()} 喵～ 🔍"
            )

            # 检查 message_obj 是否有 raw_message 属性喵～ 📋
            if not hasattr(event.message_obj, "raw_message"):
                logger.warning("event.message_obj 没有 raw_message 属性喵 😿")
                raise AttributeError("No raw_message attribute")

            raw_event = event.message_obj.raw_message
            if not raw_event:
                logger.warning("raw_message 为空喵 😿")
                raise ValueError("raw_message is None")

            logger.info(f"获取到原始事件对象喵: {type(raw_event)} 📦")

            # 优先从 aiocqhttp_platform_adapter 传递的 raw_message 中获取原始 OneBot 字段喵～ 🎯
            if event.get_platform_name() == "aiocqhttp":
                logger.debug("处理 aiocqhttp 平台的原始事件喵～ 🤖")

                # 方法1: 直接从 OneBot Event 对象访问字段喵～ 📋
                if hasattr(raw_event, "message_type"):
                    onebot_fields["message_type"] = getattr(
                        raw_event, "message_type", None
                    )
                    onebot_fields["sub_type"] = getattr(raw_event, "sub_type", "normal")
                    logger.info(
                        f"✅ 从 OneBot Event 对象提取字段成功喵: message_type={onebot_fields['message_type']}, sub_type={onebot_fields['sub_type']} 🎉"
                    )

                # 方法2: 如果是字典格式（某些适配器可能传递字典）喵～ 📚
                elif isinstance(raw_event, dict):
                    onebot_fields["message_type"] = raw_event.get("message_type", None)
                    onebot_fields["sub_type"] = raw_event.get("sub_type", "normal")
                    logger.info(
                        f"✅ 从字典格式提取字段成功喵: message_type={onebot_fields['message_type']}, sub_type={onebot_fields['sub_type']} 📖"
                    )

                # 方法3: 通过索引访问（OneBot Event 也支持字典式访问）喵～ 🔑
                elif hasattr(raw_event, "__getitem__"):
                    try:
                        onebot_fields["message_type"] = raw_event["message_type"]
                        onebot_fields["sub_type"] = raw_event.get("sub_type", "normal")
                        logger.info(
                            f"✅ 通过索引访问提取字段成功喵: message_type={onebot_fields['message_type']}, sub_type={onebot_fields['sub_type']} 🗝️"
                        )
                    except (KeyError, TypeError) as e:
                        logger.debug(f"通过索引访问失败喵: {e}，继续尝试其他方法 🔄")

                # 方法4: 详细检查原始事件的结构喵～ 🔬
                if onebot_fields["message_type"] is None:
                    logger.warning(
                        "所有常规方法都未能提取到 OneBot 字段，进行详细分析喵 🔍"
                    )
                    logger.debug(f"raw_event 可用属性喵: {dir(raw_event)} 📋")
                    if hasattr(raw_event, "__dict__"):
                        logger.debug(f"raw_event.__dict__ 喵: {raw_event.__dict__} 📝")

                    # 尝试强制转换为字符串查看内容喵～ 📄
                    raw_str = str(raw_event)
                    logger.debug(f"raw_event 字符串表示喵: {raw_str[:200]}... 📜")

                    # 查找可能的 message_type 字段喵～ 🔍
                    if "message_type" in raw_str:
                        logger.debug("在字符串表示中找到 message_type 字段喵 ✨")

            # 如果上游没有提供原始字段，则从 AstrBot 的 message_type 推断喵～ 🤔
            if onebot_fields["message_type"] is None:
                astr_message_type = event.get_message_type()
                if astr_message_type.name == "GROUP_MESSAGE":
                    onebot_fields["message_type"] = "group"
                elif astr_message_type.name == "FRIEND_MESSAGE":
                    onebot_fields["message_type"] = "private"
                else:
                    onebot_fields["message_type"] = "unknown"
                logger.warning(
                    f"⚠️ 从 AstrBot MessageType 推断喵: {onebot_fields['message_type']} 🎯"
                )

            # 确保 sub_type 有默认值喵～ 📋
            if onebot_fields["sub_type"] is None:
                onebot_fields["sub_type"] = "normal"

            logger.info(f"🎯 最终提取的 OneBot 字段喵: {onebot_fields} ✅")

        except Exception as e:
            logger.error(f"❌ 提取 OneBot 字段时出错喵: {e} 😿", exc_info=True)
            # 发生错误时使用推断值喵～ 🆘
            astr_message_type = event.get_message_type()
            if astr_message_type.name == "GROUP_MESSAGE":
                onebot_fields["message_type"] = "group"
            elif astr_message_type.name == "FRIEND_MESSAGE":
                onebot_fields["message_type"] = "private"
            onebot_fields["sub_type"] = "normal"
            logger.warning(f"⚠️ 错误恢复: 使用推断值喵 {onebot_fields} 🔧")

        return onebot_fields

    async def on_all_message(self, event: AstrMessageEvent):
        """
        监听所有消息并进行处理喵～ 👂
        这是消息处理的核心方法，会对每条消息进行详细分析！

        Args:
            event: 消息事件对象喵

        Note:
            会自动过滤重复消息和插件指令喵～ 🔍
        """
        try:
            # 获取消息ID，避免重复处理喵～ 🆔
            try:
                message_id = event.message_obj.message_id
                if not message_id:
                    # 生成临时ID防止处理失败喵～ 🔧
                    message_id = f"temp_{int(time.time())}_{hash(str(event.message_str))}"
                    logger.warning(f"消息ID为空，使用临时ID: {message_id} 喵～ ⚠️")
            except AttributeError as e:
                # 处理消息对象缺少属性的情况喵～ 😿
                message_id = f"fallback_{int(time.time())}_{hash(str(event.message_str))}"
                logger.warning(f"获取消息ID失败，使用fallback ID: {message_id}，错误: {e} 喵～ ⚠️")

            # 提取 OneBot V11 协议的原始字段喵～ 📋
            try:
                onebot_fields = self._extract_onebot_fields(event)
                logger.info(f"🎯 提取到的 OneBot 字段喵: {onebot_fields} ✨")
            except Exception as e:
                # 处理字段提取失败的情况喵～ 😿
                logger.warning(f"提取 OneBot 字段失败，使用默认值喵: {e} ⚠️")
                onebot_fields = {
                    "message_type": "unknown",
                    "sub_type": "normal",
                    "platform": "aiocqhttp"
                }

            # 初始化关键变量喵～ 🔢
            has_mface = False
            serialized_messages = []

            # 检查消息是否已经处理过喵～ 🔍
            if self._is_message_processed(message_id):
                logger.debug(f"消息 {message_id} 已经处理过，跳过喵～ ⏭️")
                return

            # 检查是否为插件指令，如果是则跳过监听喵～ ⚠️
            plain_text = event.message_str
            if plain_text:
                # 检查是否为插件的指令前缀喵～ 🔍
                if (
                    plain_text.startswith("/tr ")
                    or plain_text.startswith("/turnrig ")
                    or plain_text == "/tr"
                    or plain_text == "/turnrig"
                ):
                    logger.debug(f"消息 {message_id} 是插件指令，跳过监听喵～ 🚫")
                    return
                # 检查是否为转发指令喵～ 📤
                if plain_text.startswith("/fn ") or plain_text == "/fn":
                    logger.debug(f"消息 {message_id} 是转发指令，跳过监听喵～ 🔄")
                    return

            logger.info(
                f"MessageListener.on_all_message 被调用，处理消息喵: {event.message_str} 📨"
            )

            # 获取消息平台名称，判断是否为 aiocqhttp喵～ 🤖
            # platform_name = event.get_platform_name()
            self.message_count += 1  # 获取已启用的任务喵～ ✅
            enabled_tasks = self.plugin.get_all_enabled_tasks()
            logger.debug(f"获取到 {len(enabled_tasks)} 个已启用任务喵～ 📊")

            # 优先使用事件的message_str属性喵～ 📝
            if not plain_text and hasattr(event.message_obj, "message_str"):
                plain_text = event.message_obj.message_str

            logger.debug(
                f'收到消息 [{event.get_sender_name()}]: "{plain_text}" (长度: {len(plain_text) if plain_text else 0}) 喵～ 📩'
            )

            # 如果还是没有文本内容，尝试从raw_message中获取喵～ 🔍
            if (
                not plain_text
                and hasattr(event.message_obj, "raw_message")
                and event.message_obj.raw_message
            ):
                # 尝试从raw_message中获取内容喵～ 📄

                try:
                    logger.debug(
                        f"从raw_message找到内容喵: {event.message_obj.raw_message} 📋"
                    )
                except Exception:
                    pass

            # 获取消息组件喵～ 🧩
            messages = event.get_messages()
            if (
                not messages
                and hasattr(event.message_obj, "message")
                and isinstance(event.message_obj.message, list)
            ):
                logger.warning("框架未处理message列表，直接进行处理喵 🔧")
                # 简单处理为文本消息喵～ 📝
                for msg_part in event.message_obj.message:
                    if (
                        msg_part.get("type") == "text"
                        and "data" in msg_part
                        and "text" in msg_part["data"]
                    ):
                        messages.append(Plain(text=msg_part["data"]["text"]))
                    elif msg_part.get("type") == "mface":
                        # 检测到特殊表情喵～ 😸
                        has_mface = True

            # 输出组件详情喵～ 📋
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
                logger.debug(f"消息组件喵: {' | '.join(components_info)} 🧩")

            # 强制检查消息原始数据 - 直接处理aicqhttp适配器转发的原始事件喵～ 🔍
            if hasattr(event.message_obj, "__dict__"):
                raw_obj = event.message_obj.__dict__
                # 直接检查是否有特殊表情相关结构喵～ 😸
                if "message" in raw_obj and isinstance(raw_obj["message"], list):
                    for msg in raw_obj["message"]:
                        if isinstance(msg, dict) and msg.get("type") == "mface":
                            has_mface = True
                            logger.warning(f"直接从__dict__找到mface喵: {msg} 😸")
                            # 提取数据喵～ 📊
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

            # 开始激进检测模式，查找所有可能的mface内容喵～ 🔍
            for attr_name in dir(event.message_obj):
                if not attr_name.startswith("_"):
                    try:
                        attr_value = getattr(event.message_obj, attr_name)
                        if "mface" in str(attr_value).lower():
                            has_mface = True
                            logger.warning(
                                f"从属性 {attr_name} 中发现mface内容喵: {attr_value} 😸"
                            )
                    except Exception:
                        pass

            # 开始针对每个任务进行处理喵～ 🎯
            task_matched = False
            for task in enabled_tasks:
                task_id = task.get("id")

                # 检查是否应该监听此消息喵～ 🔍
                should_monitor = self._should_monitor_message(task, event)
                should_monitor_user = self._should_monitor_user(task, event)
                should_monitor_group_user = self._should_monitor_group_user(task, event)

                logger.debug(f"任务 {task_id} 监听判断结果喵: 常规监听={should_monitor}, 用户监听={should_monitor_user}, 群内用户监听={should_monitor_group_user} 📊")

                if should_monitor or should_monitor_user or should_monitor_group_user:
                    task_matched = True
                    # 确保消息非空 - 优先使用各种方式确保获取到内容喵～ 📝
                    session_id = event.unified_msg_origin

                    # 重置特殊表情标记，单独检测每个任务喵～ 🔄
                    task_has_mface = has_mface

                    # 初始化缓存喵～ 💾
                    if task_id not in self.plugin.message_cache:
                        self.plugin.message_cache[task_id] = {}
                    if session_id not in self.plugin.message_cache[task_id]:
                        self.plugin.message_cache[task_id][session_id] = []

                    # 获取消息详情喵～ 📊
                    timestamp = int(time.time())
                    mface_components = [
                        msg for msg in serialized_messages if msg.get("is_mface")
                    ]

                    logger.debug(
                        f"详细消息对象喵: {event.message_obj.__dict__ if hasattr(event.message_obj, '__dict__') else 'No __dict__'} 📋"
                    )

                    # 序列化消息 - 保存之前已探测到的特殊表情喵～ 📦
                    task_serialized_messages = await async_serialize_message(
                        messages if messages else [], event
                    )

                    # 合并普通消息和特殊表情消息喵～ 🔗
                    for mface_msg in mface_components:
                        task_serialized_messages.append(mface_msg)

                    serialized_messages = task_serialized_messages

                    # 方法1: 直接从message属性获取喵～ 📋
                    if (
                        not task_has_mface
                        and hasattr(event.message_obj, "message")
                        and isinstance(event.message_obj.message, list)
                    ):
                        for msg in event.message_obj.message:
                            if isinstance(msg, dict) and msg.get("type") == "mface":
                                task_has_mface = True
                                logger.warning(f"从message列表找到mface喵: {msg} 😸")
                                # 提取数据喵～ 📊
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

                    # 方法2: 检查raw_message对象结构喵～ 🔍
                    if (
                        not task_has_mface
                        and hasattr(event.message_obj, "raw_message")
                        and event.message_obj.raw_message
                    ):
                        try:
                            raw_message = event.message_obj.raw_message
                            logger.warning(f"原始消息类型喵: {type(raw_message)} 📦")

                            if hasattr(raw_message, "message") and isinstance(
                                raw_message.message, list
                            ):
                                msg_list = raw_message.message
                            # 再尝试从raw_message字典中获取message列表喵～ 📚
                            elif (
                                isinstance(raw_message, dict)
                                and "message" in raw_message
                            ):
                                msg_list = raw_message["message"]
                            else:
                                msg_list = []

                            # 处理获取到的消息列表喵～ 📋
                            for raw_msg in msg_list:
                                # 处理图片消息并提取filename喵～ 🖼️
                                if (
                                    isinstance(raw_msg, dict)
                                    and raw_msg.get("type") == "image"
                                    and "data" in raw_msg
                                ):
                                    extracted_filename = raw_msg["data"].get("filename")
                                    if extracted_filename:
                                        logger.debug(
                                            f"从原始消息提取到filename喵: {extracted_filename} 📁"
                                        )
                                        # 在序列化消息中找到对应的图片并添加filename喵～ 🔗
                                        for i, msg in enumerate(serialized_messages):
                                            if msg.get("type") == "image":
                                                serialized_messages[i]["filename"] = (
                                                    extracted_filename
                                                )
                                                logger.debug(
                                                    f"已将filename {extracted_filename} 添加到图片消息喵～ ✅"
                                                )
                                                break

                                # 处理特殊表情(mface)喵～ 😸
                                elif (
                                    isinstance(raw_msg, dict)
                                    and raw_msg.get("type") == "mface"
                                ):
                                    task_has_mface = True
                                    logger.warning(
                                        f"从raw_message列表找到mface喵: {raw_msg} 😸"
                                    )
                                    # 提取表情数据喵～ 📊
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

                    # 检查消息长度限制并使用智能清理策略喵～ 🧠
                    max_messages = task.get(
                        "max_messages",
                        self.plugin.config.get("default_max_messages", 20),
                    )
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

                    # 应用智能缓存清理策略喵～ 🧠✨
                    self._smart_cache_cleanup(task_id, session_id, max_messages)

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

                # 为文件上传通知也应用智能缓存清理策略喵～ 🧠✨
                max_messages = task.get(
                    "max_messages",
                    self.plugin.config.get("default_max_messages", 20),
                )
                self._smart_cache_cleanup(task_id, session_id, max_messages)

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

        # 注意：群内特定用户监听由 _should_monitor_group_user 方法专门处理，
        # 这里只处理常规的群聊和私聊监听，不处理群内用户监听喵～ ⚠️

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
        """检查是否监听群内特定用户喵～ 🎯"""
        message_type_name = event.get_message_type().name
        group_id = event.get_group_id()
        session_id = event.unified_msg_origin
        sender_id = event.get_sender_id()

        # 只处理群消息
        if message_type_name != "GROUP_MESSAGE":
            logger.debug(f"非群消息 ({message_type_name})，跳过群内用户监听检查喵～")
            return False

        group_id_str = str(group_id)
        sender_id_str = str(sender_id)

        logger.debug(f"检查群内用户监听喵: 群{group_id_str}, 用户{sender_id_str}, 会话{session_id} 🔍")

        # 重要修改：同时检查纯群号和完整会话ID两种格式
        monitored_users = task.get("monitored_users_in_groups", {}).get(
            group_id_str, []
        )

        # 如果纯群号没找到，尝试使用完整会话ID
        if not monitored_users:
            monitored_users = task.get("monitored_users_in_groups", {}).get(
                session_id, []
            )
            if monitored_users:
                logger.debug(f"在完整会话ID {session_id} 中找到用户监听配置喵 📋")
            else:
                logger.debug(f"群 {group_id_str} 或会话 {session_id} 没有配置特定用户监听喵 ❌")

        # 如果没有指定用户列表，则不监听任何人
        if not monitored_users:
            logger.debug(f"群 {group_id_str} 没有配置特定用户监听，跳过喵～ ⏭️")
            return False

        logger.debug(f"群 {group_id_str} 的监听用户列表喵: {monitored_users} 👥")

        # 检查当前发送者是否在监听列表中
        is_monitored = sender_id_str in [str(uid) for uid in monitored_users]

        if is_monitored:
            logger.info(f"✅ 群 {group_id_str} 中的用户 {sender_id_str} 在监听列表中，应该监听此消息喵！ 🎯")
        else:
            logger.debug(f"❌ 群 {group_id_str} 中的用户 {sender_id_str} 不在监听列表中，跳过此消息喵～ ⏭️")

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

            # 注意：群内用户监听由 _should_monitor_group_user 方法专门处理，
            # 这里不处理群内用户监听配置喵～ ⚠️
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

    def _is_empty_message(self, cached_message: dict) -> bool:
        """
        检测消息是否为空消息（如群文件上传通知）喵～ 🔍

        Args:
            cached_message: 缓存的消息字典喵

        Returns:
            如果是空消息返回True，否则返回False喵
        """
        try:
            messages = cached_message.get("messages", [])

            # 如果没有消息组件，肯定是空消息喵～
            if not messages:
                return True

            # 检查是否只包含群文件上传通知喵～
            for msg in messages:
                if isinstance(msg, dict):
                    msg_type = msg.get("type")
                    notice_type = msg.get("notice_type")

                    # 群文件上传通知被认为是空消息喵～
                    if msg_type == "notice" and notice_type == "group_upload":
                        continue
                    else:
                        # 如果有其他类型的消息，就不是空消息喵～
                        return False
                else:
                    # 如果有非字典的消息，就不是空消息喵～
                    return False

            # 如果只有群文件上传通知，就是空消息喵～
            return True

        except Exception as e:
            # 出错时保守处理，认为不是空消息喵～
            logger.debug(f"检测空消息时出错喵: {e}")
            return False

    def _smart_cache_cleanup(self, task_id: str, session_id: str, max_messages: int):
        """
        智能清理缓存策略喵～ 🧠✨
        优先删除空消息，然后删除旧的有效消息，确保有效消息数量符合阈值要求喵！

        Args:
            task_id: 任务ID喵
            session_id: 会话ID喵
            max_messages: 消息阈值喵
        """
        try:
            cache = self.plugin.message_cache[task_id][session_id]
            cache_capacity = max(max_messages * 3, 20)  # 缓存容量 = 阈值 × 3，最小20喵

            logger.debug(f"开始智能缓存清理检查喵: 当前缓存 {len(cache)}，容量限制 {cache_capacity}，阈值 {max_messages}")

            # 分类消息：有效消息和空消息喵～
            valid_messages = []
            empty_messages = []

            for msg in cache:
                if self._is_empty_message(msg):
                    empty_messages.append(msg)
                else:
                    valid_messages.append(msg)

            logger.debug(f"消息分类结果喵: 有效消息 {len(valid_messages)}，空消息 {len(empty_messages)}")

            removed_count = 0

            # 第一步：清理所有空消息（但保留一些以免丢失上下文）喵～
            if len(empty_messages) > 2:  # 最多保留2条空消息作为上下文喵～
                empty_to_remove = len(empty_messages) - 2
                # 按时间戳排序，删除最老的空消息喵～
                empty_messages.sort(key=lambda x: x.get("timestamp", 0))
                for i in range(empty_to_remove):
                    cache.remove(empty_messages[i])
                    removed_count += 1

                logger.debug(f"删除了 {empty_to_remove} 条空消息喵～")

            # 第二步：如果缓存超过容量限制，删除旧的有效消息喵～
            if len(cache) > cache_capacity:
                need_to_remove = len(cache) - cache_capacity

                # 重新获取当前缓存中的有效消息喵～
                current_valid = []
                for msg in cache:
                    if not self._is_empty_message(msg):
                        current_valid.append(msg)

                # 确保删除后有效消息数量不少于阈值喵～
                can_remove = max(0, len(current_valid) - max_messages)
                actual_remove = min(need_to_remove, can_remove)

                if actual_remove > 0:
                    # 按时间戳排序，删除最老的有效消息喵～
                    current_valid.sort(key=lambda x: x.get("timestamp", 0))
                    for i in range(actual_remove):
                        cache.remove(current_valid[i])
                        removed_count += 1

                    logger.debug(f"删除了 {actual_remove} 条旧的有效消息喵～")

            if removed_count > 0:
                logger.info(f"智能缓存清理完成喵: 删除了 {removed_count} 条消息，当前缓存 {len(cache)} 条")

        except Exception as e:
            logger.error(f"智能缓存清理时出错喵: {e}")
