# OmniAI 服务基础约定 v1

此约定适用于 OmniAI 新增服务，不改动 RAGFlow upstream API。

## 健康接口

服务提供 `GET /health` 或 `GET /api/v1/health`，返回 JSON，至少包含 `ok`、`service`、`version`。Spring Actuator 的 `/actuator/health` 继续提供标准 Spring 健康状态；新增 `/api/v1/health` 提供跨服务约定。

## 请求标识与错误

收到 `X-Request-ID` 时应沿用；没有时生成。响应通过 `X-Request-ID` 或 JSON `request_id` 返回。错误 JSON 形如：

```json
{"error":{"code":"UPSTREAM_UNAVAILABLE","message":"gateway request failed","request_id":"..."}}
```

`message` 不包含密钥、完整请求体或栈追踪。跨服务调用设置超时；NestJS BFF 的上游超时可通过 `OMNIAI_UPSTREAM_TIMEOUT_MS` 配置。NATS 事件携带 `trace_id` 与 `run_id`，但当前 Core NATS 作业状态仍在网关内存中，不能宣称持久投递。

## 版本

Gateway 为 2.0.0；Go、NestJS、Spring 学习服务为 0.1.0。具体运行版本以服务响应和环境报告为准。
