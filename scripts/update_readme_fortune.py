#!/usr/bin/env python3
"""
更新README中的占卜内容
"""

import os
import sys

from fortune_teller import get_fortune


def update_readme():
    """更新README.md中的占卜内容"""
    readme_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "README.md")

    if not os.path.exists(readme_path):
        print("README.md not found!")
        return False

    # 读取当前README内容
    with open(readme_path, encoding="utf-8") as f:
        content = f.read()

    # 获取新的占卜内容
    fortune = get_fortune()

    # 定义标记位置
    start_marker = "> 一个消息监听与转发插件，支持多种消息类型"
    fortune_start = "## 🔮 麦咪的数字占卜"

    # 查找插入位置
    start_pos = content.find(start_marker)
    if start_pos == -1:
        print("Could not find insertion marker in README.md")
        return False

    # 查找占卜内容的结束位置
    insertion_pos = start_pos + len(start_marker)

    # 检查是否已经存在占卜内容
    fortune_pos = content.find(fortune_start, insertion_pos)
    if fortune_pos != -1:
        # 找到下一个 ## 标题的位置作为结束位置
        next_section = content.find("\n## ", fortune_pos + 1)
        if next_section == -1:
            # 如果没有找到下一个标题，查找其他可能的结束标记
            end_markers = ["\n# ", "\n##", "\n### "]
            for marker in end_markers:
                marker_pos = content.find(marker, fortune_pos + 1)
                if marker_pos != -1:
                    next_section = marker_pos
                    break

        if next_section != -1:
            # 删除旧的占卜内容
            content = content[:fortune_pos] + content[next_section:]
        else:
            # 如果找不到结束位置，删除到文件末尾（这种情况不太可能）
            content = content[:fortune_pos]

        # 重新计算插入位置
        insertion_pos = start_pos + len(start_marker)

    # 插入新的占卜内容
    new_content = (
        content[:insertion_pos] + "\n\n" + fortune + "\n" + content[insertion_pos:]
    )

    # 写入更新后的内容
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    print("README.md updated successfully with new fortune!")
    return True


if __name__ == "__main__":
    success = update_readme()
    sys.exit(0 if success else 1)
