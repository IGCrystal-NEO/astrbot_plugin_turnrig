#!/usr/bin/env python3
"""
麦咪的数字占卜脚本 🔮
每小时为项目带来新的运势喵～
"""

import datetime
import hashlib
import random


def get_seed():
    """基于当前小时生成种子，确保同一小时内结果一致"""
    now = datetime.datetime.now()
    # 使用年月日小时作为种子，确保每小时更新
    seed_str = f"{now.year}{now.month:02d}{now.day:02d}{now.hour:02d}"
    return int(hashlib.md5(seed_str.encode()).hexdigest()[:8], 16)


def get_fortune():
    """获取当前时刻的运势"""
    seed = get_seed()
    random.seed(seed)

    # 运势等级
    fortune_levels = [
        "🌟 超级幸运",
        "✨ 非常幸运",
        "🍀 比较幸运",
        "😊 小幸运",
        "😐 平平无奇",
        "😅 需要加油",
        "🤔 要小心喵",
    ]

    # 幸运数字 (1-99)
    lucky_number = random.randint(1, 99)

    # 幸运颜色
    lucky_colors = [
        "💙 蓝色",
        "💚 绿色",
        "💜 紫色",
        "❤️ 红色",
        "💛 黄色",
        "🧡 橙色",
        "🤍 白色",
        "🖤 黑色",
        "💗 粉色",
        "🤎 棕色",
        "💎 银色",
        "✨ 金色",
    ]

    # 今日建议
    daily_tips = [
        "今天适合写代码喵～记得多喝水哦",
        "今天是修复bug的好日子喵～",
        "适合学习新技术的一天喵～",
        "今天要记得休息，不要熬夜喵～",
        "适合整理代码和文档的日子喵～",
        "今天可能会有意外的收获喵～",
        "记得备份重要数据喵～",
        "今天适合和朋友交流技术喵～",
        "保持好心情，bug都会迎刃而解喵～",
        "今天的灵感特别多，快去创造吧喵～",
        "适合重构代码的一天喵～",
        "记得关注项目的star数喵～",
    ]

    # 特殊事件 (低概率)
    special_events = [
        "🎉 今天可能会有特别的好消息喵～",
        "🌈 今天是充满彩虹般美好的一天喵～",
        "🎊 今天适合庆祝小成就喵～",
        "🔥 今天的工作效率会特别高喵～",
        "💫 今天可能会遇到贵人相助喵～",
    ]

    level = random.choice(fortune_levels)
    color = random.choice(lucky_colors)
    tip = random.choice(daily_tips)

    # 15%概率触发特殊事件
    special = random.choice(special_events) if random.random() < 0.15 else None

    # 生成时间戳
    now = datetime.datetime.now()
    timestamp = now.strftime("%Y-%m-%d %H:%M")

    # 格式化输出
    fortune_text = f"""## 🔮 麦咪的数字占卜 ({timestamp})

**{level}** ✨

🎯 **幸运数字**: {lucky_number}
🎨 **幸运颜色**: {color}
💡 **今日建议**: {tip}"""

    if special:
        fortune_text += f"\n🌟 **特殊预言**: {special}"

    fortune_text += "\n\n*每小时更新一次，仅供娱乐喵～* 🐱"

    return fortune_text


if __name__ == "__main__":
    print(get_fortune())
