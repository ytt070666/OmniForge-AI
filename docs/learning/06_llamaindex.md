# LlamaIndex

## 解决的问题

构建独立索引并检索文档。

## 核心原理

Document 转 Node，VectorStoreIndex 结合 embedding 建索引，Retriever 返回命中。

## 本项目代码位置

services/omniai_llamaindex/app.py

## 如何运行

运行 .\scripts\omniai\dev.ps1 llamaindex；POST /api/v1/index 后 POST /api/v1/search。

## 如何测试

3 文档 MockEmbedding 的 health/index/search 已通过。

## 与其他技术的关系

这是学习服务；MockEmbedding 结果不能证明优于 RAGFlow。

## 常见面试题

MockEmbedding 能评估语义质量吗？答：不能。Query Engine 与 Retriever 的差别？答：前者可附加合成回答。

## 当前真实运行状态

PASS：索引和检索功能；语义质量 DEFERRED。
