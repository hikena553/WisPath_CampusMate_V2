"""FER2013 数据集加载与数据增强。

数据来源：HuggingFace 镜像 hf-mirror.com 上的 Jeneral/fer-2013
（原始 FER2013：48×48 灰度人脸，7 类表情），文件为 pickle 序列化的
[{img_bytes, labels}, ...]，本项目自动下载并解析。

标签映射（对齐前端 EMOTION_LABELS 的 7 类）：
  fer: angry/disgust/fear/happy/neutral/sad/surprise
  ->  angry/disgusted/fearful/happy/neutral/sad/surprised
"""
from __future__ import annotations

import io
import math
import pickle
import random
import urllib.request
from pathlib import Path
from typing import Callable, Optional

import numpy as np
import torch
from PIL import Image, ImageEnhance
from torch.utils.data import Dataset

from .architectures import CLASS_NAMES
from .config import TrainingConfig

# FER2013 原始字符串标签 -> 本项目类序索引
FER_LABEL_MAP = {
    "angry": 0,
    "disgust": 1,
    "fear": 2,
    "happy": 3,
    "neutral": 4,
    "sad": 5,
    "surprise": 6,
}
_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/122.0 Safari/537.36")


def _download(url: str, dst: Path) -> None:
    if dst.exists() and dst.stat().st_size > 0:
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=180) as r, open(dst, "wb") as f:
        while True:
            chunk = r.read(1024 * 256)
            if not chunk:
                break
            f.write(chunk)


def ensure_dataset(cfg: TrainingConfig) -> tuple[Path, Path]:
    """确保 train.pt / test.pt 就绪，返回 (train_path, test_path)。"""
    data_dir = Path(cfg.data_dir)
    train_p, test_p = data_dir / "train.pt", data_dir / "test.pt"
    if not (train_p.exists() and test_p.exists()):
        _download(f"{cfg.hf_mirror}/train.pt", train_p)
        _download(f"{cfg.hf_mirror}/test.pt", test_p)
    return train_p, test_p


def _load_split(path: Path) -> list[dict]:
    with open(path, "rb") as f:
        return pickle.load(f)


def _base_image(img_bytes: bytes, size: int) -> Image.Image:
    """JPEG bytes -> 灰度 PIL 图，并统一到 size×size。"""
    img = Image.open(io.BytesIO(img_bytes)).convert("L")
    if img.size != (size, size):
        img = img.resize((size, size), Image.BILINEAR)
    return img


def _augment(img: Image.Image, size: int, cfg: TrainingConfig) -> Image.Image:
    """随机增强：水平翻转 / 旋转平移 / 缩放裁切 / 亮度抖动。"""
    if random.random() < cfg.aug_hflip:
        img = img.transpose(Image.FLIP_LEFT_RIGHT)
    if cfg.aug_rotation > 0:
        ang = random.uniform(-cfg.aug_rotation, cfg.aug_rotation)
        dx = random.uniform(-cfg.aug_translate, cfg.aug_translate) * size
        dy = random.uniform(-cfg.aug_translate, cfg.aug_translate) * size
        img = img.rotate(ang, resample=Image.BILINEAR, translate=(dx, dy), fillcolor=0)
    if cfg.aug_scale > 0:
        f = random.uniform(max(0.5, 1 - cfg.aug_scale), 1.0)
        cw = int(size * f)
        x0 = random.randint(0, size - cw)
        y0 = random.randint(0, size - cw)
        img = img.crop((x0, y0, x0 + cw, y0 + cw)).resize((size, size), Image.BILINEAR)
    if cfg.aug_brightness > 0:
        factor = random.uniform(1 - cfg.aug_brightness, 1 + cfg.aug_brightness)
        img = ImageEnhance.Brightness(img).enhance(factor)
    return img


IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


def _to_array(img: Image.Image, cfg: TrainingConfig) -> np.ndarray:
    """PIL 灰度图 -> float32 数组 [3, size, size]。

    - 默认：归一化到 [-1, 1]（mean=std=0.5），适用于自训练网络；
    - imagenet_norm=True：按 ImageNet 均值/方差归一化，与预训练骨干匹配（迁移学习）。
    """
    arr = np.asarray(img, dtype=np.float32) / 255.0
    arr = np.repeat(arr[None, :, :], 3, axis=0)          # 灰度 -> 3 通道
    if cfg.imagenet_norm:
        return (arr - IMAGENET_MEAN[:, None, None]) / IMAGENET_STD[:, None, None]
    return (arr - 0.5) / 0.5


def _random_erase(arr: np.ndarray, cfg: TrainingConfig) -> np.ndarray:
    """RandomErasing：以一定概率随机擦除一个矩形区域（填灰）。

    归一化后 0.0 对应像素灰度 0.5，因此填 0 相当于置灰；该方法能迫使模型
    不过度依赖局部纹理，是提升泛化与精度的常用正则手段。
    """
    if cfg.random_erase_prob <= 0 or random.random() >= cfg.random_erase_prob:
        return arr
    size = arr.shape[1]
    area = size * size
    for _ in range(10):
        target = random.uniform(cfg.random_erase_min, cfg.random_erase_max) * area
        ratio = random.uniform(0.3, 3.3)
        h = int(round((target * ratio) ** 0.5))
        w = int(round((target / ratio) ** 0.5))
        if 0 < h < size and 0 < w < size:
            y0 = random.randint(0, size - h)
            x0 = random.randint(0, size - w)
            arr[:, y0:y0 + h, x0:x0 + w] = 0.0
            return arr
    return arr


class FER2013Dataset(Dataset):
    """FER2013 torch 数据集。

    preload=True 时在初始化阶段把每张图的灰度图预解码为 uint8 数组常驻内存
    （约 28k×48×48 ≈ 66MB），每轮只做廉价增强，避免重复 JPEG 解码拖慢训练。
    """

    def __init__(self, records: list[dict], cfg: TrainingConfig, augment: bool = False) -> None:
        self.records = records
        self.cfg = cfg
        self.augment = augment
        self.cache: list[np.ndarray] | None = None
        if cfg.preload:
            self.cache = [
                np.asarray(_base_image(r["img_bytes"], cfg.input_size), dtype=np.uint8)
                for r in records
            ]

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, int]:
        rec = self.records[idx]
        label = FER_LABEL_MAP[rec["labels"]]
        if self.cache is not None:
            img = Image.fromarray(self.cache[idx], mode="L")
        else:
            img = _base_image(rec["img_bytes"], self.cfg.input_size)
        if self.augment:
            img = _augment(img, self.cfg.input_size, self.cfg)
        arr = _to_array(img, self.cfg)
        if self.augment:
            arr = _random_erase(arr, self.cfg)
        return torch.from_numpy(arr), label


def build_datasets(cfg: TrainingConfig, seed: int | None = None) -> tuple[FER2013Dataset, FER2013Dataset, FER2013Dataset]:
    """构建 (train, val, test)。train 内部按 val_split 划分验证集。"""
    train_p, test_p = ensure_dataset(cfg)
    train_recs = _load_split(train_p)
    test_recs = _load_split(test_p)

    if cfg.max_samples and cfg.max_samples > 0:
        train_recs = train_recs[: cfg.max_samples]
        test_recs = test_recs[: max(1, cfg.max_samples // 4)]

    if cfg.train_on_all:
        # 全量重训：验证集并入训练，抽取少量样本仅供日志观测（不参与选优）
        train_set = FER2013Dataset(train_recs, cfg, augment=True)
        val_set = FER2013Dataset(train_recs[:512], cfg, augment=False)
        test_set = FER2013Dataset(test_recs, cfg, augment=False)
        return train_set, val_set, test_set

    rng = random.Random(cfg.seed if seed is None else seed)
    idx = list(range(len(train_recs)))
    rng.shuffle(idx)
    n_val = int(len(idx) * cfg.val_split)
    val_idx, train_idx = set(idx[:n_val]), idx[n_val:]

    train_set = FER2013Dataset([train_recs[i] for i in train_idx], cfg, augment=True)
    val_set = FER2013Dataset([train_recs[i] for i in sorted(val_idx)], cfg, augment=False)
    test_set = FER2013Dataset(test_recs, cfg, augment=False)
    return train_set, val_set, test_set


def compute_class_weights(records: list[dict], num_classes: int = 7) -> torch.Tensor:
    """按类别频次计算反比权重（归一化到均值 1），缓解 disgust 等长尾类。"""
    counts = np.zeros(num_classes, dtype=np.float64)
    for r in records:
        counts[FER_LABEL_MAP[r["labels"]]] += 1
    counts = np.maximum(counts, 1.0)
    weights = counts.sum() / (counts * num_classes)
    return torch.tensor(weights, dtype=torch.float32)


def dataset_stats(cfg: TrainingConfig) -> dict:
    """数据集规模与类别分布（用于报告）。"""
    train_p, test_p = ensure_dataset(cfg)
    out = {}
    for name, p in (("train", train_p), ("test", test_p)):
        recs = _load_split(p)
        dist = {CLS: 0 for CLS in CLASS_NAMES}
        for r in recs:
            dist[CLASS_NAMES[FER_LABEL_MAP[r["labels"]]]] += 1
        out[name] = {"total": len(recs), "distribution": dist}
    return out