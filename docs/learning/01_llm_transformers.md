# LLM 与 Transformers

## 解决的问题

将文本映射为上下文相关的 token 表示并生成续写。

## 核心原理

分词、注意力、位置编码和自回归解码；LoRA 只训练低秩增量。

## 本项目代码位置

scripts/omnirag/phase6_build_router_dataset.py；extensions/omnirag/router/

## 如何运行

先执行 nvidia-smi；Phase-6 训练按 docs/omnirag/FINAL_LOCAL_EXECUTION_PLAN.md 的 Gate 6。

## 如何测试

比较零样本、规则、LoRA、QLoRA，并通过 promotion gate；不下载大于 10GB 的模型。

## 与其他技术的关系

Router 选择策略，RAG 提供证据；TensorFlow 严重度分类不承担 LLM 生成。

## 常见面试题

为什么注意力需要位置编码？答：纯注意力对顺序不敏感。LoRA 改变什么？答：冻结基座并训练低秩矩阵。

## 当前真实运行状态

本地独立环境中已完成 Qwen3-0.6B 的基座推理及 LoRA、QLoRA 两组独立合成数据训练；adapter 加载可运行。短推理不等于正式 Router schema 与受保护 benchmark 评估，不能进入产品。训练结果与限制见 `artifacts/runtime/FINAL_RUNTIME_REPORT.md`。Gate 1 尚未完成，因此 Gate 6 的 promotion gate 保持 DEFERRED。
