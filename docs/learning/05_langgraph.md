# LangGraph

## 解决的问题

实现有边界的 Agent 状态流。

## 核心原理

StateGraph 的节点更新状态，条件边决定 retry 或 finish，重试上限防止循环。

## 本项目代码位置

services/omniai_agent/graph.py；scripts/omniai/smoke_agent.py

## 如何运行

运行 .\scripts\omniai\dev.ps1 agent。

## 如何测试

三条确定性路径：PASS、RETRIEVE_MORE 后 PASS、ABSTAIN。

## 与其他技术的关系

编排可替换，但 OmniRAG Evidence Verifier 和 ToolPolicy 保持权威。

## 常见面试题

为何设置 max_retries？答：避免反思循环。条件边依据什么？答：验证决策和当前重试数。

## 当前真实运行状态

PASS：LangGraph 图真实 invoke，重试计数已验证。
