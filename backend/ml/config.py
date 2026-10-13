"""训练 / 微调超参数配置。

所有"调的参数"集中在此，便于复现与调参对照；配置会随训练产物一起落盘
（runs/<run_id>/config.json），保证每次实验结果可追溯。
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

# 固定的实验根目录（训练产物统一落盘）
RUNS_DIR = Path(__file__).resolve().parent / "runs"
# 数据集缓存目录（FER2013 的 train.pt / test.pt）
DATA_DIR = Path(__file__).resolve().parent / "data" / "fer2013"


@dataclass
class TrainingConfig:
    # ---------- 数据 ----------
    data_dir: str = str(DATA_DIR)
    # 数据集下载源（HuggingFace 镜像，国内可直连；GitHub 与 huggingface.co 被网络屏蔽）
    hf_mirror: str = "https://hf-mirror.com/datasets/Jeneral/fer-2013/resolve/main"
    input_size: int = 48          # FER2013 原图即 48×48
    in_channels: int = 3          # 灰度复制为 3 通道，与 face-api.js 一致
    num_classes: int = 7
    val_split: float = 0.1        # 从 train 切出的验证集比例
    num_workers: int = 0          # Windows 下取 0，避免子进程反复重建
    preload: bool = True          # 预解码全部图片到内存（uint8），加速每轮增强
    max_samples: int = 0          # >0 时限制样本数，用于快速冒烟测试

    # ---------- 模型 ----------
    model_name: str = "face_expression_net"  # 或 torchvision 骨干：mobilenet_v3_small 等（迁移学习）
    pretrained: bool = False      # 是否加载 ImageNet 预训练权重（迁移学习建议 True）
    imagenet_norm: bool = False   # 是否用 ImageNet 均值/方差归一化（迁移学习建议 True）
    width_mult: float = 1.0
    dropout: float = 0.2

    # ---------- 优化 ----------
    epochs: int = 40
    batch_size: int = 256
    lr: float = 2e-3              # 主干初始学习率（AdamW）
    head_lr_mult: float = 3.0     # 分类头学习率倍数（微调时头部更快收敛）
    backbone_lr_mult: float = 1.0
    weight_decay: float = 1e-4
    optimizer: str = "adamw"      # adamw | sgd
    momentum: float = 0.9         # sgd 专用
    scheduler: str = "cosine"     # cosine | step | none
    warmup_epochs: int = 2
    min_lr: float = 1e-5
    label_smoothing: float = 0.05
    grad_clip: float = 5.0
    use_class_weight: bool = True # 按类别频次加权，缓解 disgust 等长尾类
    amp: bool = True              # 混合精度（仅在 CUDA 生效，CPU 自动关闭）

    # ---------- 数据增强 ----------
    aug_hflip: float = 0.5        # 水平翻转概率
    aug_rotation: float = 10.0    # 随机旋转角度上限
    aug_translate: float = 0.1    # 随机平移比例
    aug_brightness: float = 0.2   # 亮度抖动幅度
    aug_scale: float = 0.1        # 随机缩放幅度

    # RandomErasing（随机擦除）：训练时随机遮挡一小块，抑制过拟合、提升鲁棒性
    random_erase_prob: float = 0.0
    random_erase_min: float = 0.02
    random_erase_max: float = 0.20
    # MixUp：批内线性混合（alpha>0 启用）
    mixup_alpha: float = 0.0
    # 权重指数滑动平均（EMA）：0 表示关闭，常用 0.999，通常可稳定提升精度
    ema_decay: float = 0.0
    # 测试时增强（水平翻转后平均 logits）
    tta: bool = False

    # ---------- 微调 ----------
    init_weights: str = ""        # 载入已有 checkpoint 做微调（transfer learning）
    freeze_backbone: bool = False # 冻结主干，仅训练分类头（linear probe）
    finetune_lr: float = 0.0      # >0 时覆盖 lr，用于微调的更小学习率

    # ---------- 训练控制 ----------
    early_stop_patience: int = 8  # 验证集 accuracy 连续无提升的容忍轮数
    train_on_all: bool = False    # True 时把验证集并入训练（全量重训/精调），不再做验证集选优
    seed: int = 42
    run_name: str = ""            # 产物目录名后缀，便于区分实验
    device: str = "auto"          # auto | cpu | cuda

    def to_dict(self) -> dict:
        return asdict(self)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "TrainingConfig":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})

    @classmethod
    def from_kwargs(cls, **kwargs) -> "TrainingConfig":
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in kwargs.items() if k in known and v is not None})