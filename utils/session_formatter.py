import re

from astrbot.api import logger


def normalize_session_id(session_id):
    """标准化会话ID格式"""
    # 处理简化输入 - 群聊/私聊关键字处理
    if (
        session_id.startswith("群聊 ")
        or session_id.startswith("群聊：")
        or session_id.startswith("群聊:")
    ):
        group_id = (
            session_id.split(" ", 1)[1].strip().split("：", 1)[-1].split(":", 1)[-1]
        )
        return f"aiocqhttp:GroupMessage:{group_id}"

    if (
        session_id.startswith("私聊 ")
        or session_id.startswith("私聊：")
        or session_id.startswith("私聊:")
    ):
        user_id = (
            session_id.split(" ", 1)[1].strip().split("：", 1)[-1].split(":", 1)[-1]
        )
        return f"aiocqhttp:FriendMessage:{user_id}"

    # 纯数字ID处理 - 现在不再自动推断，而是给出明确的警告
    if session_id.isdigit():
        logger.warning(
            f"收到纯数字ID: {session_id}，现在只支持完整会话ID格式。请使用'群聊 {session_id}'或'私聊 {session_id}'格式，或者直接使用完整的会话ID"
        )
        logger.warning(
            f"例如: aiocqhttp:GroupMessage:{session_id} 或 aiocqhttp:FriendMessage:{session_id}"
        )
        return session_id  # 返回原始ID，但可能不能正确匹配

    # 如果会话ID已经是正确格式（platform:type:id），则直接返回
    if re.match(r"^[^:]+:[^:]+:[^:]+$", session_id):
        # 标准化消息类型格式
        parts = session_id.split(":", 2)
        platform, msg_type, id_part = parts

        # 规范化消息类型
        if "group" in msg_type.lower():
            msg_type = "GroupMessage"
        elif "private" in msg_type.lower() or "friend" in msg_type.lower():
            msg_type = "FriendMessage"

        return f"{platform}:{msg_type}:{id_part}"

    # 处理平台:ID格式 - 现在不再自动推断，给出明确的警告
    if ":" in session_id and len(session_id.split(":")) == 2:
        logger.warning(
            f"会话ID '{session_id}' 格式不完整，需要三段式格式: platform:type:id"
        )
        logger.warning(
            "例如: aiocqhttp:GroupMessage:123456 或 aiocqhttp:FriendMessage:123456"
        )

    logger.warning(f"无法识别会话ID格式: {session_id}，请使用完整的会话ID格式")
    return session_id
