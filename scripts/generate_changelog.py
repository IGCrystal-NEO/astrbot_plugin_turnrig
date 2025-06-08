#!/usr/bin/env python3
"""
Changelog 生成脚本
用于根据 Git 提交记录自动生成 changelog 条目
"""

import subprocess
import re
import sys
from datetime import datetime
from typing import List, Dict
from pathlib import Path


class ChangelogGenerator:
    """Changelog 生成器"""
      # 提交类型映射到 changelog 分类
    COMMIT_TYPE_MAP = {
        'feat': 'Added',
        'add': 'Added',
        'feature': 'Added',
        'fix': 'Fixed',
        'bugfix': 'Fixed',
        'perf': 'Changed',
        'refactor': 'Changed',
        'docs': 'Changed',
        'style': 'Changed',
        'test': 'Changed',
        'chore': 'Changed',
        'remove': 'Removed',
        'deprecate': 'Deprecated',
        'security': 'Security',
        'revert': 'Reverted',
        'ci': 'Run'
    }
    
    def __init__(self):
        self.changes: Dict[str, List[str]] = {
            'Added': [],
            'Changed': [],
            'Deprecated': [],
            'Removed': [],
            'Fixed': [],
            'Security': [],
            'Run': []  # 添加 Run 分类用于 CI 相关提交
        }
        
    def get_latest_tag(self) -> str:
        """获取最新的 Git 标签"""
        try:
            result = subprocess.run(
                ["git", "describe", "--tags", "--abbrev=0"],
                capture_output=True,
                text=True,
                check=True,
                encoding='utf-8'
            )
            if result.stdout:
                return result.stdout.strip()
            return None
        except subprocess.CalledProcessError:
            # 如果没有标签，返回 None
            return None
    def get_git_commits(self, from_tag: str = None, to_tag: str = "HEAD") -> List[str]:
        """获取 Git 提交记录"""
        if from_tag == "--all":
            # 特殊参数：获取所有提交（用于初始版本）
            cmd = f"git log --oneline {to_tag}"
            print(f"📋 生成初始版本 changelog：包含所有提交到 {to_tag}")
        elif from_tag:
            cmd = f"git log --oneline {from_tag}..{to_tag}"
            print(f"📋 基于标签 {from_tag} 到 {to_tag} 生成 changelog")
        else:
            # 如果没有指定 from_tag，尝试获取最新标签
            latest_tag = self.get_latest_tag()
            if latest_tag:
                # 检查是否有新的提交
                cmd_check = f"git log --oneline {latest_tag}..{to_tag}"
                try:
                    result_check = subprocess.run(
                        cmd_check.split(),
                        capture_output=True,
                        text=True,
                        check=True,
                        encoding='utf-8'
                    )
                    if result_check.stdout.strip():
                        cmd = cmd_check
                        print(f"📋 自动检测：基于标签 {latest_tag} 到 {to_tag} 生成 changelog")
                    else:
                        # 如果没有新提交，获取最近10个提交作为示例
                        cmd = f"git log --oneline -10"
                        print(f"📋 警告：{latest_tag} 到 {to_tag} 之间没有新提交，使用最近10个提交")
                except subprocess.CalledProcessError:
                    cmd = f"git log --oneline -20"
                    print("📋 Git命令执行失败，使用最近20个提交")
            else:
                cmd = f"git log --oneline -20"  # 如果没有标签，获取最近20个提交
                print("📋 没有找到Git标签，基于最近20个提交生成 changelog")

        try:
            result = subprocess.run(
                cmd.split(),
                capture_output=True,
                text=True,
                check=True,
                encoding='utf-8'
            )
            if result.stdout:
                commits = result.stdout.strip().split('\n')
                # 过滤空行
                commits = [c for c in commits if c.strip()]
                print(f"📊 找到 {len(commits)} 个提交")
                return commits
            else:
                print("📊 没有找到新的提交")
                return []
        except subprocess.CalledProcessError as e:
            print(f"Error: 无法获取 Git 提交记录: {e}")
            return []
        except UnicodeDecodeError:
            # 尝试使用系统默认编码
            try:
                result = subprocess.run(cmd.split(), capture_output=True, check=True)
                if result.stdout:
                    output = result.stdout.decode('utf-8', errors='ignore')
                    commits = output.strip().split('\n')
                    commits = [c for c in commits if c.strip()]
                    return commits
                return []
            except Exception as e:
                print(f"Error: 无法获取 Git 提交记录: {e}")
                return []

    def parse_commit_message(self, commit_line: str) -> tuple:
        """解析提交信息"""
        # 提取提交哈希和消息
        parts = commit_line.split(' ', 1)
        if len(parts) < 2:
            return None, None, None
        
        commit_hash = parts[0]
        message = parts[1]
        
        # 匹配常见的提交格式
        patterns = [
            r'([🎈🐞📃🤖✨🎉🌈🐎🧪🔧🐋🦄]\s*)?(\w+):\s*(.+)',  # emoji + type: message
            r'(\w+):\s*(.+)',                    # type: message
            r'(\w+)\s*-\s*(.+)',                 # type - message
            r'(\w+)\s+(.+)',                     # type message
        ]
        
        commit_type = None
        description = message
        
        for pattern in patterns:
            match = re.match(pattern, message, re.IGNORECASE)
            if match:
                if len(match.groups()) == 3:  # 有 emoji
                    commit_type = match.group(2).lower()
                    description = match.group(3)
                else:  # 没有 emoji
                    commit_type = match.group(1).lower()
                    description = match.group(2)
                break
        
        return commit_hash, commit_type, description
    
    def categorize_commit(self, commit_type: str, description: str):
        """将提交分类到相应的 changelog 分类"""
        if not commit_type or not description:
            return
        
        # 查找匹配的分类
        category = None
        for key, value in self.COMMIT_TYPE_MAP.items():
            if commit_type.startswith(key):
                category = value
                break
        
        if not category:
            category = 'Changed'  # 默认分类
        
        # 清理描述信息
        description = description.strip()
        if description and description not in self.changes[category]:
            self.changes[category].append(description)
    def generate_changelog_section(self, version: str, date: str = None) -> str:
        """生成 changelog 部分"""
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        
        lines = [f"## [{version}] - {date}", ""]
        
        # 检查是否有任何变更
        has_changes = any(self.changes[category] for category in self.changes)
        if not has_changes:
            lines.append("### Changed")
            lines.append("- No significant changes in this version")
            lines.append("")
            return '\n'.join(lines)
        
        # 按顺序添加各个分类
        for category in ['Added', 'Changed', 'Deprecated', 'Removed', 'Fixed', 'Security']:
            if self.changes[category]:
                lines.append(f"### {category}")
                for change in self.changes[category]:
                    lines.append(f"- {change}")
                lines.append("")
        
        return '\n'.join(lines)
    
    def process_commits(self, from_tag: str = None, to_tag: str = "HEAD"):
        """处理提交记录"""
        commits = self.get_git_commits(from_tag, to_tag)
        
        for commit_line in commits:
            if not commit_line.strip():
                continue
            
            commit_hash, commit_type, description = self.parse_commit_message(commit_line)
            self.categorize_commit(commit_type, description)
    
    def generate(self, version: str, from_tag: str = None, to_tag: str = "HEAD") -> str:
        """生成 changelog"""
        self.process_commits(from_tag, to_tag)
        return self.generate_changelog_section(version)
    def update_changelog_file(self, version: str, changelog_section: str, file_path: str = "CHANGELOG.md") -> bool:
        """将生成的 changelog 更新到 CHANGELOG.md 文件中"""
        try:
            # 如果是相对路径，则相对于项目根目录（脚本的上级目录）
            if not Path(file_path).is_absolute():
                script_dir = Path(__file__).parent
                project_root = script_dir.parent
                file_path = project_root / file_path
            changelog_path = Path(file_path)
            if not changelog_path.exists():
                print(f"警告: {file_path} 文件不存在，创建新文件")
                changelog_path.write_text(
                    "# Changelog\n\n"
                    "All notable changes to this project will be documented in this file.\n\n"
                    "## [Unreleased]\n\n"
                    + changelog_section + "\n",
                    encoding='utf-8'
                )
                return True
            
            # 读取现有文件
            content = changelog_path.read_text(encoding='utf-8')
            
            # 检查版本是否已经存在
            version_pattern = rf'## \[{re.escape(version)}\]'
            if re.search(version_pattern, content):
                print(f"⚠️  版本 {version} 已存在于 {file_path} 中")
                user_input = input("是否要覆盖现有版本？(y/N): ").strip().lower()
                if user_input not in ['y', 'yes']:
                    print("❌ 操作已取消")
                    return False
                
                # 删除现有版本
                # 匹配整个版本块（从 ## [version] 到下一个 ## [ 或文件结束）
                version_block_pattern = rf'(## \[{re.escape(version)}\].*?)(?=\n## \[|\n<!--|\Z)'
                content = re.sub(version_block_pattern, '', content, flags=re.DOTALL)
                content = re.sub(r'\n\n\n+', '\n\n', content)  # 清理多余的空行
            
            # 查找 [Unreleased] 部分
            unreleased_pattern = r'(## \[Unreleased\].*?)(\n## \[|$)'
            match = re.search(unreleased_pattern, content, re.DOTALL)
            
            if match:
                # 在 [Unreleased] 部分后插入新版本
                before_unreleased = content[:match.end(1)]
                after_unreleased = content[match.start(2):]
                
                new_content = before_unreleased + "\n\n" + changelog_section + "\n" + after_unreleased
            else:
                # 如果找不到 [Unreleased] 部分，在文件末尾添加
                new_content = content + "\n\n" + changelog_section + "\n"
            # 写入文件
            changelog_path.write_text(new_content, encoding='utf-8')
            print(f"✅ 成功更新 {file_path}")
            return True
            
        except Exception as e:
            print(f"❌ 更新 {file_path} 失败: {e}")
            return False

    def update_metadata_version(self, version: str, file_path: str = "metadata.yaml") -> bool:
        """更新 metadata.yaml 中的版本号"""
        try:
            # 如果是相对路径，则相对于项目根目录（脚本的上级目录）
            if not Path(file_path).is_absolute():
                script_dir = Path(__file__).parent
                project_root = script_dir.parent
                file_path = project_root / file_path
            metadata_path = Path(file_path)
            if not metadata_path.exists():
                print(f"警告: {file_path} 文件不存在")
                return False
            content = metadata_path.read_text(encoding='utf-8')
            # 更严格的版本字段匹配，支持带引号和不带引号的格式
            version_patterns = [
                r'version:\s*["\']?v?[^"\']*["\']?',  # 匹配 version: "v1.2.0" 或 version: v1.2.0
                r'version:\s*["\'][^"\']*["\']',      # 匹配带引号的版本
                r'version:\s*[^\s#]+',                # 匹配不带引号的版本
            ]
            
            new_content = content
            for pattern in version_patterns:
                if re.search(pattern, content):
                    new_content = re.sub(pattern, f'version: "{version}"', content)
                    break
            
            if new_content != content:
                metadata_path.write_text(new_content, encoding='utf-8')
                print(f"✅ 成功更新 {file_path} 版本号为 {version}")
                return True
            else:
                print(f"警告: 在 {file_path} 中未找到版本字段")
                return False
                
        except Exception as e:
            print(f"❌ 更新 {file_path} 失败: {e}")
            return False


def main():
    """主函数"""
    if len(sys.argv) < 2:        
        print("Usage: python generate_changelog.py <version> [from_tag] [to_tag] [--preview/-p]")
        print("Examples:")
        print("  python generate_changelog.py 1.3.0                    # 自动检测最新标签")
        print("  python generate_changelog.py 1.3.0 v1.2.0 HEAD       # 指定版本范围")
        print("  python generate_changelog.py 1.3.0 --all v1.0.0      # 为初始版本生成（从项目开始到指定标签）")
        print("  python generate_changelog.py 1.3.0 --preview          # 只预览不写入")
        print("  python generate_changelog.py 1.3.0 v1.2.0 HEAD -p    # 指定范围并预览")
        print("\n⚠️  重要提示:")
        print("  - 如果版本内容重复，请手动指定 from_tag 参数")
        print("  - 对于初始版本，使用 --all 参数")
        print("  - 推荐先使用 --preview 查看生成内容")
        sys.exit(1)

    version = sys.argv[1]
    from_tag = None
    to_tag = "HEAD"
    preview_only = False
    
    # 解析参数
    for i, arg in enumerate(sys.argv[2:], 2):
        if arg in ['--preview', '-p']:
            preview_only = True
        elif i == 2 and not arg.startswith('--'):
            from_tag = arg
        elif i == 3 and not arg.startswith('--'):
            to_tag = arg

    generator = ChangelogGenerator()
    changelog_section = generator.generate(version, from_tag, to_tag)

    if preview_only:
        # 只预览，不写入文件
        print("\nGenerated changelog section (preview only):")
        print("=" * 50)
        print(changelog_section)
        print("=" * 50)
        if from_tag:
            print(f"\n💡 要写入文件，请运行: python generate_changelog.py {version} {from_tag} {to_tag}")
        else:
            print(f"\n💡 要写入文件，请运行: python generate_changelog.py {version}")
    else:
        # 默认直接写入文件
        print(f"\n🚀 正在将版本 {version} 的 changelog 写入文件...")
        
        success = generator.update_changelog_file(version, changelog_section)
        if success:
            # 同时更新 metadata.yaml 版本号
            generator.update_metadata_version(version)
            print(f"\n✅ 版本 {version} 的 changelog 已成功写入!")
            print("📝 CHANGELOG.md 和 metadata.yaml 已更新")            
            print(f"\n🎉 下一步操作:")
            print(f"   git add .")
            print(f"   git commit -m \"📃 docs: release {version}\"")
            print(f"   git tag {version}")
            print(f"   git push && git push --tags")
        else:
            print("\n❌ 写入失败，请检查文件权限和路径")


if __name__ == "__main__":
    main()
