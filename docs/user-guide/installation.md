# 📦 安装指南

欢迎使用 **Turnrig** 插件喵 这里会详细教你如何安装和初始化插件！

## 🎯 前提条件

在开始之前，请确保你已经：

- ✅ 安装并配置了 AstrBot 3.x 或更高版本
- ✅ 拥有至少一个QQ机器人账号（推荐使用NapCat，其次Lagarange）
- ✅ 对AstrBot的基本操作有一定了解

## 🚀 快速安装

### 方法1: 通过AstrBot插件市场安装 (推荐)

1. 打开AstrBot的WebUI界面
2. 进入「插件管理」页面
3. 在插件市场中搜索「turnrig」或「转发」
4. 点击「安装」按钮
5. 等待安装完成后，重启AstrBot

### 方法2: 手动Git安装

```bash
# 进入AstrBot的插件目录
cd AstrBot/data/plugins

# 克隆插件仓库
git clone https://github.com/WentUrc/astrbot_plugin_turnrig.git

# 安装依赖
cd astrbot_plugin_turnrig
pip install -r requirements.txt
```

### 方法3: 下载压缩包安装

1. 访问 [GitHub Releases](https://github.com/IGCrystal-NEO/astrbot_plugin_turnrig/releases)
2. 下载最新版本的压缩包
3. 解压到 `AstrBot/data/plugins/` 目录下
4. 重命名文件夹为 `astrbot_plugin_turnrig`
5. 安装依赖：`pip install -r requirements.txt`

## ⚙️ 初始配置

### 1. 启用插件

安装完成后：

1. 重启AstrBot
2. 在WebUI的「插件管理」页面找到「turnrig」
3. 点击「启用」按钮
4. 确认插件状态显示为「运行中」

### 2. 基础配置

插件启用后，需要进行基础配置：

```json
{
  "转发任务": [
    {
      "name": "我的第一个转发任务",
      "source_sessions": ["aiocqhttp:GroupMessage:源群号"],
      "target_sessions": ["aiocqhttp:GroupMessage:目标群号"],
      "max_messages": 20,
      "enabled": true
    }
  ]
}
```

### 3. 配置说明

- `source_sessions`: 消息来源会话列表
- `target_sessions`: 转发目标会话列表  
- `max_messages`: 触发转发的消息数量阈值
- `enabled`: 是否启用该转发任务

详细配置说明请查看 [配置说明](configuration.md) 文档喵～

## 🧪 测试安装

安装完成后，可以通过以下方式测试：

### 1. 检查插件状态

在AstrBot日志中应该能看到：
```
[Plug] [INFO] turnrig插件已启动 ✨
```

### 2. 发送测试命令

在配置的源群中发送几条测试消息，检查是否按预期转发到目标群。

### 3. 查看插件日志

在AstrBot的插件管理页面，点击「查看日志」按钮，确认插件正常工作。

## 🔧 常见安装问题

### 问题1: 依赖安装失败

**症状**: 出现 `ModuleNotFoundError` 错误

**解决方案**:
```bash
# 手动安装缺失的依赖
pip install aiohttp aiofiles
```

### 问题2: 插件无法启动

**症状**: 插件在启用后立即停止

**解决方案**:
1. 检查AstrBot版本是否兼容
2. 查看详细错误日志
3. 确认配置文件格式正确

### 问题3: 权限不足

**症状**: 无法创建文件或目录

**解决方案**:
```bash
# 为插件目录设置适当的权限
chmod -R 755 data/plugins/astrbot_plugin_turnrig
```

## 📊 安装完成检查清单

安装完成后，请确认以下项目：

- [ ] 插件在WebUI中显示为「运行中」状态
- [ ] 配置文件格式正确且已保存
- [ ] 机器人没有被风控
- [ ] 测试转发功能正常工作
- [ ] 插件日志没有错误信息

## 🎉 下一步

恭喜你成功安装了 **Turnrig** 转发插件 接下来你可以：

1. 📖 阅读 [配置说明](configuration.md) 了解详细配置选项
2. 🚀 查看 [使用教程](usage.md) 学习高级功能
3. 🔧 如有问题，参考 [故障排除](troubleshooting.md) 文档

---

祝你使用愉快 如果遇到任何问题，随时可以在GitHub上提issue或加群讨论！✨ 
