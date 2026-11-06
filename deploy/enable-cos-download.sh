#!/usr/bin/env bash
# =============================================================================
# deploy/enable-cos-download.sh
#
# 把线上 /download/mian02.apk 从「本机静态文件」无感切换为
# 「302 跳转到腾讯云 COS」。只改 nginx vhost 里的一个 exact-match location。
#
# 用法:
#   bash deploy/enable-cos-download.sh --dry-run  [--vhost PATH]   只打印 diff，不改文件
#   bash deploy/enable-cos-download.sh --status   [--vhost PATH]   只读状态检查
#   deploy/enable-cos-download.sh --apply   [--force] [--vhost PATH]
#   deploy/enable-cos-download.sh --rollback [--vhost PATH]
#
#   --apply     先 HEAD + 真实 GET 预检 COS 对象（200 + octet-stream + GET 可下载），
#               备份 vhost 为 *.bak-cos-<时间戳>，幂等写入托管标记块，
#               nginx -t 通过后 reload，最后 curl 本站确认 302。
#               nginx -t 失败自动回滚备份并退出非 0。
#   --rollback  恢复最近一次 *.bak-cos-* 备份，nginx -t 通过后 reload。
#   --status    显示标记块是否生效、COS 对象 HTTP 状态、本站 /download/mian02.apk 状态码。
#   --dry-run   只打印将要写入的最终文件 diff（可配合 --vhost 对副本试跑）。
#   --force     跳过 COS 对象预检（COS 上无对象时用户会 404，慎用）。
#   --vhost P   指定 vhost 路径（默认线上 /www/server/panel/vhost/nginx/python_backend.conf）。
#               指向非线上路径时，--apply / --rollback 只改文件，不执行 nginx -t / reload /
#               线上校验，方便在 /tmp 副本上试跑。
#
# 退出码: 0 成功 / 1 失败 / 2 用法错误
# =============================================================================
set -uo pipefail

# ----------------------------- 可修改配置 -----------------------------
COS_BUCKET="anzhuangbao-1441295645"
COS_REGION="ap-guangzhou"
COS_DOMAIN="https://anzhuangbao-1441295645.cos.ap-guangzhou.myqcloud.com"
# 为什么对象 key 不带 .apk 后缀:
#   腾讯云 COS 默认访问域名禁止匿名分发「.apk 后缀」或「APK Content-Type」的对象
#   （匿名 HEAD 返回 200，真实 GET 返回 403 DownloadForbidden）。
#   所以对象 key 用无扩展名的 apk/mian02-latest；下载文件名由 COS 对象的
#   Content-Disposition 提供，且只能是 filename* 形式（实测不能再带 filename="..."，
#   否则同样 403）:
#     Content-Type: application/octet-stream
#     Content-Disposition: attachment; filename*=UTF-8''mian02.apk
#   浏览器/下载器仍会存成 mian02.apk，用户侧无感。
#   详见 deploy/COS对象存储接入说明.md「为什么对象名不带 .apk 后缀」。
COS_KEY="apk/mian02-latest"
COS_URL="$COS_DOMAIN/$COS_KEY"

LOCAL_APK="/www/wwwroot/SmartCampus/apk/download/mian02.apk"
DEFAULT_VHOST="/www/server/panel/vhost/nginx/python_backend.conf"
NGINX_BIN="/www/server/nginx/sbin/nginx"

VHOST="$DEFAULT_VHOST"
SITE_HOSTS="https://www.mianxiaocheng.cn https://mianxiaocheng.cn"
PRIMARY_HOST="https://www.mianxiaocheng.cn"
SITE_PATH="/download/mian02.apk"

MARK_BEGIN="# >>> smartcampus-cos-download (managed by deploy/enable-cos-download.sh) >>>"
MARK_END="# <<< smartcampus-cos-download <<<"
ANCHOR_RE='^[[:space:]]*location[[:space:]]+/download/[[:space:]]*[{]'
LOC_RE='location[[:space:]]*=[[:space:]]*/download/mian02[.]apk'

ACTION=""
OPT_FORCE=0

TMP=""
cleanup() {
  if [ -n "$TMP" ] && [ -d "$TMP" ]; then
    rm -rf -- "$TMP"
  fi
}
trap cleanup EXIT INT TERM

say()  { printf '%s\n' "$*"; }
warn() { printf 'WARN: %s\n' "$*" >&2; }
die()  { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

usage() {
  say "用法: bash deploy/enable-cos-download.sh --apply|--rollback|--status|--dry-run [--force] [--vhost PATH]"
  say ""
  say "  --apply     预检 COS -> 备份 -> 写入 302 标记块 -> nginx -t -> reload -> 校验 302"
  say "  --rollback  恢复最近一次 *.bak-cos-* 备份 -> nginx -t -> reload"
  say "  --status    只读：标记块 / COS 对象 / 本站响应码"
  say "  --dry-run   只读：打印将要写入的最终文件 diff"
  say "  --force     跳过 COS 对象预检（仅 emergency 使用）"
  say "  --vhost P   指定 vhost 路径（默认 $DEFAULT_VHOST；指向副本时跳过 nginx 操作）"
  say ""
  say "当前目标: $COS_URL"
}

# ----------------------------- 参数解析 -----------------------------
while [ "$#" -gt 0 ]; do
  case "$1" in
    --apply|--rollback|--status|--dry-run)
      ACTION="$1"
      ;;
    --force)
      OPT_FORCE=1
      ;;
    --vhost)
      shift
      if [ "$#" -lt 1 ]; then
        die "--vhost 需要一个路径参数"
      fi
      VHOST="$1"
      ;;
    --vhost=*)
      VHOST=$(printf '%s' "$1" | sed 's/^--vhost=//')
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      usage >&2
      die "未知参数: $1"
      ;;
  esac
  shift
done

if [ -z "$ACTION" ]; then
  usage >&2
  exit 2
fi

if [ -z "$VHOST" ]; then
  die "--vhost 不能为空"
fi

TMP=$(mktemp -d /tmp/enable-cos-download.XXXXXX) || die "无法创建临时目录"

# ----------------------------- sudo 探测 -----------------------------
SUDO=""
if [ "$(id -u)" = "0" ]; then
  SUDO=""
elif sudo -n true 2>/dev/null; then
  SUDO="sudo -n"
fi

su_run() {
  if [ -n "$SUDO" ]; then
    $SUDO "$@"
  else
    "$@"
  fi
}

vhost_is_real() {
  [ "$VHOST" = "$DEFAULT_VHOST" ]
}

require_vhost() {
  if ! su_run test -f "$VHOST" 2>/dev/null; then
    die "vhost 不存在: $VHOST"
  fi
  if ! su_run test -r "$VHOST" 2>/dev/null; then
    die "无权限读取 $VHOST（请用 root 运行，或确认当前用户有免密 sudo）"
  fi
}

vhost_read() {
  if [ -r "$VHOST" ]; then
    cat -- "$VHOST"
  else
    $SUDO cat -- "$VHOST"
  fi
}

# vhost_stat <format>  例: %a %U %G %s %y
vhost_stat() {
  local out
  out=$(stat -c "$1" -- "$VHOST" 2>/dev/null) || out=""
  if [ -z "$out" ]; then
    out=$($SUDO stat -c "$1" -- "$VHOST" 2>/dev/null) || out=""
  fi
  printf '%s' "$out"
}

# ----------------------------- 配置生成 -----------------------------
render_block() {
  printf '%s\n' "$MARK_BEGIN"
  printf '    location = /download/mian02.apk {\n'
  printf '        add_header Cache-Control "no-store" always;\n'
  printf '        return 302 %s;\n' "$COS_URL"
  printf '    }\n'
  printf '%s\n' "$MARK_END"
}

# 删除已有的托管标记块（幂等）
strip_managed_block() {
  awk '
    /^[[:space:]]*# >>> smartcampus-cos-download/ { skip = 1; next }
    skip == 1 {
      if ($0 ~ /^[[:space:]]*# <<< smartcampus-cos-download/) { skip = 0 }
      next
    }
    { print }
  ' "$1"
}

# 在第一条 "location /download/ {" 之前插入标记块
insert_block_before_anchor() {
  awk -v blkfile="$2" '
    BEGIN {
      blk = ""
      while ((getline line < blkfile) > 0) { blk = blk line "\n" }
      close(blkfile)
    }
    inserted == 0 && $0 ~ /^[[:space:]]*location[[:space:]]+\/download\/[[:space:]]*[{]/ {
      printf "%s", blk
      inserted = 1
    }
    { print }
    END { if (inserted == 0) { exit 3 } }
  ' "$1"
}

build_desired() {
  local src out stripped
  src="$1"
  out="$2"
  stripped="$TMP/stripped.conf"
  if ! strip_managed_block "$src" > "$stripped"; then
    return 1
  fi
  if grep -qE "$LOC_RE" "$stripped"; then
    printf 'ERROR: %s 中已存在「未托管」的 location = /download/mian02.apk，请先人工确认后再执行。\n' "$VHOST" >&2
    return 4
  fi
  if ! grep -qE "$ANCHOR_RE" "$stripped"; then
    printf 'ERROR: %s 中未找到锚点「location /download/ {」，无法安全插入标记块。\n' "$VHOST" >&2
    return 5
  fi
  render_block > "$TMP/block.txt" || return 6
  if ! insert_block_before_anchor "$stripped" "$TMP/block.txt" > "$out"; then
    return 3
  fi
  # 保持源文件「末尾是否带换行」的原有形态，避免产生无意义 diff
  if [ -z "$(tail -c 1 -- "$src")" ]; then
    :
  else
    printf '%s' "$(cat -- "$out")" > "$TMP/trim.conf" || return 7
    mv -f -- "$TMP/trim.conf" "$out" || return 7
  fi
  return 0
}

write_vhost_file() {
  local src mode owner group
  src="$1"
  mode=$(vhost_stat '%a')
  owner=$(vhost_stat '%U')
  group=$(vhost_stat '%G')
  [ -n "$mode" ] || mode=600
  [ -n "$owner" ] || owner=root
  [ -n "$group" ] || group=root
  if [ -w "$VHOST" ]; then
    cat -- "$src" > "$VHOST" || return 1
  else
    $SUDO install -m "$mode" -o "$owner" -g "$group" -- "$src" "$VHOST" || return 1
  fi
  return 0
}

# ----------------------------- nginx -----------------------------
nginx_test() {
  local out rc
  out=$($SUDO "$NGINX_BIN" -t 2>&1)
  rc=$?
  printf '%s\n' "$out"
  return $rc
}

nginx_reload() {
  $SUDO "$NGINX_BIN" -s reload 2>&1
}

# ----------------------------- HTTP 工具 -----------------------------
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

cos_http_code() {
  local code
  code=$(curl -sS -o /dev/null -w '%{http_code}' -I --max-time 25 "$COS_URL" 2>/dev/null) || code="000"
  printf '%s' "$code"
}

site_head() {
  local url hdrfile code
  url="$1"
  hdrfile="$2"
  code=$(curl -sS -o /dev/null -D "$hdrfile" -I --max-time 20 -w '%{http_code}' "$url" 2>/dev/null) || code="000"
  printf '%s' "$code"
}

# ----------------------------- COS 预检 -----------------------------
# 重点: COS 默认域名对「.apk 后缀 / APK Content-Type」的对象会放行 HEAD 但拦截真实 GET
#       （403 DownloadForbidden）。所以预检必须同时做 HEAD 和一次真实 GET，不能只看 HEAD。
cos_preflight() {
  local hdrs ct len local_size dlsize got code
  say "-- [预检] HEAD $COS_URL"
  if ! hdrs=$(curl -fsSI --max-time 25 "$COS_URL" 2>"$TMP/cos.err"); then
    code=$(cos_http_code)
    say "   FAIL: 无法匿名访问 COS 对象（HTTP $code）"
    if [ -s "$TMP/cos.err" ]; then
      sed -n '1,3p' "$TMP/cos.err" | sed 's/^/         /'
    fi
    say "   可能原因: 对象尚未上传 / 对象 ACL 不是 public-read / 桶策略禁止匿名读"
    return 1
  fi
  ct=$(header_value "$hdrs" "Content-Type")
  [ -n "$ct" ] || ct="(空)"
  case "$ct" in
    *application/octet-stream*)
      say "   PASS: Content-Type = $ct（无扩展名对象，推荐配置）"
      ;;
    *android.package-archive*)
      say "   WARN: Content-Type = $ct（APK 类型可能被 COS 默认域名拦截匿名下载）"
      ;;
    *)
      say "   FAIL: Content-Type = $ct，期望 application/octet-stream"
      return 1
      ;;
  esac
  len=$(header_value "$hdrs" "Content-Length")
  say "   INFO: Content-Length = $len"
  if [ -f "$LOCAL_APK" ]; then
    local_size=$(stat -c '%s' -- "$LOCAL_APK")
    if [ "$len" = "$local_size" ]; then
      say "   PASS: 与本地 APK 大小一致 ($local_size 字节)"
    else
      warn "COS 对象大小 $len 与本地 APK $local_size 不一致（不阻塞切换，但请确认是同一版本）"
    fi
  else
    warn "本地 APK 不存在: $LOCAL_APK（跳过大小比对）"
  fi
  say "-- [预检] 真实 GET（Range: bytes=0-0，验证不是 403 DownloadForbidden）"
  got=$(curl -sS -o /dev/null -r 0-0 --max-time 30 -w '%{http_code} %{size_download}' "$COS_URL" 2>/dev/null) || got="000 0"
  code=$(printf '%s' "$got" | awk '{print $1}')
  dlsize=$(printf '%s' "$got" | awk '{print $2}')
  case "$code" in
    200|206)
      say "   PASS: 真实 GET 可下载（HTTP $code，下载 $dlsize 字节）"
      ;;
    *)
      say "   FAIL: 真实 GET 被拒（HTTP $code）"
      say "         若 HEAD 是 200 而 GET 是 403，通常是 COS 默认域名拦截了 .apk 后缀 / APK Content-Type，"
      say "         请使用无扩展名 key（apk/mian02-latest）+ application/octet-stream + Content-Disposition。"
      return 1
      ;;
  esac
  return 0
}

# ----------------------------- 动作 -----------------------------
do_dry_run() {
  require_vhost
  vhost_read > "$TMP/before.conf" || die "读取 vhost 失败"
  build_desired "$TMP/before.conf" "$TMP/after.conf" || die "生成目标配置失败"
  say "== dry-run（不会修改任何文件、不执行 nginx -t / reload）=="
  say "vhost: $VHOST"
  if cmp -s "$TMP/before.conf" "$TMP/after.conf"; then
    say "结果: 已是目标状态，--apply 不会产生任何改动。"
    exit 0
  fi
  say ""
  say "--- 将要写入的最终文件 diff（a = 当前，b = 应用后）---"
  diff -u --label "a:$VHOST" --label "b:$VHOST" "$TMP/before.conf" "$TMP/after.conf"
  say "--- diff 结束 ---"
  say ""
  say "提示: 以上内容只有执行 --apply 才会写入；线上文件 mtime 保持不变。"
  exit 0
}

do_apply() {
  require_vhost
  say "== apply =="
  say "vhost : $VHOST"
  say "COS   : $COS_URL"
  if [ "$(id -u)" != "0" ] && [ -z "$SUDO" ]; then
    die "需要 root 或免密 sudo 才能写入 vhost"
  fi

  if [ "$OPT_FORCE" = "1" ]; then
    warn "--force 已指定：跳过 COS 对象预检（COS 上无对象时用户会看到 404）"
    say "-- [预检] 当前 COS 对象 HTTP 状态: $(cos_http_code)"
  else
    if ! cos_preflight; then
      say ""
      die "COS 预检未通过，已中止，未做任何改动。确认对象已上传、public-read、且真实 GET 可下载（200）后重试，或加 --force 跳过。"
    fi
  fi

  vhost_read > "$TMP/before.conf" || die "读取 vhost 失败"
  build_desired "$TMP/before.conf" "$TMP/after.conf" || die "生成目标配置失败，未做任何改动"
  if cmp -s "$TMP/before.conf" "$TMP/after.conf"; then
    say "-- 当前配置已是目标状态，无需变更（未 reload）"
    exit 0
  fi

  BAK="$VHOST.bak-cos-$(date +%Y%m%d-%H%M%S-%N)"
  say "-- 备份: $BAK"
  su_run cp -a -- "$VHOST" "$BAK" || die "备份失败，已中止，未做任何改动"

  say "-- 写入托管标记块"
  if ! write_vhost_file "$TMP/after.conf"; then
    say "-- 写入失败，尝试恢复备份"
    su_run cp -a -- "$BAK" "$VHOST" || warn "恢复备份失败，请手工恢复: cp -a $BAK $VHOST"
    die "写入 vhost 失败"
  fi

  if vhost_is_real; then
    say "-- nginx -t"
    if ! nginx_test; then
      say "FAIL: nginx -t 未通过，自动回滚备份"
      su_run cp -a -- "$BAK" "$VHOST" || die "回滚失败！请手工执行: cp -a $BAK $VHOST"
      if nginx_test; then
        say "回滚后 nginx -t 通过（线上配置已复原，未 reload）"
      else
        say "回滚后 nginx -t 仍失败，请立即人工处理"
      fi
      exit 1
    fi
    say "-- nginx -s reload"
    if ! nginx_reload; then
      say "FAIL: reload 失败，配置已写入，备份: $BAK"
      exit 1
    fi
    say "-- 线上校验（期望 302 -> COS）"
    if ! verify_redirect; then
      say ""
      say "FAIL: 站点未返回期望的 302。配置已写入并 reload，但校验未通过。"
      say "      可执行 deploy/enable-cos-download.sh --rollback 立即回退。"
      exit 1
    fi
  else
    say "-- --vhost 指向非线上配置：跳过 nginx -t / reload / 线上校验"
  fi

  say ""
  say "== apply 完成 =="
  say "备份文件: $BAK"
  say "回滚命令: deploy/enable-cos-download.sh --rollback"
  exit 0
}

verify_redirect() {
  local host url code loc i ok
  ok=0
  for host in $SITE_HOSTS; do
    url="$host$SITE_PATH"
    code="000"
    i=0
    while [ "$i" -lt 10 ]; do
      code=$(site_head "$url" "$TMP/site.hdr")
      if [ "$code" = "302" ]; then
        break
      fi
      i=$((i + 1))
      sleep 1
    done
    loc=$(header_value "$(cat -- "$TMP/site.hdr" 2>/dev/null)" "Location")
    if [ "$code" = "302" ]; then
      case "$loc" in
        "$COS_DOMAIN"/*)
          say "   PASS: $url -> 302 $loc"
          ok=1
          ;;
        *)
          say "   WARN: $url -> 302 但 Location 不是 COS: $loc"
          ;;
      esac
    else
      say "   FAIL: $url -> HTTP $code（期望 302）"
    fi
  done
  [ "$ok" = "1" ]
}

latest_backup() {
  local p
  p=$(ls -1t -- "$VHOST".bak-cos-* 2>/dev/null | head -n 1) || p=""
  if [ -z "$p" ] && [ -n "$SUDO" ]; then
    p=$($SUDO bash -c "ls -1t -- '$VHOST'.bak-cos-* 2>/dev/null | head -n 1") || p=""
  fi
  printf '%s' "$p"
}

do_rollback() {
  require_vhost
  local bak code
  bak=$(latest_backup)
  if [ -z "$bak" ]; then
    die "未找到备份文件: $VHOST.bak-cos-*（可能从未 --apply 过）"
  fi
  say "== rollback =="
  say "vhost: $VHOST"
  say "备份 : $bak"
  if [ "$(id -u)" != "0" ] && [ -z "$SUDO" ]; then
    die "需要 root 或免密 sudo 才能写入 vhost"
  fi
  su_run cp -a -- "$bak" "$VHOST" || die "恢复备份失败"
  say "-- 已恢复备份内容"
  if vhost_is_real; then
    say "-- nginx -t"
    nginx_test || die "nginx -t 未通过，请人工检查（备份仍在 $bak）"
    say "-- nginx -s reload"
    nginx_reload || die "reload 失败"
    say "-- 线上校验（期望回到本机 200）"
    code=$(site_head "$PRIMARY_HOST$SITE_PATH" "$TMP/site.hdr")
    say "   $PRIMARY_HOST$SITE_PATH -> HTTP $code"
    if [ "$code" = "200" ]; then
      say "   PASS: 已回到本机静态文件"
    else
      warn "期望 200，实际 $code（请检查是否还残留标记块）"
    fi
  else
    say "-- --vhost 指向非线上配置：跳过 nginx -t / reload / 线上校验"
  fi
  say ""
  say "== rollback 完成 =="
  exit 0
}

do_status() {
  require_vhost
  local content code site_code loc desired_rc
  content=$(vhost_read)
  say "== status =="
  say "vhost: $VHOST"
  say "  文件: $(vhost_stat '%s') 字节, mtime $(vhost_stat '%y')"
  say "  属主: $(vhost_stat '%U'):$(vhost_stat '%G'), 权限 $(vhost_stat '%a')"

  if printf '%s\n' "$content" | grep -qE '^# >>> smartcampus-cos-download'; then
    say "  标记块: 已写入"
  else
    say "  标记块: 未写入（当前仍是本机静态文件）"
  fi

  printf '%s\n' "$content" > "$TMP/cur.conf"
  if build_desired "$TMP/cur.conf" "$TMP/desired.conf" 2>/dev/null; then
    if cmp -s "$TMP/cur.conf" "$TMP/desired.conf"; then
      say "  与脚本期望: 一致（--apply 不会产生改动）"
    else
      say "  与脚本期望: 不一致（--apply 会更新标记块）"
    fi
  else
    say "  与脚本期望: 无法计算（锚点缺失，或存在未托管的同名 location）"
  fi

  say ""
  say "COS 对象: $COS_URL"
  code=$(cos_http_code)
  case "$code" in
    200) say "  HTTP 200（匿名可读）" ;;
    *)   say "  HTTP $code（匿名不可读：未上传 / 未设 public-read / 桶策略限制）" ;;
  esac

  say ""
  say "线上响应: $PRIMARY_HOST$SITE_PATH"
  site_code=$(site_head "$PRIMARY_HOST$SITE_PATH" "$TMP/site.hdr")
  loc=$(header_value "$(cat -- "$TMP/site.hdr" 2>/dev/null)" "Location")
  say "  HTTP $site_code"
  if [ -n "$loc" ]; then
    say "  Location: $loc"
  fi
  case "$site_code" in
    302) say "  判断: 已切换到 COS 302" ;;
    200) say "  判断: 仍由本机静态文件提供" ;;
    *)   say "  判断: 异常状态码，请检查 nginx 与文件" ;;
  esac
  exit 0
}

# ----------------------------- 入口 -----------------------------
case "$ACTION" in
  --dry-run)  do_dry_run ;;
  --apply)    do_apply ;;
  --rollback) do_rollback ;;
  --status)   do_status ;;
  *)
    usage >&2
    exit 2
    ;;
esac
