"""人脸表情识别网络 FaceExpressionNet（架构复现 + 微调支持）。

技术路线与前端 face-api.js 的 faceExpressionNet 保持一致：
- 深度可分离卷积（depthwise separable convolution）
- 稠密堆叠的卷积块（densely connected blocks）
- 输入 3×S×S（灰度图复制为 3 通道），输出 7 类表情

说明：face-api.js 官方权重为 TF.js 量化分片格式（uint8 + scale/min），
且未公开逐层 stride / padding，无法无损导入；本模块复现同一技术族
（MobileNet 风格深度可分离 CNN），支持从头训练，也支持基于本项目
产出的 checkpoint 继续微调（transfer / fine-tune）。

通道配置严格对齐官方 manifest：
  stem(3→32) → dense0(32→32 ×3) → dense1(32→64, 64→64 ×3)
  → dense2(64→128, 128→128 ×3) → dense3(128→256, 256→256 ×3)
  → 全局平均池化 → fc(256→7)
"""
from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F

NUM_CLASSES = 7

# 与前端 EMOTION_LABELS 对齐的类序（索引即标签）
CLASS_NAMES = ["angry", "disgusted", "fearful", "happy", "neutral", "sad", "surprised"]
CLASS_NAMES_CN = ["生气", "厌恶", "害怕", "开心", "平静", "难过", "惊讶"]


class SEBlock(nn.Module):
    """SE（Squeeze-and-Excitation）通道注意力。

    先全局平均池化压成通道描述子，再用两层 1×1 卷积学出每个通道的权重并重标定。
    对表情识别这类"关键线索只集中在少数通道（如眉、嘴区域特征）"的任务，
    通道注意力能放大有效通道、抑制无关通道，是低成本的涨点手段。
    """

    def __init__(self, ch: int, ratio: int = 8) -> None:
        super().__init__()
        hidden = max(4, ch // ratio)
        self.fc1 = nn.Conv2d(ch, hidden, 1, bias=True)
        self.fc2 = nn.Conv2d(hidden, ch, 1, bias=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        s = F.adaptive_avg_pool2d(x, 1)
        s = F.relu(self.fc1(s), inplace=True)
        s = torch.sigmoid(self.fc2(s))
        return x * s


class DepthwiseSeparableConv(nn.Module):
    """深度可分离卷积：depthwise 3×3 + pointwise 1×1 + BN +（可选 SE）+ ReLU6。

    ReLU6 是 MobileNet 系的标准激活，保证量化（uint8）友好；
    depthwise 分组数 = 输入通道数，参数量与计算量远低于同规格普通卷积。
    """

    def __init__(self, in_ch: int, out_ch: int, stride: int = 1,
                 use_se: bool = False, se_ratio: int = 8) -> None:
        super().__init__()
        self.depthwise = nn.Conv2d(in_ch, in_ch, 3, stride, 1, groups=in_ch, bias=False)
        self.pointwise = nn.Conv2d(in_ch, out_ch, 1, 1, 0, bias=False)
        self.bn = nn.BatchNorm2d(out_ch)
        self.se = SEBlock(out_ch, se_ratio) if use_se else None
        self.act = nn.ReLU6(inplace=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.depthwise(x)
        x = self.pointwise(x)
        x = self.bn(x)
        if self.se is not None:
            x = self.se(x)
        return self.act(x)


class FaceExpressionNet(nn.Module):
    """MobileNet 风格深度可分离 CNN，输出 7 类表情概率（logits）。

    参数说明：
    - in_channels：输入通道（灰度数据集复制为 3，与 face-api.js 一致）
    - width_mult：通道宽度缩放系数，用于轻量化实验（1.0 = 官方通道配置）
    - dropout：分类头前的 Dropout 概率，抑制过拟合
    """

    def __init__(
        self,
        in_channels: int = 3,
        num_classes: int = NUM_CLASSES,
        width_mult: float = 1.0,
        dropout: float = 0.2,
        use_se: bool = False,
        se_ratio: int = 8,
    ) -> None:
        super().__init__()

        def c(ch: int) -> int:
            return max(8, int(round(ch * width_mult / 8) * 8))

        ch32, ch64, ch128, ch256 = c(32), c(64), c(128), c(256)

        def sep(in_ch: int, out_ch: int, stride: int = 1) -> DepthwiseSeparableConv:
            return DepthwiseSeparableConv(in_ch, out_ch, stride, use_se, se_ratio)

        # 输入下采样：3×S×S -> 32×S/2×S/2
        self.stem = nn.Sequential(
            nn.Conv2d(in_channels, ch32, 3, stride=2, padding=1, bias=False),
            nn.BatchNorm2d(ch32),
            nn.ReLU6(inplace=True),
        )
        # dense0：通道保持，特征深化
        self.dense0 = nn.Sequential(sep(ch32, ch32), sep(ch32, ch32), sep(ch32, ch32))
        # dense1：32 -> 64，空间降采样
        self.dense1 = nn.Sequential(sep(ch32, ch64, 2), sep(ch64, ch64), sep(ch64, ch64))
        # dense2：64 -> 128
        self.dense2 = nn.Sequential(sep(ch64, ch128, 2), sep(ch128, ch128), sep(ch128, ch128))
        # dense3：128 -> 256
        self.dense3 = nn.Sequential(sep(ch128, ch256, 2), sep(ch256, ch256), sep(ch256, ch256))
        self.head = nn.Sequential(
            nn.Dropout(dropout),
            nn.AdaptiveAvgPool2d(1),
            nn.Flatten(),
            nn.Linear(ch256, num_classes),
        )

    def features(self, x: torch.Tensor) -> torch.Tensor:
        """骨干特征提取（微调时可冻结/解冻该部分）。"""
        x = self.stem(x)
        x = self.dense0(x)
        x = self.dense1(x)
        x = self.dense2(x)
        x = self.dense3(x)
        return x

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.head(self.features(x))


def count_parameters(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


if __name__ == "__main__":  # pragma: no cover - 手动查看参数量
    net = FaceExpressionNet()
    print(f"参数量: {count_parameters(net):,}")
    print("输出形状:", tuple(net(torch.zeros(1, 3, 48, 48)).shape))