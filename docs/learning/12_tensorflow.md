# TensorFlow / Keras

## 解决的问题

训练独立的事件严重度分类器。

## 核心原理

tf.data 输入，Keras 拟合、评估、保存，再由 FastAPI 加载预测。

## 本项目代码位置

labs/tensorflow_lab/train.py；services/omniai_tensorflow/app.py

## 如何运行

在独立的 TensorFlow 虚拟环境中运行 `python labs/tensorflow_lab/train.py`；需要启动服务时使用 `scripts/omniai/dev.ps1 tensorflow`，并通过 `OMNIAI_TF_PYTHON` 指定该环境的 Python。

## 如何测试

CPU 训练 160 条合成样本；evaluate、模型保存及 /api/v1/severity 通过。

## 与其他技术的关系

该分类器不是 OmniRAG 的大语言模型。

## 常见面试题

为何使用独立环境？答：避免 TensorFlow 与 RAGFlow 依赖冲突。训练准确率可当生产指标吗？答：不能。

## 当前真实运行状态

PASS：CPU 学习实验与服务预测；生产效果未评估。
