# 🐱 代码风格指南

## 注释风格规范

### 函数注释模板
```python
def some_function():
    """
    这个函数做什么什么事情
    
    Args:
        参数: 参数说明
        
    Returns:
        返回值: 返回什么东西
        
    Note:
        特别注意的事情！⚠️
    """
    pass
```

### 常用注释短语
- `# 开始处理消息`
- `# 这里需要特别小心`
- `# 成功完成任务`
- `# 出错了，需要重试`
- `# 初始化完成`
- `# 清理工作完成`

### 错误处理注释
```python
try:
    # 尝试做某件事
    pass
except Exception as e:
    # 出错了！记录错误信息
    logger.error(f"发生错误: {e}")
```

### 循环注释
```python
for item in items:
    # 一个一个处理
    pass
```

### 条件判断注释
```python
if condition:
    # 如果满足条件就这样做！ ✅
    pass
else:
    # 否则就那样做 ❌
    pass
```

## 表情符号使用指南（表情符号部分将会在 v1.6.5 弃用） 🎨

### 常用表情
- 🐱 🐾 ฅ(^•ω•^ฅ) (´ω`) (=^･ω･^=)
- ✨ 🌟 💫 (成功/完成)
- ⚠️ 😿 💔 (警告/错误)
- 🔄 ⏳ (处理中)
- ✅ ❌ (条件判断)
- 🧹 📝 (清理/记录)

### 使用原则
1. 每个重要函数都要有文档字符串
2. 关键逻辑处添加行内注释
3. 错误处理要表达出猫咪的委屈感
4. 成功完成要表达出猫咪的开心

## 示例代码 📖

```python
class MessageProcessor:
    """
    消息处理器
    负责把消息变得更规范
    """
    
    def __init__(self):
        """初始化消息处理器"""
        self.messages = []  # 存储消息的小篮子
        
    async def process_message(self, msg):
        """
        处理单条消息
        会把消息变得规范
        
        Args:
            msg: 要处理的消息
            
        Returns:
            处理后的消息
        """
        try:
            # 开始处理消息
            processed = self._clean_message(msg)
            processed = self._add_cuteness(processed)
            
            return processed
            
        except Exception as e:
            # 出错了
            logger.error(f"处理消息失败: {e}")
            return None
            
    def _clean_message(self, msg):
        """清理消息内容"""
        # 去掉多余的空格
        return msg.strip()
        
    def _add_cuteness(self, msg):
        """给消息添加元素"""
        # 在消息末尾添加可爱的表情
        return f"{msg} 喵～"
```

代码书写完成后，需要使用 `ruff` 检查一下。

记住：代码不仅要工作，还要规范而又统一！
