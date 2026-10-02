# LangChain

## 解决的问题

组合确定性处理与工具调用。

## 核心原理

RunnableLambda、RunnableParallel 和 LCEL 管道形成可组合执行图；工具 schema 约束参数。

## 本项目代码位置

labs/langchain_lab/runnable_demo.py

## 如何运行

运行 .\scripts\omniai\dev.ps1 langchain。

## 如何测试

已运行规范化查询和 calculate_availability 工具调用。

## 与其他技术的关系

LangGraph 使用状态机；OmniRAG Core 保留检索与证据治理所有权。

## 常见面试题

Runnable 与函数区别？答：Runnable 提供统一 invoke/batch/stream 接口。工具注解能授权吗？答：不能，ToolPolicy 才能授权。

## 当前真实运行状态

PASS：隔离环境中真实 import、LCEL 和工具调用。
