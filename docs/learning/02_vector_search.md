# 向量检索

## 解决的问题

按语义相似度查找候选证据。

## 核心原理

余弦相似度比较方向；精确 top-k 全量排序，ANN 用索引换取速度。

## 本项目代码位置

labs/vector_lab/cosine_search.py；labs/vector_lab/milvus_lite_demo.py

## 如何运行

运行 .\scripts\omniai\dev.ps1 vector。

## 如何测试

精确 top-k 测试通过；Milvus Lite 在 Linux 容器中插入 2 条并检索通过。

## 与其他技术的关系

为 RAG 提供候选；OmniRAG 的核心评分与 benchmark 保持独立。

## 常见面试题

向量维度不一致会怎样？答：拒绝比较。ANN 与 exact 有何区别？答：ANN 用近似换取吞吐和延迟。

## 当前真实运行状态

PASS：纯 Python 精确检索和容器化 Milvus Lite smoke。
