# Docker 微服务

## 解决的问题

以隔离服务组合多语言模块并控制资源。

## 核心原理

Compose profile 选择一批服务；健康检查确认进程可服务。

## 本项目代码位置

infra/omniai/docker-compose.yml

## 如何运行

docker compose -f infra/omniai/docker-compose.yml --profile core up -d --build gateway。

## 如何测试

core 已构建、健康、功能测试并停止；其他 profile 配置已验证。

## 与其他技术的关系

Windows 主机保留源码，Docker Desktop Linux Containers 承载 Linux 镜像。

## 常见面试题

profile 有什么用？答：按需启动一组服务。容器健康与进程启动相同吗？答：不同。

## 当前真实运行状态

PARTIAL：core 实测，其余 profile 需逐批验证。
