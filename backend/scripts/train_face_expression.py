"""便捷入口：训练 / 微调人脸表情识别模型。

等价于在 backend 目录下执行 `python -m ml.train`，但可在任意工作目录运行：
  python backend/scripts/train_face_expression.py --smoke
  python backend/scripts/train_face_expression.py --epochs 30
"""
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from ml.train import main  # noqa: E402

if __name__ == "__main__":
    main()