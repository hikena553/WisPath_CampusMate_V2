#!/bin/sh
# 启用 HTTPS（Let's Encrypt + nginx）
#
# 用法：
#   ./deploy/enable_https.sh <域名> <邮箱>
#   ./deploy/enable_https.sh --renew
#
# 前置条件（缺一不可）：
#   1. 已有域名，A 记录已解析到本机公网 IP，且解析已生效：
#        ping <域名>   # 应返回本机 IP
#   2. 安全组/防火墙放通 80 与 443
#   3. `docker compose up -d` 已跑过，frontend 容器在运行
#
# 为什么必须用域名：Let's Encrypt 不对公网 IP 签发证书。
# 只有 IP 时无法走本脚本，只能自签（浏览器会告警，且麦克风类功能
# 在未信任的证书下会被浏览器拒绝，等于语音通话不可用）。
#
# 流程：webroot 模式申请（不停前端）→ 证书同步为固定文件名 → 切换
#       NGINX_CONF 指向 ssl 配置 → 重建 frontend。
set -e

PROJECT_DIR=$(cd "$(dirname "$0")/.." && pwd)
CERTS_DIR="$PROJECT_DIR/deploy/certs"
LE_DIR="$CERTS_DIR/letsencrypt"
# compose 文件里 name: smart-campus，故卷名带该前缀
WEBROOT_VOLUME="smart-campus_certbot_webroot"

cd "$PROJECT_DIR"

# ---------- 续期模式 ----------
if [ "$1" = "--renew" ]; then
    echo "[renew] 检查并续期证书 ..."
    docker run --rm \
        -v "$LE_DIR:/etc/letsencrypt" \
        -v "$WEBROOT_VOLUME:/var/www/certbot" \
        certbot/certbot renew --webroot -w /var/www/certbot --quiet
    # 证书有更新时同步固定文件名并让 nginx 重新加载
    DOMAIN_FILE="$CERTS_DIR/.domain"
    if [ -f "$DOMAIN_FILE" ]; then
        DOMAIN=$(cat "$DOMAIN_FILE")
        cp -L "$LE_DIR/live/$DOMAIN/fullchain.pem" "$CERTS_DIR/fullchain.pem"
        cp -L "$LE_DIR/live/$DOMAIN/privkey.pem" "$CERTS_DIR/privkey.pem"
        docker compose exec -T frontend nginx -s reload || true
        echo "[renew] 完成，nginx 已重新加载"
    else
        echo "[renew] 未找到 $DOMAIN_FILE，跳过同步（首次请先执行申请）"
    fi
    exit 0
fi

# ---------- 申请模式 ----------
DOMAIN="${1:-}"
EMAIL="${2:-}"

if [ -z "$DOMAIN" ] || [ -z "$EMAIL" ]; then
    echo "用法: $0 <域名> <邮箱>"
    echo "  例: $0 campus.example.edu.cn admin@example.edu.cn"
    echo "续期: $0 --renew"
    exit 1
fi

# 拒绝 IP，给出明确原因，避免用户卡在 certbot 的模糊报错上
case "$DOMAIN" in
    *[!0-9.]*)
        ;;
    *)
        echo "[错误] '$DOMAIN' 看起来是 IP 地址，Let's Encrypt 不对 IP 签发证书。"
        echo "       请先配置域名并解析到本机，再用域名执行。"
        exit 1
        ;;
esac

echo "[1/5] 检查 frontend 是否在运行 ..."
if ! docker compose ps --status running --format '{{.Service}}' | grep -q '^frontend$'; then
    echo "[错误] frontend 未运行。请先执行: docker compose up -d"
    exit 1
fi

echo "[2/5] 检查域名解析 ..."
RESOLVED=$(getent hosts "$DOMAIN" | awk '{print $1}' | head -1 || true)
PUBLIC_IP=$(curl -fsS --max-time 8 https://api.ipify.org 2>/dev/null || true)
echo "      域名解析到: ${RESOLVED:-<未解析>}"
echo "      本机公网IP: ${PUBLIC_IP:-<获取失败>}"
if [ -n "$RESOLVED" ] && [ -n "$PUBLIC_IP" ] && [ "$RESOLVED" != "$PUBLIC_IP" ]; then
    echo "[警告] 解析结果与本机公网 IP 不一致。若使用 CDN/负载均衡可忽略，"
    echo "       否则证书申请会因校验文件取不到而失败（DNS 生效通常需几分钟到几十分钟）。"
fi

echo "[3/5] 申请证书（webroot 模式，前端不停机）..."
mkdir -p "$LE_DIR"
docker run --rm \
    -v "$LE_DIR:/etc/letsencrypt" \
    -v "$WEBROOT_VOLUME:/var/www/certbot" \
    certbot/certbot certonly --webroot -w /var/www/certbot \
    -d "$DOMAIN" --email "$EMAIL" --agree-tos --non-interactive

echo "[4/5] 同步证书为固定文件名 ..."
cp -L "$LE_DIR/live/$DOMAIN/fullchain.pem" "$CERTS_DIR/fullchain.pem"
cp -L "$LE_DIR/live/$DOMAIN/privkey.pem" "$CERTS_DIR/privkey.pem"
echo "$DOMAIN" > "$CERTS_DIR/.domain"
chmod 600 "$CERTS_DIR/privkey.pem"

echo "[5/5] 切换 nginx 配置为 HTTPS ..."
if grep -q '^NGINX_CONF=' .env 2>/dev/null; then
    sed -i 's|^NGINX_CONF=.*|NGINX_CONF=./deploy/nginx.ssl.conf|' .env
else
    echo 'NGINX_CONF=./deploy/nginx.ssl.conf' >> .env
fi
docker compose up -d --force-recreate frontend

echo
echo "============================================"
echo " HTTPS 已启用：https://$DOMAIN/"
echo "============================================"
echo "验证："
echo "  curl -sI https://$DOMAIN | head -1        # 应返回 HTTP/2 200"
echo "  docker compose logs --tail=20 frontend    # 无证书相关报错"
echo
echo "续期（证书 90 天有效，建议加 cron 每日检查）："
echo "  30 4 * * * cd $PROJECT_DIR && ./deploy/enable_https.sh --renew >> /var/log/certbot-renew.log 2>&1"
