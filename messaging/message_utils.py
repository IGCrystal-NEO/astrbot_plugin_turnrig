# 导入消息工具模块喵～ 📦
import time

from astrbot.api import logger


async def fetch_forward_message_nodes(forward_id, event):
    """
    获取转发消息的节点内容喵～ 📤
    将转发消息转换为可用于构建新转发消息的节点格式！

    Args:
        forward_id: 转发消息ID喵
        event: 消息事件对象喵

    Returns:
        list: 转发消息节点列表，失败时返回None喵～

    Note:
        返回的节点可以直接用于构建新的转发消息喵！ ✨
    """
    if event.get_platform_name() != "aiocqhttp":
        logger.warning(f"平台 {event.get_platform_name()} 不支持转发消息获取喵 😿")
        return None

    if not forward_id:
        logger.warning("转发消息ID为空，无法获取内容喵 😿")
        return None

    try:
        client = event.bot
        logger.info(f"尝试获取转发消息内容喵: ID={forward_id} 🔍")

        # 方法1: 尝试使用get_forward_msg API喵～ 📤
        forward_payload = {"id": forward_id}
        try:
            forward_response = await client.api.call_action(
                "get_forward_msg", **forward_payload
            )
            logger.info(f"成功通过get_forward_msg获取转发消息喵: {forward_response} ✅")

            if not forward_response:
                logger.warning(f"get_forward_msg返回空结果喵: {forward_response} 😿")
                return None

            # 检查是否有message字段喵～ 📋
            if "message" in forward_response and isinstance(
                forward_response["message"], list
            ):
                messages = forward_response["message"]
                logger.info(f"从get_forward_msg获取到 {len(messages)} 条消息喵 📊")

                # 转换为节点格式喵～ 🔄
                nodes = []
                for i, msg in enumerate(messages):
                    if not isinstance(msg, dict):
                        logger.debug(f"跳过非字典格式的消息 {i}: {type(msg)} 📦")
                        continue

                    # 检查是否是node类型的消息喵～ 🎯
                    if msg.get("type") == "node" and "data" in msg:
                        # 直接使用OneBot返回的节点数据喵～ 📤
                        node_data = msg["data"]

                        # 构建标准化节点数据喵～ 🏗️
                        node = {
                            "type": "node",
                            "data": {
                                "name": node_data.get("nickname", "未知用户"),
                                "uin": str(node_data.get("user_id", "0")),
                                "content": node_data.get("content", []),
                                "time": node_data.get("time", int(time.time())),
                            },
                        }

                        logger.info(
                            f"处理节点 {i + 1}: 用户={node['data']['name']}, 内容数量={len(node['data']['content'])} 📋"
                        )
                        nodes.append(node)
                    else:
                        # 兼容旧格式，构建节点数据喵～ 🔄
                        node = {
                            "type": "node",
                            "data": {
                                "name": msg.get(
                                    "nickname",
                                    msg.get("sender", {}).get("nickname", "未知用户"),
                                ),
                                "uin": str(
                                    msg.get(
                                        "user_id",
                                        msg.get("sender", {}).get("user_id", "0"),
                                    )
                                ),
                                "content": [],
                                "time": msg.get("time", int(time.time())),
                            },
                        }

                        # 处理消息内容喵～ 📝
                        content_processed = False

                        # 尝试从content字段获取消息内容喵～ 🔍
                        if "content" in msg and isinstance(msg["content"], list):
                            for content_item in msg["content"]:
                                if isinstance(content_item, dict):
                                    content_type = content_item.get("type", "")
                                    if content_type == "text":
                                        text_content = content_item.get("data", {}).get(
                                            "text", ""
                                        )
                                        if text_content:
                                            node["data"]["content"].append(
                                                {
                                                    "type": "text",
                                                    "data": {"text": text_content},
                                                }
                                            )
                                            content_processed = True
                                    elif content_type == "image":
                                        node["data"]["content"].append(
                                            {
                                                "type": "image",
                                                "data": content_item.get("data", {}),
                                            }
                                        )
                                        content_processed = True
                                    else:
                                        # 保持原始格式喵～ 📦
                                        node["data"]["content"].append(content_item)
                                        content_processed = True

                        # 尝试从message字段获取消息内容喵～ 🔍
                        if not content_processed and "message" in msg:
                            message_content = msg["message"]
                            if isinstance(message_content, list):
                                for msg_part in message_content:
                                    if isinstance(msg_part, dict):
                                        if msg_part.get("type") == "text":
                                            text_content = msg_part.get("data", {}).get(
                                                "text", ""
                                            )
                                            if text_content:
                                                node["data"]["content"].append(
                                                    {
                                                        "type": "text",
                                                        "data": {"text": text_content},
                                                    }
                                                )
                                                content_processed = True
                                    else:
                                        node["data"]["content"].append(msg_part)
                                        content_processed = True
                            elif isinstance(message_content, str) and message_content:
                                node["data"]["content"].append(
                                    {"type": "text", "data": {"text": message_content}}
                                )
                                content_processed = True

                        # 如果仍然没有内容，添加默认文本喵～ 📝
                        if not content_processed:
                            node["data"]["content"].append(
                                {"type": "text", "data": {"text": "[消息内容无法解析]"}}
                            )

                        nodes.append(node)

                if nodes:
                    logger.info(f"成功转换转发消息为 {len(nodes)} 个节点喵 ✅")
                    return nodes
                else:
                    logger.warning("转发消息转换后没有有效节点喵 😿")
                    return None
            else:
                logger.warning(
                    f"get_forward_msg响应格式不正确喵: {forward_response} 😿"
                )
                return None

        except Exception as api_error:
            logger.error(f"调用get_forward_msg API失败喵: {api_error} 😿")
            # API失败时直接返回None，让上层决定如何处理喵～ 📝
            return None

    except Exception as e:
        logger.error(f"获取转发消息节点失败喵: {e} 😿")
        return None


async def fetch_message_detail(message_id, event):
    """
    获取消息详情喵～ 📄
    参考了搬史插件的实现，支持普通消息和转发消息！

    Args:
        message_id: 消息ID喵
        event: 消息事件对象喵

    Returns:
        dict | None: 消息详情数据，失败时返回None喵～

    Note:
        会自动检测并获取转发消息的完整内容喵！ ✨
    """
    if event.get_platform_name() != "aiocqhttp":
        return None

    try:
        client = event.bot
        # 获取消息详情喵～ 🔍
        payload = {"message_id": message_id}
        response = await client.api.call_action("get_msg", **payload)
        logger.debug(f"获取到消息详情喵: {response} 📋")

        # 如果是转发消息，尝试获取转发消息的内容喵～ 📤
        if response and "message" in response:
            message_list = response["message"]
            if isinstance(message_list, list) and len(message_list) > 0:
                first_segment = message_list[0]
                if (
                    isinstance(first_segment, dict)
                    and first_segment.get("type") == "forward"
                ):
                    # 这是一个转发消息，尝试获取其内容喵～ 📨
                    forward_id = first_segment.get("data", {}).get("id", "")
                    if forward_id:
                        forward_payload = {"message_id": forward_id}
                        try:
                            forward_response = await client.api.call_action(
                                "get_forward_msg", **forward_payload
                            )
                            # 将转发消息的内容添加到原始响应中喵～ 📝
                            response["forward_content"] = forward_response
                            logger.debug(f"获取到转发消息内容喵: {forward_response} ✨")
                        except Exception as e:
                            logger.warning(f"获取转发消息内容失败喵: {e} 😿")

        return response
    except Exception as e:
        logger.error(f"获取消息详情失败喵: {e} 😿")
        return None


async def fetch_emoji_reactions(message_id, event):
    """
    获取消息表情回应喵～ 😊
    此功能已禁用，返回空数据！

    Args:
        message_id: 消息ID喵
        event: 消息事件对象喵

    Returns:
        dict: 空字典，表情回应功能已禁用喵～

    Note:
        为了兼容性保留此方法，但不再获取实际数据喵！ 💫
    """
    # 直接返回空字典，不再获取表情回应喵～ 📦
    return {}
