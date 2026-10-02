# FastAPI

## 解决的问题

提供统一 HTTP、校验、异步作业和 OpenAPI。

## 核心原理

Pydantic v2 校验输入；中间件加 Request-ID、限流和 metrics。

## 本项目代码位置

services/omniai_gateway/；omniai_platform/

## 如何运行

运行 .\scripts\omniai\dev.ps1 gateway。

## 如何测试

容器 core profile 的 health/modules/docs/openapi/metrics 均返回 200；HTTP 自检通过。

## 与其他技术的关系

Gateway 面向 UI，并把作业交给本地管理器或 NATS。

## 常见面试题

为何返回 202？答：分析异步完成。幂等键作用？答：避免重复提交同一请求。

## 当前真实运行状态

PASS：真实 HTTP 和容器健康检查。
