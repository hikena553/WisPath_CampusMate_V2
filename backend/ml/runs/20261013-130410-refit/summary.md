# 训练运行 20261013-130410-refit

## 模型与数据
- 架构: face_expression_net（从头训练）
- 参数量: 361,487
- 训练设备: NVIDIA GeForce RTX 3050 Laptop GPU（cuda），混合精度 AMP: True
- 数据集: FER2013（train 28709 / test 7178）
- 输入尺寸: 48×48，类别数: 7

## 关键超参数
- epochs=12, batch_size=256
- optimizer=adamw, lr=0.003, weight_decay=0.0005
- scheduler=cosine, warmup_epochs=1
- label_smoothing=0.1, aug(hflip=0.5, rot=12.0)
- init_weights=ml/runs/20261013-115245-strong/best_model.pt, freeze_backbone=False

## 结果
- 训练轮数: 12（早停耐心 0）
- 最佳验证准确率: 0.6777 @ epoch 5
- 测试集准确率: 0.6489
- 测试集 Top-2 准确率: 0.8256
- 测试集 Macro-F1: 0.5985 / Weighted-F1: 0.6446

## 产物
- `config.json` 完整配置
- `metrics.json` 全部指标（含混淆矩阵、每类 P/R/F1）
- `history.csv` 逐轮训练/验证指标
- `training_curves.png` 损失与准确率曲线
- `confusion_matrix.png` 混淆矩阵（计数）
- `confusion_matrix_normalized.png` 混淆矩阵（召回率归一化）
- `classification_report.txt` 分类报告
- `best_model.pt` 最佳权重