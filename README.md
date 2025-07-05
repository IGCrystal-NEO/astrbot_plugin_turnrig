# 转发侦听插件 (TurnRig) 喵～

<img src="https://count.getloli.com/@:astrbot_plugin_turnig" alt=":astrbot_plugin_turnig" width="100%" />

> 一个消息监听与转发插件，支持多种消息类型喵～

## 🔮 麦咪的数字占卜 (2025-07-06 06:11 CST)

**😐 平平无奇** ✨

🎯 **幸运数字**: 95
🎨 **幸运颜色**: 🤍 白色
💡 **今日建议**: 今天适合写代码喵～记得多喝水哦

*每小时更新一次，仅供娱乐喵～* 🐱



## 📚 文档导航

### 🌟 用户文档
- 📖 [完整文档](docs/README.md) - 完整的文档中心，包含所有详细信息
- 📦 [安装指南](docs/user-guide/installation.md) - 详细的安装步骤和配置说明
- ⚙️ [配置说明](docs/user-guide/configuration.md) - 所有配置参数的详细解释
- 🚀 [使用教程](docs/user-guide/usage.md) - 从基础到高级的使用方法
- 🔧 [故障排除](docs/user-guide/troubleshooting.md) - 常见问题和解决方案

### 👩‍💻 开发者文档
- 🎨 [代码风格](docs/development/coding-style.md) - 麦咪特有的可爱代码规范
- 🔧 [插件开发](docs/development/plugin-development.md) - AstrBot插件开发指南
- 🤝 [贡献指南](CONTRIBUTING.md) - 如何为项目做贡献

### 📡 API参考
- 📨 [消息处理](docs/api/message-handling.md) - 消息处理相关API
- 🔀 [转发功能](docs/api/forwarding.md) - 转发核心功能API  
- 📋 [配置结构](docs/api/configuration-schema.md) - 配置文件结构说明

### 🏛️ 架构文档
- 🎯 [设计概览](docs/architecture/overview.md) - 整体设计理念和目标
- 🧩 [组件设计](docs/architecture/component-design.md) - 各个组件的设计说明
- 📊 [消息流程](docs/architecture/message-flow.md) - 数据在组件间的流转

## ✨ 功能一览喵～

- 🔍 **多源监听**: 可以同时监听多个群聊/私聊的消息喵～
- 🚀 **灵活转发**: 支持将消息转发到多个目标会话喵～
- 👤 **精确监控**: 可以只监听群内特定用户的消息喵～
- 📱 **多平台支持**: 目前支持QQ(aiocqhttp)平台，未来会支持更多平台喵～
- 🖼️ **富媒体支持**: 完整保留表情、图片、引用回复等消息元素喵～
- 🔄 **任务管理**: 支持创建多个转发任务，每个任务可以有不同的配置喵～

## 📦 安装方法喵～

1. 确保你已经安装了 AstrBot 主程序喵～
2. 将整个 `astrbot_plugin_turnrig` 文件夹放入 AstrBot 的 `data/plugins` 目录下喵～
3. 重启 AstrBot，插件会自动加载喵～

## 🛠️ 使用指南喵～

### 基础指令喵～

所有的指令都以 `/turnrig` 或简化版 `/tr` 开头喵～

#### 管理命令喵～

- `/turnrig list` - 列出所有转发任务喵～
- `/turnrig status [任务ID]` - 查看缓存状态喵～
- `/turnrig create [名称]` - 创建新任务喵～
- `/turnrig delete <任务ID>` - 删除任务喵～
- `/turnrig enable <任务ID>` - 启用任务喵～
- `/turnrig disable <任务ID>` - 禁用任务喵～

#### 任务配置命令喵～

- `/turnrig monitor <任务ID> 群聊/私聊 <会话ID>` - 添加监听源喵～
- `/turnrig unmonitor <任务ID> 群聊/私聊 <会话ID>` - 删除监听源喵～
- `/turnrig target <任务ID> 群聊/私聊 <会话ID>` - 添加转发目标喵～
- `/turnrig untarget <任务ID> 群聊/私聊 <会话ID>` - 删除转发目标喵～
- `/turnrig threshold <任务ID> <数量>` - 设置消息阈值喵～

#### 群聊用户监听命令喵～

- `/turnrig adduser <任务ID> <群号> <QQ号>` - 添加群聊内特定用户监听喵～
- `/turnrig removeuser <任务ID> <群号> <QQ号>` - 移除群聊内特定用户监听喵～

#### 其他功能命令喵～

- `/turnrig rename <任务ID> <名称>` - 重命名任务喵～
- `/turnrig forward <任务ID> [群聊/私聊 <会话ID>]` - 手动触发转发喵～
- `/turnrig cleanup <天数>` - 清理指定天数前的已处理消息ID喵～
- `/turnrig help` - 显示帮助信息喵～

### 简化指令喵～

为了方便使用，插件提供了一组简化指令，自动使用当前会话ID喵～

- `/tr add <任务ID>` - 将当前会话添加到监听列表喵～
- `/tr remove <任务ID>` - 将当前会话从监听列表移除喵～
- `/tr target <任务ID>` - 将当前会话添加为转发目标喵～
- `/tr untarget <任务ID>` - 将当前会话从转发目标移除喵～
- `/tr adduser <任务ID> <QQ号>` - 添加指定用户到当前群聊的监听列表喵～
- `/tr removeuser <任务ID> <QQ号>` - 从当前群聊的监听列表中移除指定用户喵～
- `/tr list` - 列出所有转发任务喵～
- `/tr help` - 显示简化指令帮助喵～

## 📝 会话ID格式说明喵～

插件支持多种会话ID格式喵～：

- **推荐格式**: `群聊 群号` 或 `私聊 QQ号`（注意空格）
- **标准格式**: `aiocqhttp:GroupMessage:群号` 或 `aiocqhttp:FriendMessage:QQ号`
- **不推荐**: 纯数字ID可能会导致类型识别错误喵～

## 🌟 使用示例喵～

### 创建转发任务喵～
```
/turnrig create 监控群A
```

### 添加监听源喵～
```
/turnrig monitor 1 群聊 123456789
```
或者在目标群内直接使用：
```
/tr add 1
```

### 添加转发目标喵～
```
/turnrig target 1 私聊 987654321
```
或者在目标会话内直接使用：
```
/tr target 1
```

### 只监听群内特定用户喵～
```
/turnrig adduser 1 123456789 111222333
```
或者在目标群内直接使用：
```
/tr adduser 1 111222333
```

### 手动触发转发喵～
```
/turnrig forward 1
```

## 💾 数据存储喵～

插件的数据会自动保存在 `data/plugins_data/astrbot_plugin_turnrig` 目录下喵～：

- 配置文件: `config.json` - 保存任务配置喵～
- 消息缓存: `message_cache.json` - 保存监听到的消息喵～
- 临时文件: `temp/` - 存储转发过程中的临时图片文件喵～

## 🔧 进阶配置喵～

插件会每5分钟自动保存数据，每天自动清理7天前的消息ID，每小时清理24小时前的临时文件喵～

## 📢 已经实现的功能

- [x] 文字
- [x] 图片
- [x] 转发消息 （旧版本的协议端或许可用）
- [x] 引用消息
- [ ] 语音
- [x] 视频
- [x] 文件
- [ ] QQ表情
- [ ] QQ卡片

> [!WARNING] 
> 
> 目前很多功能没有实现，只能将就用用。
>
> 目前没有想要更新的打算。

## 🤝 问题反馈喵～

如果使用过程中遇到任何问题，可以通过以下方式联系作者喵～：

- GitHub: [WentUrc/astrbot_plugin_turnrig](https://github.com/WentUrc/astrbot_plugin_turnrig)

感谢使用转发侦听插件喵～！希望它能为你带来便利喵～❤️

<img src="https://raw.githubusercontent.com/IGCyukira/IGCyukira/refs/heads/main/img/ChatGPT%20Image%202025%E5%B9%B44%E6%9C%8821%E6%97%A5%2017_32_36.png" width="100%" />
