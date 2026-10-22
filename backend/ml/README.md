# FaceExpressionNet 训练 / 微调模块

复现前端 `face-api.js` 表情识别网络（`faceExpressionNet`）的**技术路线**，
在 FER2013 上做从头训练与微调，并把训练过程指标（准确率、混淆矩阵、
分类报告、训练曲线）落盘，供后端 API 与报告读取。

> 说明：`face-api.js` 官方权重是 TF.js **量化分片**（uint8 + scale/min）格式，
> 且未公开逐层 stride/padding，无法无损导入。本模块复现同一技术族
> （MobileNet 风格**深度可分离卷积 + 稠密卷积块**），支持：
> 1）从头训练；2）基于本项目 checkpoint 继续**微调**（transfer learning）。

## 目录结构

```
backend/ml/
├── 核心训练
│   ├── architectures.py   # FaceExpressionNet（深度可分离 CNN）+ 通道对齐官方 manifest
│   ├── backbones.py       # 迁移学习骨干（mobilenet_v3 / efficientnet_b0 / resnet18）
│   ├── config.py          # 全部超参数（TrainingConfig）
│   ├── dataset.py         # FER2013 / RAF-DB 解析 + 数据增强
│   ├── losses.py          # Focal / 标签平滑等损失
│   ├── metrics.py         # 混淆矩阵 / P-R-F1 / Top-k（纯 numpy）
│   ├── artifacts.py       # 曲线图、混淆矩阵图、指标 JSON、报告落盘
│   └── train.py           # 训练主流程（含早停、分组学习率、AMP、微调）
├── 训练配方
│   └── configs/*.json     # improved / strong / transfer / rafmix* 等实验配置
├── 数据集构建
│   ├── ferplus.py         # FER+ 标签清洗与合并集
│   ├── real_fer.py        # 真实场景测试集（FER/RAF）
│   ├── remote_parquet.py  # 远程 parquet 分片读取（AffectNet 演示）
│   ├── face_detect_data.py# 合成人脸检测训练数据
│   ├── wider_to_yolo.py   # WIDER FACE → YOLO 格式
│   └── train_yolo_face.py # 人脸检测器（YOLOv8n 单类）训练
├── 评估与分析（一次性实验脚本）
│   ├── eval_checkpoints.py / eval_extra.py / eval_blend.py
│   ├── ensemble.py        # 多模型加权集成
│   ├── faceapi_eval.py    # 与 face-api.js 同口径对比
│   ├── smoother_eval.py / error_analysis.py / denoise.py
│   └── face_pipeline.py   # 检测+分类串联链路
├── 浏览器端验证
│   ├── e2e_emotion.py     # 端到端回放（file / realtime）
│   ├── make_selftest.py   # 生成自测样本
│   └── fake_camera.py     # 合成摄像头测试流
├── export_onnx.py         # 导出前端运行时 ONNX（产物在 frontend/public/models/）
├── requirements-train.txt
├── runs/<run_id>/         # 训练/评估产物（生成物，不入库，见 .gitignore）
└── data/                  # FER2013 / RAF-DB / FER+ / AffectNet / 检测数据（生成物，不入库）
```

## 环境

训练使用本项目既有的 conda 环境 **`aistudy`**（已内置 GPU 版 PyTorch），
**无需重新安装 PyTorch**：

```powershell
& 'D:\conda\envs\aistudy\python.exe' -c "import torch; print(torch.__version__, torch.cuda.is_available())"
# 期望：2.12.0+cu126  True
```

若在其它环境运行，只需保证 `torch / numpy / pillow / matplotlib` 可用
（见 `requirements-train.txt`）。训练依赖与 Web 运行时解耦，FastAPI 不需要 torch。

## 训练 / 微调

在 `backend` 目录下执行（用 `aistudy` 的 python）：

```powershell
cd backend

# 1) 从头训练（默认 40 epoch，warmup + cosine、类别加权、标签平滑、数据增强、GPU + AMP）
& 'D:\conda\envs\aistudy\python.exe' -m ml.train --run-name full

# 1b) 更强配方（更大宽度 1.25 + 70 轮 + RandomErasing + EMA + TTA，精度更高）
& 'D:\conda\envs\aistudy\python.exe' -m ml.train --config ml/configs/strong.json --run-name strong

# 2) 快速冒烟（2000 样本 / 2 epoch，验证链路）
& 'D:\conda\envs\aistudy\python.exe' -m ml.train --smoke
```

### 提升精度的手段

| 手段 | 参数 | 作用 |
| --- | --- | --- |
| 更宽网络 | `width_mult=1.25` | 增加通道容量 |
| 更长训练 | `epochs=70`（配合 cosine 退火到 0） | 充分收敛 |
| RandomErasing | `random_erase_prob=0.3` | 随机遮挡，抑制过拟合 |
| 权重平均 EMA | `ema_decay=0.999` | 评测用滑动平均权重，稳定提分 |
| 测试时增强 TTA | `tta=true` | 原图 + 水平翻转平均 logits |
| 正则调整 | `label_smoothing=0.1`、`weight_decay=5e-4`、`dropout=0.3` | 抑制过自信与过拟合 |
| 类别权重 | `use_class_weight=false` | 面向总体准确率（不再为长尾类牺牲多数类） |
| MixUp（可选） | `mixup_alpha` | >0 启用批内线性混合 |

上述"强配方"见 `backend/ml/configs/strong.json`，可用 `--config` 直接复用。

### 迁移学习（突破从头训练天花板）

FER2013 上从头训练通常止步 65-68%。用 ImageNet 预训练骨干替换分类头微调，
可进一步提升。已支持 `mobilenet_v3_small / mobilenet_v3_large / efficientnet_b0 / resnet18`：

```powershell
# 迁移学习：mobilenet_v3_small + ImageNet 预训练 + 96px + MixUp/EMA/TTA
& 'D:\conda\envs\aistudy\python.exe' -m ml.train --config ml/configs/transfer2.json --run-name transfer2
```

关键参数：`model_name`、`pretrained=true`、`imagenet_norm=true`、`input_size`。
小数据集微调必须配合**更低学习率 + 更强正则**（见 `configs/transfer2.json`：
lr 1e-4 / head 5e-4、weight_decay 1e-3、dropout 0.4、RandomErasing 0.35、MixUp 0.2），
否则预训练模型会迅速过拟合（训练准确率 0.85 而验证停在 0.60）。

### 多模型集成

```powershell
& 'D:\conda\envs\aistudy\python.exe' -m ml.ensemble `
    --runs <run_id_strong> <run_id_transfer2> --name ensemble
```

按各模型验证准确率加权做概率平均（各带 TTA），结果写入 `runs/<ts>-ensemble/`。
自训练模型（48px、[-1,1] 归一化）与迁移模型（96px、ImageNet 归一化）可混合集成。

```powershell
# 3) 基于已训练权重微调（更小学习率）
& 'D:\conda\envs\aistudy\python.exe' -m ml.train --init-weights ml/runs/<run_id>/best_model.pt `
    --finetune-lr 3e-4 --epochs 12 --run-name finetune

# 4) 只训练分类头（linear probe，冻结主干）
& 'D:\conda\envs\aistudy\python.exe' -m ml.train --init-weights ml/runs/<run_id>/best_model.pt `
    --freeze-backbone --finetune-lr 2e-4 --run-name linear_probe
```

数据集首次运行会自动从镜像 `hf-mirror.com` 下载到 `backend/ml/data/fer2013/`。

## 产物（`runs/<run_id>/`）

| 文件 | 说明 |
| --- | --- |
| `config.json` | 本次训练的完整超参数快照 |
| `metrics.json` | 验证/测试全部指标（含混淆矩阵、每类 P/R/F1、Top-2/3） |
| `history.csv` | 逐轮 train/val loss 与 accuracy、学习率 |
| `training_curves.png` | 损失与准确率曲线（标注最佳验证轮次） |
| `confusion_matrix.png` | 混淆矩阵（计数） |
| `confusion_matrix_normalized.png` | 混淆矩阵（按行归一化 = 召回率） |
| `classification_report.txt` | 分类报告（precision/recall/f1/support） |
| `best_model.pt` | 最佳验证准确率权重（微调可复用） |
| `summary.md` | 本次运行摘要（技术、参数、结果） |

## 后端查询接口

训练产物通过 FastAPI 只读接口暴露（需管理员权限，不依赖 torch）：

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/ml/runs` | 列出全部训练运行与关键指标 |
| GET | `/api/ml/runs/{run_id}` | 读取某次运行完整 `metrics.json` |
| GET | `/api/ml/runs/{run_id}/file/{name}` | 下载产物（白名单，含曲线/混淆矩阵图） |
| POST | `/api/ml/train` | 发起训练/微调（后台线程，需目标机装有 torch） |
| GET | `/api/ml/jobs/{job_id}` | 查询后台训练任务进度 |