"""模型构建：内置 FaceExpressionNet 与 torchvision 预训练骨干（迁移学习）。

- face_expression_net：本项目的深度可分离 CNN（与 face-api.js 同技术族），从头训练；
- torchvision 骨干（mobilenet_v3_small / mobilenet_v3_large / efficientnet_b0 /
  resnet18）：加载 ImageNet 预训练权重，替换分类头后在 FER2013 上微调。
  这是在小数据集上突破"从头训练天花板"（FER2013 约 65-68%）最有效的手段。
"""
from __future__ import annotations

import torch.nn as nn

from .architectures import FaceExpressionNet

# ∅ 分类头在不同骨干中的命名前缀（用于分组学习率与冻结主干）
TORCHVISION_BACKBONES: dict[str, tuple[str, str]] = {
    "mobilenet_v3_small": ("mobilenet_v3_small", "MobileNet_V3_Small_Weights"),
    "mobilenet_v3_large": ("mobilenet_v3_large", "MobileNet_V3_Large_Weights"),
    "efficientnet_b0": ("efficientnet_b0", "EfficientNet_B0_Weights"),
    "resnet18": ("resnet18", "ResNet18_Weights"),
}

BUILTIN_NAME = "face_expression_net"


def head_prefix_for(model_name: str) -> str:
    """返回分类头的参数名前缀，用于区分主干/头部学习率。"""
    n = (model_name or BUILTIN_NAME).lower()
    if n.startswith("mobilenet_v3") or n.startswith("efficientnet"):
        return "classifier."
    if n.startswith("resnet"):
        return "fc."
    return "head."


def is_torchvision(name: str) -> bool:
    return (name or "").lower() in TORCHVISION_BACKBONES


def build_model(
    name: str = BUILTIN_NAME,
    num_classes: int = 7,
    pretrained: bool = False,
    dropout: float = 0.2,
    width_mult: float = 1.0,
    use_se: bool = False,
    se_ratio: int = 8,
) -> nn.Module:
    """按名称构建模型；torchvision 骨干会替换为 num_classes 分类头。"""
    key = (name or BUILTIN_NAME).lower()

    if key in ("face_expression_net", "custom", "builtin"):
        return FaceExpressionNet(in_channels=3, num_classes=num_classes,
                                 width_mult=width_mult, dropout=dropout,
                                 use_se=use_se, se_ratio=se_ratio)

    if key not in TORCHVISION_BACKBONES:
        raise ValueError(
            f"未知模型 {name!r}；可选：{BUILTIN_NAME}、{', '.join(TORCHVISION_BACKBONES)}"
        )

    import torchvision.models as tvm

    fn_name, weights_enum_name = TORCHVISION_BACKBONES[key]
    fn = getattr(tvm, fn_name)
    weights = None
    if pretrained:
        weights = getattr(tvm, weights_enum_name).IMAGENET1K_V1

    model = fn(weights=weights)
    _replace_head(model, key, num_classes, dropout)
    return model


def _replace_head(model: nn.Module, key: str, num_classes: int, dropout: float) -> None:
    """把骨干的 ImageNet 1000 类分类头替换为 num_classes 类，并加入 Dropout。"""
    if key.startswith("mobilenet_v3") or key.startswith("efficientnet"):
        # classifier 为 Sequential(... , Dropout, Linear)，末位即 Linear
        in_f = model.classifier[-1].in_features
        model.classifier[-1] = nn.Linear(in_f, num_classes)
        return
    if key.startswith("resnet"):
        in_f = model.fc.in_features
        model.fc = nn.Sequential(nn.Dropout(dropout), nn.Linear(in_f, num_classes)) if dropout > 0 \
            else nn.Linear(in_f, num_classes)
        return
    raise ValueError(f"未实现分类头替换：{key}")