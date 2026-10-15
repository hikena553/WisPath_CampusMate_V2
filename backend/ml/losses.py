"""损失函数：交叉熵与 Focal Loss。

Focal Loss 用于缓解"易分样本主导梯度"：在交叉熵前乘 (1-pt)^gamma 调制因子，
把梯度集中到难分样本上。在类别不均衡 + 标签有噪声的场景（FER2013）里，
它常与重采样、标签平滑配合使用。
"""
from __future__ import annotations

import torch
import torch.nn as nn

from .config import TrainingConfig


class FocalLoss(nn.Module):
    """Focal Loss（gamma 调制 + 可选类别加权 + 标签平滑）。

    实现说明：先算带权重与标签平滑的逐样本交叉熵，再乘 focal 调制因子。
    pt 由 -loss 反推（loss = -log(pt)），因此调制项自然地把"已经分对且很自信"
    的样本权重压低。这是实现简单且被广泛采用的近似写法。
    """

    def __init__(self, gamma: float = 2.0, weight: torch.Tensor | None = None,
                 label_smoothing: float = 0.0) -> None:
        super().__init__()
        self.gamma = float(gamma)
        self.ce = nn.CrossEntropyLoss(weight=weight, label_smoothing=label_smoothing,
                                      reduction="none")

    def forward(self, logits: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        loss = self.ce(logits, target)
        pt = torch.exp(-loss)
        return ((1.0 - pt).clamp(min=0.0) ** self.gamma * loss).mean()


def build_loss(cfg: TrainingConfig, class_weight: torch.Tensor | None = None) -> nn.Module:
    """按配置构建损失：loss=ce（默认，带标签平滑与类别加权）或 loss=focal。"""
    if str(cfg.loss).lower() == "focal":
        return FocalLoss(gamma=cfg.focal_gamma, weight=class_weight,
                         label_smoothing=cfg.label_smoothing)
    return nn.CrossEntropyLoss(weight=class_weight, label_smoothing=cfg.label_smoothing)