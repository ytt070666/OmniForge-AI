# NestJS BFF

## 解决的问题

聚合前端所需的网关数据。

## 核心原理

Controller 暴露路由，依赖注入与模块组织服务；此项目聚合 health/modules。

## 本项目代码位置

services/omniai_bff_nest/src/main.ts

## 如何运行

在服务目录 npm ci、npm run build；运行 .\scripts\omniai\dev.ps1 polyglot。

## 如何测试

真实 NestJS→FastAPI summary 请求通过。

## 与其他技术的关系

BFF 不保存事件或证据源数据。

## 常见面试题

何时用 BFF？答：为客户端整合多个后端接口。为何设置上游 URL 环境变量？答：不同环境可切换。

## 当前真实运行状态

PASS：安装、构建与 HTTP 聚合。
