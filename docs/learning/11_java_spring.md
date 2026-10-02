# Spring Boot Connector

## 解决的问题

以独立服务模拟企业资产系统。

## 核心原理

Controller 返回静态 CMDB 数据，Actuator 提供健康检查。

## 本项目代码位置

services/omniai_enterprise_spring/

## 如何运行

mvn -f services/omniai_enterprise_spring/pom.xml test package；运行 .\scripts\omniai\dev.ps1 polyglot。

## 如何测试

Actuator UP，GET /api/v1/assets/GW-01 返回资产。

## 与其他技术的关系

OmniAI 可通过只读接口取得资产；不连接真实企业系统。

## 常见面试题

Actuator 解决什么问题？答：运行健康与管理端点。为何只读？答：减少练习服务的业务风险。

## 当前真实运行状态

PASS：Java 21、Maven 构建和真实 HTTP。
