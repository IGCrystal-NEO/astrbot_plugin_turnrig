# 导入消息工具模块喵～ 📦
from astrbot.api import logger


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
