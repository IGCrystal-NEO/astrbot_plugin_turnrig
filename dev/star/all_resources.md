---
outline: deep
---

# 插件开发使用的类与数据资源索引

下面讲解一些插件开发中使用到的 AstrBot 核心提供的类与数据资源, 文档中不会介绍类的所有的属性, 部分属性和方法不建议在插件中使用, 这部分内容不会在这里介绍。
文档中默认 self 是指该类的实例, 你可以在对应类内部的任何方法中使用这些资源, 注意文档中的所有方法都省略了 self 参数, 你需要使用`self.属性名`或`self.方法名()`进行调用。

## AstrBot 消息事件

- [AstrMessageEvent](/dev/star/resources/astr_message_event.md)

## 功能类

- [Star](/dev/star/resources/star.md)

## 数据类

- [Context](/dev/star/resources/context.md)
- [StarMetadata](/dev/star/resources/star_metadata.md)
