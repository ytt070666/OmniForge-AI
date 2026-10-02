# NATS 分布式消息

## 解决的问题

解耦网关与工作进程。

## 核心原理

发布/订阅和 queue group 做单次消费；JetStream 才提供持久化 ACK。

## 本项目代码位置

omniai_platform/nats_jobs.py；services/omniai_agent/worker.py

## 如何运行

先启动 NATS，再运行 .\scripts\omniai\dev.ps1 distributed。

## 如何测试

FastAPI→NATS→worker→NATS→状态查询通过。

## 与其他技术的关系

Go 网关订阅 NATS 并转发 SSE；当前作业状态仍在网关进程内存。

## 常见面试题

Core NATS 有持久 ACK 吗？答：没有，需要 JetStream。队列组做什么？答：在消费者间分配消息。

## 当前真实运行状态

PARTIAL：消息链路通过；持久 ACK/重试尚未接入产品作业。
