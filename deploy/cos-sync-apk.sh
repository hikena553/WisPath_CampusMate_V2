#!/usr/bin/env bash
# 定时兜底：把最新安装包同步到腾讯云 COS。
#
# 由 cron 每 5 分钟调用（见 /etc/cron.d/smartcampus-cos）：
#   */5 * * * * www /www/wwwroot/SmartCampus/deploy/cos-sync-apk.sh
#
# 行为：
#   - .cos.env 未配置 COS_SECRET_ID / COS_SECRET_KEY 时静默退出 0（未接入 COS 的机器无感）；
#   - flock 防并发，上一轮没跑完时本轮直接退出；
#   - 调用 frontend/scripts/publish-apk.mjs --sync，远端 latest.json 已是同一个包时会自行跳过上传；
#   - 输出追加到 <项目根>/logs/cos-sync.log（logs/ 已在 .gitignore 中忽略，不存在则自动创建）。

set -u

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.cos.env"
LOG_DIR="$PROJECT_ROOT/logs"
LOG_FILE="$LOG_DIR/cos-sync.log"
LOCK_FILE="$PROJECT_ROOT/.cos-sync.lock"
APK_FILE="$PROJECT_ROOT/apk/download/mian02.apk"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

# ---------- 1. 未配置密钥：静默退出 0（不产生日志噪音） ----------
if [ ! -f "$ENV_FILE" ]; then
  exit 0
fi
if ! grep -Eq '^[[:space:]]*COS_SECRET_ID[[:space:]]*=[[:space:]]*[^[:space:]]' "$ENV_FILE" 2>/dev/null; then
  exit 0
fi
if ! grep -Eq '^[[:space:]]*COS_SECRET_KEY[[:space:]]*=[[:space:]]*[^[:space:]]' "$ENV_FILE" 2>/dev/null; then
  exit 0
fi

# ---------- 2. 日志 ----------
mkdir -p "$LOG_DIR" 2>/dev/null || true
exec >>"$LOG_FILE" 2>&1

# ---------- 3. flock 防并发（拿不到锁说明上一轮仍在跑，直接退出） ----------
exec 9>"$LOCK_FILE" 2>/dev/null || exit 0
if ! flock -n 9; then
  echo "[$(date '+%F %T')] 上一轮同步仍在运行，跳过本轮"
  exit 0
fi

echo "[$(date '+%F %T')] ---- 开始 COS 安装包同步 ----"

if [ ! -f "$APK_FILE" ]; then
  echo "[$(date '+%F %T')] 未找到安装包：$APK_FILE，跳过"
  exit 0
fi

cd "$FRONTEND_DIR" || { echo "[$(date '+%F %T')] 无法进入 $FRONTEND_DIR"; exit 1; }

# cron 环境的 PATH 可能不含 node，这里显式兜底
NODE_BIN="$(command -v node 2>/dev/null || true)"
if [ -z "$NODE_BIN" ]; then
  for candidate in /usr/local/bin/node /usr/bin/node /opt/node/bin/node; do
    if [ -x "$candidate" ]; then
      NODE_BIN="$candidate"
      break
    fi
  done
fi
if [ -z "$NODE_BIN" ]; then
  echo "[$(date '+%F %T')] 未找到 node 可执行文件，跳过"
  exit 0
fi

# ---------- 4. 执行同步（--sync：远端已最新则脚本内部直接跳过上传） ----------
"$NODE_BIN" scripts/publish-apk.mjs --sync --apk "$APK_FILE"
STATUS=$?
if [ "$STATUS" -eq 0 ]; then
  echo "[$(date '+%F %T')] 同步完成（退出码 0）"
elif [ "$STATUS" -eq 2 ]; then
  echo "[$(date '+%F %T')] 跳过：COS 凭证未配置完整（退出码 2）"
else
  echo "[$(date '+%F %T')] 同步失败（退出码 $STATUS）"
fi

echo "[$(date '+%F %T')] ---- 结束 COS 安装包同步 ----"

if [ "$STATUS" -eq 0 ] || [ "$STATUS" -eq 2 ]; then
  exit 0
fi
exit "$STATUS"
