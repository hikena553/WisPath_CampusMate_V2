"""人脸表情识别模型训练 / 微调后端模块。

本模块复现前端 face-api.js faceExpressionNet 的技术路线
（深度可分离卷积 + 稠密卷积块），提供：
- 模型架构（architectures.FaceExpressionNet）
- 数据集加载与增强（dataset）
- 训练 / 微调主流程（train.run_training）
- 评估指标（metrics）与产物落盘（artifacts）

注意：本模块依赖 PyTorch，属于"离线训练工具"，不是 Web 服务运行时的
必需依赖。FastAPI 侧只读取 runs/ 下的产物，不 import torch。
"""
from .architectures import CLASS_NAMES, CLASS_NAMES_CN, FaceExpressionNet, count_parameters  # noqa: F401
from .config import TrainingConfig  # noqa: F401

__all__ = ["FaceExpressionNet", "TrainingConfig", "CLASS_NAMES", "CLASS_NAMES_CN", "count_parameters"]