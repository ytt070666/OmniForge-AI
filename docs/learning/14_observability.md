# 可观测性

## 解决的问题

追踪请求、作业和工具执行并暴露指标。

## 核心原理

Request-ID 贯穿 HTTP；Prometheus Counter/Histogram 记录次数和时延。

## 本项目代码位置

services/omniai_gateway/app.py；infra/omniai/prometheus/

## 如何运行

启动 core profile 后请求 /metrics；observability profile 启动 Prometheus。

## 如何测试

/metrics 返回真实指标，HTTP 响应含 X-Request-ID。

## 与其他技术的关系

LangGraph/NATS/Go 的 trace_id 仍需统一传播；Langfuse 需真实配置。

## 常见面试题

Trace 与 metric 有何区别？答：前者定位单次链路，后者汇总趋势。

## 当前真实运行状态

PARTIAL：Prometheus 与 Request-ID 已验证；跨服务完整 tracing 未验证。
