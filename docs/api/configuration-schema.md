# 📋 配置结构 API

欢迎查看麦咪的配置结构API文档喵♡～ 这里详细说明了所有配置参数的数据结构和验证规则！

## 🏗️ 配置文件结构

### 主配置对象

```typescript
interface PluginConfig {
    tasks: Task[];                    // 转发任务列表
    default_max_messages: number;     // 默认消息阈值
    bot_self_ids?: string[];          // 机器人ID过滤列表（可选）
}
```

### 任务配置结构

```typescript
interface Task {
    id: string;                       // 任务ID（必填）
    name: string;                     // 任务名称（必填）
    monitor_groups: string[];         // 监听的群聊列表
    monitor_private_users: string[];  // 监听的私聊用户列表
    monitored_users_in_groups: {      // 监听的群聊中的特定用户
        [groupId: string]: string[];
    };
    target_sessions: string[];        // 转发目标会话列表
    max_messages: number;             // 任务消息阈值
    enabled: boolean;                 // 是否启用该任务
}
```

## 📊 配置模式定义

基于 `_conf_schema.json` 的完整配置模式喵～

### 根级配置

```json
{
    "tasks": {
        "description": "转发任务列表",
        "type": "list",
        "hint": "每个任务都有独立的监听源和转发目标配置",
        "items": { /* Task Schema */ }
    },
    "default_max_messages": {
        "description": "默认消息阈值",
        "type": "int",
        "hint": "当任务未设置消息阈值时使用的默认值",
        "default": 20
    }
}
```

### 任务项配置模式

#### 基本信息

```json
{
    "id": {
        "description": "任务ID",
        "type": "string",
        "hint": "系统自动生成的任务标识符"
    },
    "name": {
        "description": "任务名称", 
        "type": "string",
        "hint": "便于识别的任务名称"
    },
    "enabled": {
        "description": "是否启用该任务",
        "type": "bool",
        "hint": "设置为false可临时禁用此任务而不删除配置",
        "default": true
    }
}
```

#### 监听源配置

```json
{
    "monitor_groups": {
        "description": "监听的群聊列表",
        "type": "list", 
        "hint": "需要监听的群聊ID列表",
        "default": []
    },
    "monitor_private_users": {
        "description": "监听的私聊用户列表",
        "type": "list",
        "hint": "需要监听的私聊用户ID列表", 
        "default": []
    },
    "monitored_users_in_groups": {
        "description": "监听的群聊中的特定用户",
        "type": "object",
        "hint": "格式：{群聊ID: [用户ID1, 用户ID2, ...]}",
        "default": {}
    }
}
```

#### 转发目标配置

```json
{
    "target_sessions": {
        "description": "转发目标会话",
        "type": "list",
        "hint": "消息将被转发到这些会话，格式为：平台名:消息类型:会话ID",
        "default": []
    }
}
```

#### 触发条件配置

```json
{
    "max_messages": {
        "description": "任务消息阈值",
        "type": "int", 
        "hint": "当缓存的消息达到此数量时，将触发转发",
        "default": 20
    }
}
```

## 🔍 数据类型详解

### 字符串类型 (string)

- **任务ID**: 唯一标识符，通常为数字字符串
- **任务名称**: 用户友好的描述性名称
- **会话ID**: 格式为 `平台名:消息类型:会话标识符`

### 列表类型 (list)

- **monitor_groups**: 群聊ID字符串数组
- **monitor_private_users**: 用户ID字符串数组  
- **target_sessions**: 目标会话ID字符串数组

### 对象类型 (object)

- **monitored_users_in_groups**: 键值对映射
  - 键: 群聊ID字符串
  - 值: 用户ID字符串数组

### 数值类型 (int)

- **max_messages**: 正整数，范围建议 1-100
- **default_max_messages**: 正整数，默认值 20

### 布尔类型 (bool)

- **enabled**: true/false，控制任务是否生效

## 📝 配置示例

### 最小配置

```json
{
    "tasks": [],
    "default_max_messages": 20
}
```

### 完整配置示例

```json
{
    "tasks": [
        {
            "id": "1",
            "name": "工作群监控",
            "monitor_groups": ["123456789", "987654321"],
            "monitor_private_users": ["111222333"],
            "monitored_users_in_groups": {
                "123456789": ["444555666", "777888999"]
            },
            "target_sessions": [
                "aiocqhttp:GroupMessage:555666777", 
                "aiocqhttp:FriendMessage:888999000"
            ],
            "max_messages": 15,
            "enabled": true
        },
        {
            "id": "2", 
            "name": "客服转发",
            "monitor_groups": ["666777888"],
            "monitor_private_users": [],
            "monitored_users_in_groups": {},
            "target_sessions": ["aiocqhttp:GroupMessage:999000111"],
            "max_messages": 5,
            "enabled": false
        }
    ],
    "default_max_messages": 20,
    "bot_self_ids": ["123456789", "987654321"]
}
```

## 🛡️ 配置验证规则

### 必填字段验证

```python
def validate_required_fields(task: dict) -> bool:
    """验证任务必填字段喵～"""
    required_fields = ["id", "name"]
    return all(field in task and task[field] for field in required_fields)
```

### 数据类型验证

```python
def validate_data_types(config: dict) -> bool:
    """验证配置数据类型喵～"""
    type_checks = {
        "tasks": list,
        "default_max_messages": int,
        "bot_self_ids": list  # 可选字段
    }
    
    for field, expected_type in type_checks.items():
        if field in config and not isinstance(config[field], expected_type):
            return False
    return True
```

### 任务字段验证

```python
def validate_task_fields(task: dict) -> bool:
    """验证单个任务配置喵～"""
    field_types = {
        "id": str,
        "name": str, 
        "monitor_groups": list,
        "monitor_private_users": list,
        "monitored_users_in_groups": dict,
        "target_sessions": list,
        "max_messages": int,
        "enabled": bool
    }
    
    for field, expected_type in field_types.items():
        if field in task and not isinstance(task[field], expected_type):
            return False
    return True
```

### 会话ID格式验证

```python
def validate_session_id(session_id: str) -> bool:
    """验证会话ID格式喵～"""
    import re
    pattern = r'^[a-zA-Z0-9_]+:(GroupMessage|FriendMessage):[0-9]+$'
    return re.match(pattern, session_id) is not None
```

### 数值范围验证

```python
def validate_numeric_ranges(config: dict) -> bool:
    """验证数值范围喵～"""
    # 消息阈值范围检查
    if "default_max_messages" in config:
        if not (1 <= config["default_max_messages"] <= 1000):
            return False
    
    # 任务消息阈值检查
    for task in config.get("tasks", []):
        if "max_messages" in task:
            if not (1 <= task["max_messages"] <= 1000):
                return False
    
    return True
```

## 🔧 配置操作 API

### 配置加载

```python
class ConfigManager:
    def load_config(self) -> dict:
        """
        加载配置文件喵～ 📂
        
        Returns:
            解析后的配置字典，失败时返回None
        """
        
    def validate_config(self, config: dict) -> tuple[bool, str]:
        """
        验证配置有效性喵～ ✅
        
        Args:
            config: 待验证的配置字典
            
        Returns:
            (是否有效, 错误信息)
        """
```

### 配置保存

```python
def save_config(self, config: dict) -> bool:
    """
    保存配置到文件喵～ 💾
    
    Args:
        config: 要保存的配置字典
        
    Returns:
        保存是否成功
    """
```

### 配置合并

```python
def merge_config(self, base_config: dict, new_config: dict) -> dict:
    """
    合并配置对象喵～ 🔗
    
    Args:
        base_config: 基础配置
        new_config: 新配置（优先级更高）
        
    Returns:
        合并后的配置
    """
```

## 📊 配置缓存 API

### 消息缓存结构

```typescript
interface MessageCache {
    [taskId: string]: {
        [sessionId: string]: CachedMessage[];
    };
}

interface CachedMessage {
    id: string;                    // 消息ID
    timestamp: number;             // 时间戳
    sender_name: string;           // 发送者名称
    sender_id: string;             // 发送者ID
    messages: MessageComponent[];  // 序列化的消息组件
    message_outline: string;       // 消息概要
    onebot_fields: {              // OneBot协议字段
        message_type: string;
        sub_type: string;
        platform: string;
    };
}
```

### 已处理消息记录

```typescript
interface ProcessedMessageIds {
    [key: `processed_message_ids_${string}`]: ProcessedMessage[];
}

interface ProcessedMessage {
    id: string;        // 消息ID
    timestamp: number; // 处理时间戳
}
```

### 失败消息缓存

```typescript
interface FailedMessagesCache {
    [targetSession: string]: {
        [taskSessionKey: string]: FailedMessage;
    };
}

interface FailedMessage {
    task_id: string;
    session_id: string;
    target_session: string;
    timestamp: number;
    retry_count: number;
}
```

## 🔄 配置迁移 API

### 版本升级支持

```python
def migrate_config_v1_to_v2(old_config: dict) -> dict:
    """
    从v1配置格式迁移到v2喵～ 🔄
    
    v1格式特点：
    - 单一任务配置
    - 扁平化结构
    
    v2格式特点：
    - 多任务支持
    - 嵌套任务结构
    """
    
def detect_config_version(config: dict) -> str:
    """检测配置文件版本喵～"""
    
def auto_migrate_config(config: dict) -> dict:
    """自动迁移配置到最新版本喵～"""
```

### 兼容性处理

```python
def ensure_backward_compatibility(config: dict) -> dict:
    """
    确保向后兼容性喵～ 🔙
    
    处理：
    - 缺失字段的默认值填充
    - 废弃字段的清理
    - 格式规范化
    """
```

## 🎯 最佳实践

### 配置文件组织

1. **分层结构**: 全局配置 -> 任务配置 -> 具体设置
2. **命名规范**: 使用清晰描述性的任务名称
3. **文档注释**: 在配置文件中添加必要的说明

### 性能优化

1. **合理阈值**: 根据群聊活跃度设置合适的消息阈值
2. **监听优化**: 优先使用特定用户监听而非全群监听
3. **目标限制**: 单个任务的转发目标不超过10个

### 安全考虑

1. **权限控制**: 确保配置文件的读写权限安全
2. **数据验证**: 所有外部输入都进行严格验证
3. **错误处理**: 优雅处理配置错误，不影响系统稳定性

## 🚨 错误处理

### 常见配置错误

```python
class ConfigurationError(Exception):
    """配置错误基类喵～"""
    pass

class InvalidTaskIdError(ConfigurationError):
    """无效任务ID错误喵～"""
    pass

class InvalidSessionIdError(ConfigurationError):
    """无效会话ID错误喵～"""
    pass

class DuplicateTaskIdError(ConfigurationError):
    """重复任务ID错误喵～"""
    pass
```

### 错误恢复策略

1. **配置回滚**: 自动备份，错误时恢复到上一个有效配置
2. **部分失效**: 无效任务自动禁用，不影响其他任务
3. **默认值填充**: 缺失配置使用安全的默认值

---

这套配置API为麦咪提供了完整的配置管理能力，确保所有配置都是有效、安全、可维护的喵♡～ ✨

如需了解其他API，请查看 [消息处理 API](message-handling.md) 和 [转发功能 API](forwarding.md) 文档！ 