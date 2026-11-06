#!/usr/bin/env bash
# =============================================================================
# deploy/verify-cos-download.sh
#
# 只读验收脚本：检查「APK 本机下载 / COS 302 跳转」这条链路是否健康。
# 不修改任何配置、不 reload nginx、不上传任何东西。
#
# 用法:
#   deploy/verify-cos-download.sh          # 逐项 PASS/FAIL + 汇总，任一关键项失败退出 1
#   deploy/verify-cos-download.sh -h
#
# 检查项:
#   a. COS 对象（key 无 .apk 后缀）: HEAD 200 / Content-Type = application/octet-stream /
#      Content-Length 与本地 APK 大小一致 /
#      以及【真实 GET】200 且下载字节数 = 本地 APK 大小
#      —— COS 默认域名会放行 HEAD 却拦截真实 GET（403 DownloadForbidden），必须按字节验证
#   b. 本站 /download/mian02.apk HEAD:
#      未切换 -> 200 且大小 = 本地 APK（本机静态文件）
#      已切换 -> 302 且 Location 指向 COS
#   c. curl -sIL 跟随跳转后: 200 且 Content-Length = 本地 APK 大小
#   d. COS apk/latest.json: 可解析，sha256 = 本地 APK sha256
#   e. 汇总；任一关键项失败退出非 0
#
# 退出码: 0 全部通过 / 1 有失败项 / 2 用法错误
# =============================================================================
set -uo pipefail

# ----------------------------- 可修改配置 -----------------------------
COS_BUCKET="anzhuangbao-1441295645"
COS_REGION="ap-guangzhou"
COS_DOMAIN="https://anzhuangbao-1441295645.cos.ap-guangzhou.myqcloud.com"
# key 不带 .apk 后缀: COS 默认域名禁止匿名分发 .apk 后缀 / APK 类型的对象
# （HEAD 200 但真实 GET 403 DownloadForbidden），下载文件名由对象 Content-Disposition 的 filename* 提供。
COS_KEY="apk/mian02-latest"
COS_URL="$COS_DOMAIN/$COS_KEY"
LATEST_URL="$COS_DOMAIN/apk/latest.json"

LOCAL_APK="/www/wwwroot/SmartCampus/apk/download/mian02.apk"
VHOST="/www/server/panel/vhost/nginx/python_backend.conf"
SITE_HOSTS="https://www.mianxiaocheng.cn https://mianxiaocheng.cn"
PRIMARY_HOST="https://www.mianxiaocheng.cn"
SITE_PATH="/download/mian02.apk"
APK_CT="android.package-archive"
COS_CT_EXPECT="application/octet-stream"

PASS_N=0
FAIL_N=0

TMP=""
cleanup() {
  if [ -n "$TMP" ] && [ -d "$TMP" ]; then
    rm -rf -- "$TMP"
  fi
}
trap cleanup EXIT INT TERM

say()  { printf '%s\n' "$*"; }
pass() { PASS_N=$((PASS_N + 1)); printf '[PASS] %s\n' "$*"; }
fail() { FAIL_N=$((FAIL_N + 1)); printf '[FAIL] %s\n' "$*"; }
warn() { printf '[WARN] %s\n' "$*"; }
info() { printf '[INFO] %s\n' "$*"; }
die()  { printf 'ERROR: %s\n' "$*" >&2; exit 2; }

if [ "$#" -gt 0 ]; then
  case "$1" in
    -h|--help)
      say "用法: deploy/verify-cos-download.sh   （只读验收，不修改任何配置）"
      say "  检查 COS 对象 / 本站下载 / 跟随跳转 / latest.json，逐项 PASS/FAIL，失败退出 1"
      exit 0
      ;;
    *)
      die "未知参数: $1（-h 查看用法）"
      ;;
  esac
fi

TMP=$(mktemp -d /tmp/verify-cos-download.XXXXXX) || die "无法创建临时目录"

header_value() {
  printf '%s\n' "$1" | tr -d '\r' | awk -v name="$2" '
    BEGIN { want = tolower(name) ":" }
    {
      line = tolower($0)
      if (substr(line, 1, length(want)) == want) {
        v = $0
        sub(/^[^:]*:[ \t]*/, "", v)
        val = v
      }
    }
    END { print val }
  '
}

head_code() {
  local url hdrfile code
  url="$1"
  hdrfile="$2"
  code=$(curl -sS -o /dev/null -D "$hdrfile" -I --max-time 30 -w '%{http_code}' "$url" 2>/dev/null) || code="000"
  printf '%s' "$code"
}

follow_head_code() {
  local url hdrfile code
  url="$1"
  hdrfile="$2"
  code=$(curl -sS -o /dev/null -D "$hdrfile" -I -L --max-time 60 -w '%{http_code}' "$url" 2>/dev/null) || code="000"
  printf '%s' "$code"
}

say "=============================================================="
say " SmartCampus 安装包下载链路验收 (COS 302)"
say " 时间: $(date '+%Y-%m-%d %H:%M:%S %z')"
say " 主机: $(hostname 2>/dev/null || echo unknown)"
say "=============================================================="
say ""
say "目标 COS 对象 : $COS_URL"
say "目标最新清单  : $LATEST_URL"
say "本地 APK      : $LOCAL_APK"
say "线上下载地址  : $PRIMARY_HOST$SITE_PATH"
say ""

# ------------------------- 本地 APK 基线 -------------------------
LOCAL_SIZE=""
LOCAL_SHA=""
if [ -f "$LOCAL_APK" ]; then
  LOCAL_SIZE=$(stat -c '%s' -- "$LOCAL_APK" 2>/dev/null) || LOCAL_SIZE=""
  LOCAL_SHA=$(sha256sum -- "$LOCAL_APK" 2>/dev/null | cut -d' ' -f1) || LOCAL_SHA=""
  if [ -n "$LOCAL_SIZE" ] && [ -n "$LOCAL_SHA" ]; then
    info "本地 APK: $LOCAL_SIZE 字节, sha256=$LOCAL_SHA"
  else
    warn "本地 APK 存在但读取大小/sha256 失败: $LOCAL_APK"
  fi
else
  warn "本地 APK 不存在: $LOCAL_APK（依赖它的检查项会失败）"
fi
say ""

# ------------------------- a. COS 对象（HEAD + 真实 GET） -------------------------
say "--- a. COS 对象（HEAD + 真实 GET） ---"
COS_CODE=$(head_code "$COS_URL" "$TMP/cos.hdr")
COS_CT=$(header_value "$(cat -- "$TMP/cos.hdr" 2>/dev/null)" "Content-Type")
COS_LEN=$(header_value "$(cat -- "$TMP/cos.hdr" 2>/dev/null)" "Content-Length")
COS_CD=$(header_value "$(cat -- "$TMP/cos.hdr" 2>/dev/null)" "Content-Disposition")

if [ "$COS_CODE" = "200" ]; then
  pass "a1 COS 对象 HEAD 200: $COS_URL"
else
  fail "a1 COS 对象 HEAD 期望 200，实际 HTTP $COS_CODE（未上传 / 非 public-read / 桶策略限制）"
fi

case "$COS_CT" in
  *"$COS_CT_EXPECT"*)
    pass "a2 COS Content-Type = $COS_CT"
    ;;
  *)
    if [ -n "$COS_CT" ]; then
      fail "a2 COS Content-Type = $COS_CT，期望 $COS_CT_EXPECT（APK 类型会被默认域名拦截）"
    else
      fail "a2 COS Content-Type 缺失（对象不可读）"
    fi
    ;;
esac

if [ -n "$LOCAL_SIZE" ] && [ -n "$COS_LEN" ]; then
  if [ "$COS_LEN" = "$LOCAL_SIZE" ]; then
    pass "a3 COS Content-Length = $COS_LEN，与本地 APK 一致"
  else
    fail "a3 COS Content-Length = $COS_LEN，与本地 APK $LOCAL_SIZE 不一致"
  fi
else
  fail "a3 无法比对大小（COS Content-Length=$COS_LEN，本地=$LOCAL_SIZE）"
fi

if [ -n "$COS_CD" ]; then
  info "COS Content-Disposition: $COS_CD"
fi

# 最关键: HEAD 200 不代表能下载。COS 默认域名对 .apk 后缀 / APK 类型对象
# 返回 HEAD 200 + GET 403 DownloadForbidden，必须真实下载一遍并按字节数校验。
GET_RES=$(curl -sS -o /dev/null --max-time 180 -w '%{http_code} %{size_download}' "$COS_URL" 2>/dev/null) || GET_RES="000 0"
GET_CODE=$(printf '%s' "$GET_RES" | awk '{print $1}')
GET_SIZE=$(printf '%s' "$GET_RES" | awk '{print $2}')

if [ "$GET_CODE" = "200" ]; then
  pass "a4 COS 真实 GET 200（放行验证：HEAD 通过不等于能下载）"
else
  fail "a4 COS 真实 GET 期望 200，实际 HTTP $GET_CODE（403 = 默认域名拒绝分发 .apk 后缀/APK 类型对象）"
fi

if [ -n "$LOCAL_SIZE" ] && [ -n "$GET_SIZE" ]; then
  if [ "$GET_SIZE" = "$LOCAL_SIZE" ]; then
    pass "a5 COS 真实下载字节数 = $GET_SIZE，与本地 APK 一致"
  else
    fail "a5 COS 真实下载字节数 = $GET_SIZE，与本地 APK $LOCAL_SIZE 不一致"
  fi
else
  fail "a5 无法比对下载字节数（下载=$GET_SIZE，本地=$LOCAL_SIZE）"
fi

# 软校验（只 WARN，不影响退出码）: Content-Disposition 必须是 attachment + 仅 filename*，
# 带 filename="..." 会被 COS 默认域名判 403。
if [ -n "$COS_CD" ]; then
  case "$COS_CD" in
    *"filename*=UTF-8''"*)
      case "$COS_CD" in
        *'filename="'*)
          warn "Content-Disposition 同时带了 filename=\"...\"，COS 默认域名会 403；只保留 filename*"
          ;;
        *)
          pass "a6 Content-Disposition 仅 filename*，下载文件名 = SmartCampus.apk"
          ;;
      esac
      ;;
    *)
      warn "Content-Disposition = $COS_CD，期望 attachment; filename*=UTF-8''mian02.apk（浏览器可能存成 apk/mian02-latest）"
      ;;
  esac
else
  warn "COS 未返回 Content-Disposition，浏览器可能把文件存成 apk/mian02-latest 而不是 mian02.apk"
fi
say ""

# ------------------------- b. 本站 HEAD -------------------------
say "--- b. 本站 $SITE_PATH HEAD ---"
MARK_ON=0
VHOST_READABLE=0
if [ -r "$VHOST" ]; then
  VHOST_READABLE=1
elif sudo -n true 2>/dev/null; then
  VHOST_READABLE=1
fi
if [ "$VHOST_READABLE" = "1" ]; then
  VC=""
  if [ -r "$VHOST" ]; then
    VC=$(cat -- "$VHOST" 2>/dev/null) || VC=""
  else
    VC=$(sudo -n cat -- "$VHOST" 2>/dev/null) || VC=""
  fi
  if printf '%s\n' "$VC" | grep -qE '^# >>> smartcampus-cos-download'; then
    MARK_ON=1
  fi
  if [ "$MARK_ON" = "1" ]; then
    info "vhost 中检测到托管标记块（期望 302）"
  else
    info "vhost 中未检测到托管标记块（期望本机 200）"
  fi
else
  info "无法读取 vhost（权限不足），仅按 HTTP 响应判断当前模式"
fi

SITE_CODE=$(head_code "$PRIMARY_HOST$SITE_PATH" "$TMP/site.hdr")
SITE_LOC=$(header_value "$(cat -- "$TMP/site.hdr" 2>/dev/null)" "Location")
SITE_LEN=$(header_value "$(cat -- "$TMP/site.hdr" 2>/dev/null)" "Content-Length")

MODE="unknown"
if [ "$SITE_CODE" = "302" ]; then
  MODE="cos-302"
  case "$SITE_LOC" in
    "$COS_URL")
      pass "b1 本站返回 302，Location 精确指向新对象: $SITE_LOC"
      ;;
    "$COS_DOMAIN"/*)
      fail "b1 本站返回 302，但 Location 指向旧/其它对象: $SITE_LOC（期望 $COS_URL）"
      ;;
    *)
      fail "b1 本站返回 302，但 Location 不是 COS: $SITE_LOC"
      ;;
  esac
elif [ "$SITE_CODE" = "200" ]; then
  MODE="local"
  if [ -n "$LOCAL_SIZE" ] && [ -n "$SITE_LEN" ] && [ "$SITE_LEN" = "$LOCAL_SIZE" ]; then
    pass "b1 本站返回 200（本机静态文件，尚未切换），大小 $SITE_LEN 与本地一致"
  else
    fail "b1 本站返回 200 但大小异常（响应=$SITE_LEN，本地=$LOCAL_SIZE）"
  fi
else
  fail "b1 本站 HEAD 期望 200 或 302，实际 HTTP $SITE_CODE"
fi
say ""

# ------------------------- c. 端到端跟随跳转 -------------------------
say "--- c. 端到端跟随跳转（站点 -> COS） ---"
FINAL_CODE=$(follow_head_code "$PRIMARY_HOST$SITE_PATH" "$TMP/final.hdr")
FINAL_LEN=$(header_value "$(cat -- "$TMP/final.hdr" 2>/dev/null)" "Content-Length")
FINAL_CT=$(header_value "$(cat -- "$TMP/final.hdr" 2>/dev/null)" "Content-Type")

if [ "$FINAL_CODE" = "200" ]; then
  pass "c1 跟随跳转后 HEAD 200"
else
  fail "c1 跟随跳转后 HEAD 期望 200，实际 HTTP $FINAL_CODE"
fi

if [ -n "$LOCAL_SIZE" ] && [ -n "$FINAL_LEN" ]; then
  if [ "$FINAL_LEN" = "$LOCAL_SIZE" ]; then
    pass "c2 最终 Content-Length = $FINAL_LEN，与本地 APK 一致"
  else
    fail "c2 最终 Content-Length = $FINAL_LEN，与本地 APK $LOCAL_SIZE 不一致"
  fi
else
  fail "c2 无法比对最终大小（响应=$FINAL_LEN，本地=$LOCAL_SIZE）"
fi

if [ -n "$FINAL_CT" ]; then
  info "最终 Content-Type: $FINAL_CT"
fi

# 端到端真实下载只取 1 字节，确认「站点 302 -> COS」整条链没有被 403 拦住。
E2E_RES=$(curl -sS -o /dev/null -L -r 0-0 --max-time 90 -w '%{http_code} %{num_redirects}' "$PRIMARY_HOST$SITE_PATH" 2>/dev/null) || E2E_RES="000 0"
E2E_CODE=$(printf '%s' "$E2E_RES" | awk '{print $1}')
E2E_HOPS=$(printf '%s' "$E2E_RES" | awk '{print $2}')
case "$E2E_CODE" in
  200|206)
    pass "c3 端到端真实 GET 可下载（HTTP $E2E_CODE，重定向 $E2E_HOPS 次）"
    ;;
  *)
    fail "c3 端到端真实 GET 期望 200/206，实际 HTTP $E2E_CODE（跳转链被拒）"
    ;;
esac
say ""

# ------------------------- d. latest.json -------------------------
say "--- d. COS apk/latest.json ---"
LATEST_CODE=$(curl -sS --max-time 30 -o "$TMP/latest.json" -w '%{http_code}' "$LATEST_URL" 2>/dev/null) || LATEST_CODE="000"

if [ "$LATEST_CODE" != "200" ]; then
  fail "d1 取 latest.json 期望 200，实际 HTTP $LATEST_CODE（$LATEST_URL）"
else
  if [ -s "$TMP/latest.json" ]; then
    REMOTE_SHA=""
    if command -v python3 >/dev/null 2>&1; then
      REMOTE_SHA=$(python3 - "$TMP/latest.json" <<'PY' 2>/dev/null
import json
import sys

try:
    with open(sys.argv[1], encoding="utf-8") as fh:
        data = json.load(fh)
except Exception:
    sys.exit(3)

print(str(data.get("sha256") or "").strip().lower())
PY
) || REMOTE_SHA=""
      REMOTE_SHA=$(printf '%s' "$REMOTE_SHA" | tail -n 1 | tr -d '[:space:]')
    fi
    if [ -z "$REMOTE_SHA" ]; then
      REMOTE_SHA=$(sed -n 's/.*"sha256"[[:space:]]*:[[:space:]]*"\([0-9a-fA-F]*\)".*/\1/p' "$TMP/latest.json" | head -n 1 | tr 'A-F' 'a-f')
    fi
    if [ -z "$REMOTE_SHA" ]; then
      fail "d1 latest.json 解析失败或缺少 sha256 字段"
    elif [ -n "$LOCAL_SHA" ] && [ "$REMOTE_SHA" = "$LOCAL_SHA" ]; then
      pass "d1 latest.json sha256 与本地 APK 一致: $REMOTE_SHA"
    else
      fail "d1 latest.json sha256 = $REMOTE_SHA，本地 APK = $LOCAL_SHA（不一致）"
    fi
    REMOTE_SIZE=$(sed -n 's/.*"size"[[:space:]]*:[[:space:]]*\([0-9][0-9]*\).*/\1/p' "$TMP/latest.json" | head -n 1)
    if [ -n "$REMOTE_SIZE" ] && [ -n "$LOCAL_SIZE" ]; then
      if [ "$REMOTE_SIZE" = "$LOCAL_SIZE" ]; then
        pass "d2 latest.json size = $REMOTE_SIZE，与本地 APK 一致"
      else
        fail "d2 latest.json size = $REMOTE_SIZE，与本地 APK $LOCAL_SIZE 不一致"
      fi
    fi
    REMOTE_VER=$(sed -n 's/.*"versionName"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$TMP/latest.json" | head -n 1)
    if [ -n "$REMOTE_VER" ]; then
      info "latest.json versionName: $REMOTE_VER"
    fi
    REMOTE_URL=$(sed -n 's/.*"url"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$TMP/latest.json" | head -n 1)
    if [ -n "$REMOTE_URL" ]; then
      case "$REMOTE_URL" in
        "$COS_URL")
          pass "d3 latest.json url 指向当前对象: $REMOTE_URL"
          ;;
        *)
          warn "latest.json url = $REMOTE_URL，与当前对象 $COS_URL 不一致（发布脚本需更新该字段）"
          ;;
      esac
    fi
  else
    fail "d1 latest.json 响应为空"
  fi
fi
say ""

# ------------------------- e. 汇总 -------------------------
say "=============================================================="
say " 当前模式: $MODE （cos-302 = 已切到 COS；local = 仍走本机文件）"
say " 汇总: PASS=$PASS_N  FAIL=$FAIL_N"
if [ "$FAIL_N" -gt 0 ]; then
  say " 结果: FAIL（有 $FAIL_N 项未通过）"
  say ""
  say " 常见原因:"
  say "   - COS 相关项失败: 对象还没上传，或没设 public-read（匿名 HEAD 403/404）"
  say "   - latest.json 失败: 还没跑过 npm run apk:publish"
  say "   - 此时线上仍是本机 200，用户下载不受影响，可先回滚/暂不切换"
  say "=============================================================="
  exit 1
fi
say " 结果: PASS（全部关键项通过）"
say "=============================================================="
exit 0
