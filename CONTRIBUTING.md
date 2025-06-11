# 🎀 贡献指南 - Contributing Guide

感谢你对麦咪的转发插件感兴趣喵♡～ 欢迎加入我们的开发者大家庭！✨

## 📋 目录

- [开始之前](#开始之前)
- [代码风格](#代码风格)
- [开发流程](#开发流程)
- [提交规范](#提交规范)
- [测试要求](#测试要求)
- [文档更新](#文档更新)
- [社区准则](#社区准则)

## 🌟 开始之前

### 📚 了解项目
在开始贡献之前，请确保你已经：
- 阅读了 [README.md](README.md) 了解项目功能
- 查看了 [CHANGELOG.md](CHANGELOG.md) 了解项目历史
- 浏览了现有的 [Issues](https://github.com/WentUrc/astrbot_plugin_turnrig/issues) 和 [Discussions](https://github.com/WentUrc/astrbot_plugin_turnrig/discussions)

### 🛠️ 环境准备
确保你的开发环境满足以下要求：
- Python 3.10+
- Git
- 一个支持Python的代码编辑器（推荐VSCode）

### 🔧 项目设置
1. Fork 这个仓库到你的GitHub账户
2. Clone你的fork到本地：
   ```bash
   git clone https://github.com/你的用户名/astrbot_plugin_turnrig.git
   cd astrbot_plugin_turnrig
   ```
3. 添加原仓库作为upstream：
   ```bash
   git remote add upstream https://github.com/WentUrc/astrbot_plugin_turnrig.git
   ```
4. 安装依赖：
   ```bash
   pip install -e .
   ```

## 🎨 代码风格

麦咪有自己特殊的代码风格喵～ 请遵守以下规范：

### 🐱 麦咪语言风格
- **所有注释和日志消息都要使用可爱的猫娘语调**
- **在句末添加"喵～"或相关的可爱表情符号**
- **使用emoji让代码更生动**

参考 [猫娘代码风格指南](docs/development/coding-style.md) 获取详细说明喵～

### 📐 代码格式
我们使用以下工具维护代码质量：
- **Black**: 代码格式化
- **Ruff**: 代码检查和格式化
- **Pre-commit**: 提交前自动检查

安装开发工具：
```bash
pip install pre-commit black ruff
pre-commit install
```

### 🏗️ 代码结构
- 保持函数简洁，单一职责
- 使用有意义的变量和函数名
- 添加适当的类型注解
- 编写清晰的文档字符串

示例代码风格：
```python
async def send_cute_message(self, target: str, content: str) -> bool:
    """
    发送可爱的消息喵～ 💕
    
    Args:
        target: 目标会话ID喵
        content: 消息内容喵
        
    Returns:
        发送成功返回True，失败返回False喵
        
    Note:
        这个函数会自动添加可爱的表情符号喵～ ✨
    """
    try:
        logger.info(f"开始发送可爱消息到 {target} 喵～ 📤")
        # 实现代码...
        return True
    except Exception as e:
        logger.error(f"发送消息失败了喵: {e} 😿")
        return False
```

## 🔄 开发流程

### 1. 选择或创建Issue
- 查看 [Issues](https://github.com/WentUrc/astrbot_plugin_turnrig/issues) 找到你想解决的问题
- 如果没有相关Issue，请先创建一个
- 在Issue中说明你想要贡献，避免重复工作

### 2. 创建分支
```bash
git checkout -b feature/你的功能名称
# 或者
git checkout -b fix/修复的问题
```

分支命名规范：
- `feature/` - 新功能
- `fix/` - Bug修复
- `docs/` - 文档更新
- `refactor/` - 代码重构
- `test/` - 测试相关

### 3. 开发和测试
- 编写代码时遵循代码风格指南
- 确保代码通过所有检查：
  ```bash
  ruff check .
  black . --check
  ```
- 运行测试（如果有）：
  ```bash
  python -m pytest
  ```

### 4. 提交代码
使用规范的提交信息（参见[提交规范](#提交规范)）

### 5. 创建Pull Request
- 推送到你的fork：
  ```bash
  git push origin 你的分支名
  ```
- 在GitHub上创建Pull Request
- 填写PR模板中的所有必要信息

## 📝 提交规范

使用 [Conventional Commits](https://www.conventionalcommits.org/) 规范，但要加上麦咪的可爱风格喵～

### 提交消息格式
```
<类型>[可选范围]: <描述> 喵～ <emoji>

[可选的正文]

[可选的脚注]
```

### 类型说明
- `feat`: 新功能 ✨
- `fix`: Bug修复 🐛
- `docs`: 文档更新 📝
- `style`: 代码风格调整 💄
- `refactor`: 代码重构 ♻️
- `perf`: 性能优化 ⚡
- `test`: 测试相关 ✅
- `build`: 构建相关 🔧
- `ci`: CI/CD相关 👷

### 示例
```bash
git commit -m "feat(messaging): 添加消息过滤功能喵～ ✨"
git commit -m "fix(forward): 修复嵌套转发消息显示问题喵～ 🐛"
git commit -m "docs: 更新README中的配置示例喵～ 📝"
```

## 🧪 测试要求

### 单元测试
- 为新功能编写单元测试
- 确保测试覆盖核心逻辑
- 测试文件命名：`test_*.py`

### 集成测试
- 在真实环境中测试功能
- 验证与AstrBot的集成
- 测试不同平台的兼容性

### 测试环境
在PR中提供以下测试信息：
- AstrBot版本
- Python版本
- 操作系统
- QQ版本（如适用）

## 📖 文档更新

当你的更改需要文档更新时：

### README.md
- 新功能需要更新功能介绍
- 配置变更需要更新配置说明
- 安装步骤变更需要更新安装指南

### CHANGELOG.md
- 所有用户可见的更改都要记录
- 按照现有格式添加条目
- 包含更改类型和简要说明

### 代码注释
- 为复杂逻辑添加详细注释
- 更新过时的注释
- 保持麦咪的可爱风格

## 🤝 社区准则

### 💕 友善互助
- 保持友善和尊重的态度
- 欢迎新人，耐心解答问题
- 使用可爱的语调，但不要过度喵～

### 🎯 高质量贡献
- 确保你的代码能够正常工作
- 提供清晰的问题描述和解决方案
- 遵循项目的设计理念和架构

### 📢 有效沟通
- 在Issue中详细描述问题
- 在PR中说明更改的原因和影响
- 及时回应维护者的反馈

### 🔄 持续改进
- 接受代码审查的建议
- 从反馈中学习和成长
- 帮助改进项目质量

## 🎉 贡献者权益

作为贡献者，你将获得：
- 在项目README中的感谢名单
- 优先获得新功能的内测资格
- 参与项目决策的讨论权
- 麦咪的特别感谢喵♡～ ✨

## 📞 获取帮助

如果你在贡献过程中遇到任何问题：

1. 查看现有的 [Issues](https://github.com/WentUrc/astrbot_plugin_turnrig/issues)
2. 在 [Discussions](https://github.com/WentUrc/astrbot_plugin_turnrig/discussions) 中提问
3. 联系维护者：
   - GitHub: [@IGCrystal](https://github.com/IGCrystal)
   - 邮箱: tr@wenturc.com

## 🙏 致谢

感谢所有为这个项目做出贡献的可爱开发者们喵♡～ 

你的每一个贡献都让麦咪的转发插件变得更好！让我们一起创造更棒的用户体验吧！✨

---

> 记住：代码可以有bug，但可爱不能缺少喵～ ��

最后更新时间：2024年12月 