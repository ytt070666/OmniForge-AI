# RAG

## 解决的问题

让生成基于可检索证据。

## 核心原理

检索候选、重排、引用、证据验证；缺证据时应拒答。

## 本项目代码位置

rag/；extensions/omnirag/；apps/omniops/api/

## 如何运行

运行 .\scripts\omniai\dev.ps1 omniops，查看 demo 事件。

## 如何测试

执行 scripts/omnirag/omniops_selfcheck.py；正式 RAGFlow 基线按 Gate 1。

## 与其他技术的关系

LangGraph 负责编排，OmniRAG Evidence Verifier 判定证据。

## 常见面试题

如何防止无依据回答？答：核对引用与证据，不足时 abstain。

## 当前真实运行状态

PARTIAL：deterministic_product 链路通过；live RAGFlow Gate 1 未运行。
