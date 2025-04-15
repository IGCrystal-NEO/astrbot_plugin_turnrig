from astrbot.api import logger

async def fetch_message_detail(message_id, event):
    """获取消息详情喵～参考了搬史插件的实现"""
    if event.get_platform_name() != "aiocqhttp":
        return None

    try:
        client = event.bot
        # 获取消息详情
        payload = {
            "message_id": message_id
        }
        response = await client.api.call_action("get_msg", **payload)
        logger.debug(f"获取到消息详情: {response}")
        
        # 如果是转发消息，尝试获取转发消息的内容
        if response and "message" in response:
            message_list = response["message"]
            if isinstance(message_list, list) and len(message_list) > 0:
                first_segment = message_list[0]
                if isinstance(first_segment, dict) and first_segment.get("type") == "forward":
                    # 这是一个转发消息，尝试获取其内容
                    forward_id = first_segment.get("data", {}).get("id", "")
                    if forward_id:
                        forward_payload = {
                            "message_id": forward_id
                        }
                        try:
                            forward_response = await client.api.call_action("get_forward_msg", **forward_payload)
                            # 将转发消息的内容添加到原始响应中
                            response["forward_content"] = forward_response
                            logger.debug(f"获取到转发消息内容: {forward_response}")
                        except Exception as e:
                            logger.warning(f"获取转发消息内容失败: {e}")
        
        return response
    except Exception as e:
        logger.error(f"获取消息详情失败喵: {e}")
        return None

async def fetch_emoji_reactions(message_id, event):
    """获取消息表情回应喵～此功能已禁用，返回空数据"""
    # 直接返回空字典，不再获取表情回应
    return {}