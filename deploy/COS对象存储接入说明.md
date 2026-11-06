# 安装包对象存储（COS）接入说明

> 适用：SmartCampus 站点（https://www.mianxiaocheng.cn / https://mianxiaocheng.cn）
> 读者：运维 / 发布负责人
> 目标：APK 上传到腾讯云 COS，站点 `/download/mian02.apk` 由 nginx **302 跳转**到 COS；
> 用户仍然只看到自家域名（二维码、下载页、分享链接一律不变），服务器不再承载 39MB 的安装包流量。

---

## 0. 一页速览

| 项目 | 值 |
| --- | --- |
| 存储桶 Bucket | `anzhuangbao-1441295645` |
| 地域 Region | `ap-guangzhou` |
| 访问域名 | `https://anzhuangbao-1441295645.cos.ap-guangzhou.myqcloud.com` |
| 主 APK 对象 | `apk/mian02-latest`（**无扩展名**，见第 5 节） |
| 版本化对象 | `apk/releases/mian02-<versionName>-<versionCode>.apk` |
| 版本清单 | `apk/latest.json` |
| 线上下载地址 | `https://www.mianxiaocheng.cn/download/mian02.apk` |
| 兼容地址 | `https://www.mianxiaocheng.cn/download/SmartCampus.apk`（nginx rewrite 到同一条 302 规则；下载页/二维码当前使用的就是它） |
| 桶读权限 | **保持私有读**，由上传脚本对每个对象设置 `public-read` |
| 服务器密钥文件 | `/www/wwwroot/SmartCampus/.cos.env`（600，www:www，**不入库**） |

下载链路（切换后）：

```
用户 / 二维码 / 下载页
    |
    |  https://www.mianxiaocheng.cn/download/mian02.apk
    v
nginx  location = /download/mian02.apk   --> HTTP 302
    |
    |  Location: https://anzhuangbao-1441295645.cos.ap-guangzhou.myqcloud.com/apk/mian02-latest
    v
腾讯云 COS（对象 ACL = public-read）--> 200 + application/octet-stream
           + Content-Disposition: attachment; filename*=UTF-8''SmartCampus.apk
```

发布链路：

```
npm run apk:release  ->  build-apk.mjs  ->  自动执行 publish-apk.mjs（上传 COS）
                                         ->  失败只告警，不影响出包
兜底：/etc/cron.d/smartcampus-cos 每 5 分钟跑 deploy/cos-sync-apk.sh --sync
```

相关文件：

| 文件 | 作用 |
| --- | --- |
| `deploy/cos-cam-policy.json` | 子账号 CAM 策略（最小权限） |
| `deploy/cos.env.example` | 密钥文件模板（入库、无真实密钥） |
| `frontend/scripts/publish-apk.mjs` | 上传 APK / 版本化对象 / latest.json / 设置 CORS |
| `deploy/cos-sync-apk.sh` | 定时兜底同步（cron 每 5 分钟） |
| `deploy/enable-cos-download.sh` | 切换 / 回滚 nginx 302（幂等、带备份自愈） |
| `deploy/verify-cos-download.sh` | 只读验收（逐项 PASS/FAIL） |

---

## 1. 创建子用户、API 密钥并关联策略

> 需要主账号（或有 CAM 管理权限的账号）操作。子账号只用于服务器上传，**不要给它控制台登录以外的多余权限**。

### 1.1 新建子用户

1. 打开访问管理控制台：https://console.cloud.tencent.com/cam
2. 左侧「用户」→「用户列表」→「新建用户」→ 选择「自定义创建」。
3. 访问方式：**只勾选「编程访问」**（会生成 API 密钥），不要勾选控制台登录（除非确实需要人工排查）。
4. 下一步，权限先留空（稍后单独关联自定义策略），完成创建。
5. 创建结果页会显示 **SecretId / SecretKey，只显示这一次**，立刻复制保存到密码管理器。

### 1.2 创建自定义策略

1. 打开「策略」：https://console.cloud.tencent.com/cam/policy
2. 「新建自定义策略」→ 选择「按策略语法创建」→「空白模板」。
3. 把仓库里的 `deploy/cos-cam-policy.json` 全文粘贴进去：

```json
{
  "version": "2.0",
  "statement": [
    {
      "effect": "allow",
      "action": [
        "cos:PutObject",
        "cos:GetObject",
        "cos:HeadObject",
        "cos:PutObjectACL",
        "cos:GetBucketCORS",
        "cos:PutBucketCORS"
      ],
      "resource": [
        "qcs::cos:ap-guangzhou:uid/1441295645:anzhuangbao-1441295645/*"
      ]
    }
  ]
}
```

4. 策略名称填 `SmartCampusCosApk`（备注：SmartCampus APK 上传/读取/CORS），保存。

字段解释：

- `uid/1441295645`：主账号 APPID（就是桶名后缀那串数字）。
- `anzhuangbao-1441295645/*`：**该桶下所有对象**。若想更严格，可改成
  `anzhuangbao-1441295645/apk/*`（只允许 apk/ 前缀）。
- `cos:PutObjectACL`：上传脚本要按对象设置 `public-read`。
- `cos:GetBucketCORS` / `cos:PutBucketCORS`：`publish-apk.mjs --setup-cors` 需要。
- 若只想让脚本能读自己的对象，`GetObject/HeadObject` 也可去掉；保留便于 `--sync` 比对远端 latest.json。

> ⚠️ 若 CORS 设置时报 `AccessDenied`（部分账号下桶级操作需要桶根资源），
> 把 resource 再加一条桶根即可：
> `"qcs::cos:ap-guangzhou:uid/1441295645:anzhuangbao-1441295645/"`
> （CORS 只是 best-effort，不影响 APK 上传与 302 下载。）

### 1.3 关联策略到子用户

1. 「用户」→「用户列表」→ 点子用户名 →「权限」→「关联策略」。
2. 搜索 `SmartCampusCosApk` → 勾选 → 确定。
3. 关联后建议在「权限」页确认**没有**额外的高危预设策略（如 `QcloudCOSFullAccess`）。

### 1.4 换桶 / 换账号时要改哪些地方

三处必须同步改（否则 403 或 404）：

1. `deploy/cos-cam-policy.json` 的 `uid/<APPID>` 与桶名；
2. 服务器 `/www/wwwroot/SmartCampus/.cos.env` 的 `COS_BUCKET` / `COS_REGION` / `COS_DOMAIN`；
3. 两个 shell 脚本顶部的 `COS_DOMAIN` / `COS_URL` 常量
   （`deploy/enable-cos-download.sh`、`deploy/verify-cos-download.sh`）。

---

## 2. 把密钥填进服务器（`.cos.env`）

密钥只存在服务器本地文件，**不要写进 git、不要写进前端**。

```bash
# 1) 用模板生成（若文件已存在则跳过，别覆盖已有密钥）
cd /www/wwwroot/SmartCampus
sudo -n install -o www -g www -m 600 deploy/cos.env.example .cos.env

# 2) 以 www 身份编辑，填 COS_SECRET_ID / COS_SECRET_KEY
sudo -n -u www vim .cos.env

# 3) 确认权限（必须是 -rw------- www www）
sudo -n ls -l .cos.env
```

文件内容形如：

```ini
COS_BUCKET=anzhuangbao-1441295645
COS_REGION=ap-guangzhou
COS_DOMAIN=https://anzhuangbao-1441295645.cos.ap-guangzhou.myqcloud.com
COS_SECRET_ID=AKIDxxxxxxxxxxxxxxxxxxxxxxxx
COS_SECRET_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

注意：

- 等号两边不要加空格、不要加引号（尤其是中文引号），粘贴后检查有无换行截断。
- `.cos.env`、`.cos-last-upload.json`、`.cos-sync.lock` 已在 `.gitignore` 中。
- 权限 600 + 属主 www，保证只有 www 和 root 能读。
- 轮换密钥：控制台「用户详情 → API 密钥」新建密钥 → 更新 .cos.env → 观察一次上传成功 → 再禁用旧密钥。

---

## 3. 首次上传与日常发布

### 3.1 先干跑（不联网、不花钱）

```bash
cd /www/wwwroot/SmartCampus/frontend
sudo -n -u www npm run apk:publish -- --dry-run
```

会打印本地 APK 的 sha256、大小、目标 key 与最终 URL，用于核对版本。

### 3.2 真正上传

```bash
cd /www/wwwroot/SmartCampus/frontend
sudo -n -u www npm run apk:publish
```

会上传 3 个对象（均为 `public-read`）：

| 对象 | 用途 | Cache-Control |
| --- | --- | --- |
| `apk/mian02-latest` | 302 跳转的目标，始终是最新版（key 无扩展名，见第 5 节） | no-cache |
| `apk/releases/mian02-<版本>-<版本号>.apk` | 历史版本留档 | public, max-age=31536000, immutable |
| `apk/latest.json` | 版本/sha256/大小/下载地址，给前端与验收用 | no-cache |

> 主对象 key **不带 `.apk` 后缀**；Content-Type 用 `application/octet-stream`，
> Content-Disposition 只能用 `filename*`（不能再带 `filename="..."`）。原因与实测见第 5 节。

成功后本地会写 `.cos-last-upload.json`（记录 sha256/版本/URL）。

### 3.3 日常

- 每次 `npm run apk:release` 出包后**自动**上传；上传失败或缺密钥只告警，不会让打包失败。
- 兜底任务 `/etc/cron.d/smartcampus-cos` 每 5 分钟执行 `deploy/cos-sync-apk.sh --sync`：
  远端 `apk/latest.json` 的 sha256 与本地一致就跳过；无密钥时静默退出 0；通过 flock 防并发。
- 日志：`/www/wwwroot/SmartCampus/logs/cos-sync.log`（若目录不存在脚本会创建）。

### 3.4 上传后自查

```bash
curl -fsSI https://anzhuangbao-1441295645.cos.ap-guangzhou.myqcloud.com/apk/mian02-latest
curl -fsS  https://anzhuangbao-1441295645.cos.ap-guangzhou.myqcloud.com/apk/latest.json
```

期望：第一条 HEAD 200 + `Content-Type: application/octet-stream` +
`Content-Disposition: attachment; filename*=UTF-8''SmartCampus.apk`，并且**真实 GET 也必须是 200**
（只测 HEAD 会漏掉 403 DownloadForbidden）；
第二条 200 + 合法 JSON，且其中 `sha256` 与本地 `sha256sum apk/download/mian02.apk` 一致。

---

## 4. 切换线上下载到 COS（302）

> 只在第 3 步确认「对象可匿名访问且大小一致」后再切换。
> 切换不删除本机文件，**随时可以一条命令回滚**。

### 4.1 切换前检查

```bash
cd /www/wwwroot/SmartCampus
deploy/verify-cos-download.sh
```

a/c/d 全 PASS（b 此时是「本机 200」也正常）才继续。

### 4.2 看 diff（不改任何文件）

```bash
deploy/enable-cos-download.sh --dry-run
# 或对 /tmp 副本试跑：
# sudo -n cp -a /www/server/panel/vhost/nginx/python_backend.conf /tmp/vhost.conf && sudo -n chown ubuntu:ubuntu /tmp/vhost.conf
# deploy/enable-cos-download.sh --dry-run --vhost /tmp/vhost.conf
```

会打印将要插入的托管标记块及完整 unified diff。

### 4.3 执行切换

```bash
sudo -n deploy/enable-cos-download.sh --apply
```

脚本按顺序做（任何一步失败都不会把站点留在坏状态）：

1. `curl -fsSI` 预检 COS 对象：HEAD 必须 **200**、`Content-Type` 为 `application/octet-stream`，
   并额外用 `curl -r 0-0` 做一次**真实 GET**（200/206）——COS 会放行 HEAD 却拦截真实 GET。
   （否则中止，加 `--force` 可跳过——**危险**，COS 上没有对象时用户会 404）。
2. 备份 vhost 到同目录 `python_backend.conf.bak-cos-<时间戳>`。
3. 幂等写入标记块（已存在则先删后插，重复执行结果一致）。
4. `nginx -t`；失败自动恢复备份并退出非 0（此时线上 nginx 仍跑旧配置，无中断）。
5. `nginx -s reload`。
6. 用 `curl -sI` 校验 `https://www.mianxiaocheng.cn/download/mian02.apk` 返回 **302** 且 Location 指向 COS。

写入的内容就是下面这个块（插在 `location /download/ {` 之前）：

```nginx
# >>> smartcampus-cos-download (managed by deploy/enable-cos-download.sh) >>>
location = /download/mian02.apk {
    add_header Cache-Control "no-store" always;
    return 302 https://anzhuangbao-1441295645.cos.ap-guangzhou.myqcloud.com/apk/mian02-latest;
}
# <<< smartcampus-cos-download <<<
```

### 4.4 回滚

```bash
sudo -n deploy/enable-cos-download.sh --rollback
```

恢复最近一次 `.bak-cos-*` → `nginx -t` → reload，然后校验恢复到「本机 200」。
回滚**不动 COS 上的对象**，也不改任何业务代码，通常 1~2 秒完成。

### 4.5 为什么这样能生效（原理）

- nginx 的 location 匹配优先级：`=` 精确匹配 > `^~` 前缀 > 正则 > 普通前缀。
- 站点原有 `location /download/ { ... }` 是普通前缀匹配，负责本机 APK 静态文件。
- 新增的 `location = /download/mian02.apk` 是精确匹配，**优先级更高**，只拦截这一个 URL；
  `/download/`、`/download/` 页面路由、`/download/其他文件` 全部保持原样。
- `add_header Cache-Control "no-store" always` 防止客户端/CDN 把 302 缓存住（否则切回滚后仍会被带着跳）。
  注：`always` 让 3xx 响应也带这个头。

### 4.6 注意事项

- **不要手工编辑** vhost 里的标记块：下次 `--apply` 会按标记整块替换；要改跳转地址请改脚本顶部常量。
- 不要绕过脚本手工 reload；宝塔面板里其他站点的配置也别顺带改动。
- `--vhost PATH` 指向非线上路径时，脚本只改文件、**跳过** `nginx -t`/reload/线上校验，仅供演练。
- 切换后如果浏览器仍下载到旧包，先确认 302 已生效（`curl -sI` 看状态码），再清本地缓存；
  302 响应已带 no-store，通常刷新即可。

---

## 5. 为什么对象名不带 .apk 后缀（重要）

腾讯云 COS **默认访问域名**（`<bucket>.cos.<region>.myqcloud.com`）有一层限制：
对「key 以 `.apk` 结尾」或「Content-Type 为 `application/vnd.android.package-archive`」的对象，
**匿名 HEAD 返回 200，但真实 GET 返回 403 `DownloadForbidden`**。

实测（旧对象 `apk/mian02.apk`）：

```bash
# 看起来一切正常
curl -sI  https://anzhuangbao-1441295645.cos.ap-guangzhou.myqcloud.com/apk/mian02.apk
# HTTP/1.1 200 OK

# 实际下载直接 403
curl -s -o /dev/null -w '%{http_code}\n' https://anzhuangbao-1441295645.cos.ap-guangzhou.myqcloud.com/apk/mian02.apk
# 403
```

所以「传上去 + curl -I 看到 200」**不等于**用户能下载。这也是
`deploy/verify-cos-download.sh` 的 a 项必须做**真实 GET 并按字节数校验**的原因。

### 5.1 唯一可用的组合（实测）

| 项 | 必须的值 |
| --- | --- |
| 对象 key | `apk/mian02-latest`（**无扩展名**） |
| Content-Type | `application/octet-stream` |
| Content-Disposition | `attachment; filename*=UTF-8''SmartCampus.apk` |
| 对象 ACL | `public-read` |

注意：Content-Disposition **只能带 `filename*`**，不要再叠加 `filename="mian02.apk"`——
实测同时带 `filename="..."` 会重新触发 403；key 带 `.apk` 后缀、或 Content-Type 用 APK 类型同样 403。

用户侧完全无感：二维码/下载页仍是 `https://www.mianxiaocheng.cn/download/mian02.apk`，nginx 302 到
`.../apk/mian02-latest`，浏览器按 `filename*` 把文件存成 `mian02.apk`。

### 5.2 影响与后续

- 版本留档对象 `apk/releases/mian02-<版本>-<版本号>.apk` 也带 `.apk` 后缀，**不能**匿名直连，
  只作为 COS 内部归档（服务器侧可读），不对外提供下载链接。
- 将来若给 COS 绑定自定义域名（例如 `dl.mianxiaocheng.cn`，可挂 CDN），这类默认域名限制通常不再适用，
  即可恢复标准的 `.apk` 后缀分发；届时改 `.cos.env` 的 `COS_DOMAIN` 与两个脚本顶部的
  `COS_DOMAIN` / `COS_KEY` 常量后重新 `--apply` 即可。
- 换 key / 换域名后，务必先跑 `deploy/verify-cos-download.sh` 确认 a4（真实 GET）为 200，再切换线上 302。

---

## 6. 桶侧配置说明（控制台）

### 6.1 权限：**不需要**把桶改成公有读

- 桶保持默认的「私有读写」即可，匿名 GET 整桶列表依然会被拒绝，更安全。
- 上传脚本对**每个对象**单独设置 ACL = `public-read`，所以 `apk/mian02-latest` 能被匿名下载。
  但**光有 ACL 不够**：对象 key 还必须不带 `.apk` 后缀、Content-Type 为 `application/octet-stream`、
  Content-Disposition 只用 `filename*`，否则默认域名会 403（见第 5 节）。
- 判断是否设置成功：`curl -fsSI <对象URL>` 返回 200（403 表示 ACL 没生效 / 桶策略拒绝）。

### 6.2 防盗链：不要拦截自家域名

路径：控制台 →「对象存储」→「存储桶列表」→ 点 `anzhuangbao-1441295645` →
左侧「安全管理」→「防盗链设置」。

- 若**未开启**：保持关闭即可（默认）。
- 若**已开启**：白名单必须包含 `*.mianxiaocheng.cn` 与 `mianxiaocheng.cn`（含裸域），
  且「空 Referer 是否允许访问」建议设为 **允许**（App 内 WebView、部分浏览器直链下载不带 Referer，
  否则用户点下载会拿到 403）。
- 302 跳转后请求的 Referer 仍是站点域名，所以白名单对了就不会被拦。

### 6.3 CORS

路径：控制台 →「对象存储」→「存储桶列表」→ 点桶名 →「安全管理」→「跨域访问 CORS 设置」。

- 纯 `<a href>` 下载 / 302 跳转**不依赖 CORS**；CORS 主要给前端 `fetch` 读取
  `apk/latest.json`（显示版本、大小）用。
- 一键设置（best-effort，失败只告警不中断）：

```bash
cd /www/wwwroot/SmartCampus/frontend
sudo -n -u www npm run apk:publish -- --setup-cors
```

  等价于 AllowOrigin=`*`，Methods=GET/HEAD，MaxAge=600。
- 也可以控制台手工加一条规则：来源 `*`，操作 `GET`/`HEAD`，超时 600 秒。

### 6.4 其他建议

- 开「版本控制」可防误删/误覆盖（历史版本对象多占一点存储，成本很低）。
- 生命周期：`apk/releases/` 想长期留档就别配过期规则；`apk/mian02-latest` 不要配删除规则。
- 建议给桶开「日志管理」或在 CAM 侧开操作审计，便于排查谁传了什么。

---

## 7. 常见错误对照表

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| 上传 403 `AccessDenied` | 子账号没关联策略；策略 resource 的 APPID/桶名/region 不对；桶名拼错 | 对比 `cos-cam-policy.json` 与 `.cos.env`；确认策略已关联到该子用户 |
| 匿名下载 403 `AccessDenied` | 对象 ACL 不是 `public-read`（手工在控制台上传的对象默认继承桶 ACL=私有） | 用 `npm run apk:publish` 重传；或在控制台对象详情把 ACL 改成「公有读私有写」 |
| **HEAD 200 但下载 403** `DownloadForbidden` | COS 默认域名禁止匿名分发「.apk 后缀」或「APK Content-Type」的对象 | 改用无扩展名 key `apk/mian02-latest` + `application/octet-stream` + 只用 `filename*` 的 Content-Disposition（见第 5 节） |
| 403 `SignatureDoesNotMatch` | SecretKey 错/多余空格/引号；服务器时间偏差 > 15 分钟 | 重填 .cos.env；`timedatectl status` 或 `sudo ntpdate -u ntp.tencent.com` 校时 |
| 403 `RequestTimeTooSkewed` | 同上，服务器时钟漂移 | 校时后重试 |
| 403 只在浏览器出现，curl 正常 | 防盗链拦了 Referer | 「安全管理 → 防盗链设置」放行 `*.mianxiaocheng.cn`，允许空 Referer |
| `NoSuchBucket` / 域名里 region 不匹配 | region 写成 ap-shanghai 之类；COS_DOMAIN 与桶实际地域不一致 | 统一 `ap-guangzhou`，域名 `<bucket>.cos.ap-guangzhou.myqcloud.com` |
| 404 `NoSuchKey` | 对象 key 前缀不是 `apk/`；上传用了别的 `--prefix`；上传还没跑完 | `curl -I` 目标 URL 看 404；核对 `--dry-run` 打印的 key |
| 站点 302 了但下载 404 | nginx 已切到 COS，但 COS 上没对象 / 对象被删 | 立即 `--rollback`；补传对象后再 `--apply` |
| 切换后仍下到旧包 | 客户端缓存了之前的 200 响应 | 已加 `Cache-Control: no-store`；换浏览器/无痕窗验证，或给下载链接加 `?v=时间戳` |
| `nginx -t` 失败 | 手工编辑破坏了大括号/分号 | 用 `--rollback` 恢复备份（备份在 vhost 同目录） |
| `--apply` 提示「已存在未托管的同名 location」 | 有人手工加过 `location = /download/mian02.apk` | 先人工确认并删除手写块，再执行 `--apply` |

排错通用命令：

```bash
# 看真实状态码与跳转目标
curl -sSI https://www.mianxiaocheng.cn/download/mian02.apk
# 看跟随跳转后的最终响应
curl -sIL https://www.mianxiaocheng.cn/download/mian02.apk | head -40
# 只看 COS 对象
curl -fsSI https://anzhuangbao-1441295645.cos.ap-guangzhou.myqcloud.com/apk/mian02-latest
# 脚本状态总览（只读）
deploy/enable-cos-download.sh --status
```

---

## 8. 验收

```bash
cd /www/wwwroot/SmartCampus
deploy/verify-cos-download.sh; echo "exit=$?"
```

逐项含义：

| 项 | 检查 | 期望 |
| --- | --- | --- |
| a1 | COS 对象 HEAD | 200 |
| a2 | COS Content-Type | `application/octet-stream` |
| a3 | COS Content-Length | == 本地 `apk/download/mian02.apk` 大小 |
| a4 | COS **真实 GET**（最关键） | 200（HEAD 200 但 GET 403 就是默认域名拦截） |
| a5 | 真实下载字节数 | == 本地 APK 大小 |
| b1 | 本站 `/download/mian02.apk` HEAD | 未切换：200 且大小一致；已切换：302 且 Location 精确指向 `apk/mian02-latest` |
| c1 | `curl -sIL` 跟随跳转 | 200 |
| c2 | 最终 Content-Length | == 本地 APK 大小 |
| c3 | 端到端真实 GET（`-r 0-0`） | 200/206 |
| d1 | COS `apk/latest.json` | 200、可解析、sha256 == 本地 sha256 |
| d2 | latest.json size（若存在） | == 本地大小 |
| d3 | latest.json url | 指向当前对象 `apk/mian02-latest`（不一致只告警） |

- 全部 PASS → 退出码 0；
- 任一失败 → 退出码 1，并打印常见原因。
- 建议切换前后各跑一次，并把它加进发布后的例行检查（例如 cron 每日 9:00 跑一次，失败只记日志）。

**当前状态说明**：新对象 `apk/mian02-latest` 还没传时，a1~a5 会 FAIL，
b1 是「本机 200」、d 项若 latest.json 已有则 PASS——这是**正确**的区分：
「尚未切换、COS 上还没有可匿名下载的新对象」。此时线上用户下载不受影响（仍走本机文件）。

---

## 附录 A：一次完整操作的最小顺序

```bash
# 1. 配密钥（只做一次）
sudo -n install -o www -g www -m 600 /www/wwwroot/SmartCampus/deploy/cos.env.example /www/wwwroot/SmartCampus/.cos.env
sudo -n -u www vim /www/wwwroot/SmartCampus/.cos.env        # 填 SecretId/SecretKey

# 2. 首次上传（只做一次；之后出包自动上传）
cd /www/wwwroot/SmartCampus/frontend && sudo -n -u www npm run apk:publish

# 3. 验收（COS 侧应全 PASS）
cd /www/wwwroot/SmartCampus && deploy/verify-cos-download.sh

# 4. 切换 302
sudo -n /www/wwwroot/SmartCampus/deploy/enable-cos-download.sh --apply

# 5. 再验收（此时 b1 应是 302 指向 COS）
/www/wwwroot/SmartCampus/deploy/verify-cos-download.sh

# 6. 如需回滚
sudo -n /www/wwwroot/SmartCampus/deploy/enable-cos-download.sh --rollback
```

## 附录 B：密钥安全

- 子账号只给 `deploy/cos-cam-policy.json` 这一条策略，不用 `QcloudCOSFullAccess`。
- `.cos.env` 权限 600、属主 www，且已进 `.gitignore`；提交前用
  `git status --porcelain | grep -F '.cos.env'` 自查（应无输出）。
- 密钥只给服务器用；前端/APP 里**永远不要**出现 SecretId/SecretKey（前端只拿 URL）。
- 怀疑泄露：控制台停用旧密钥 → 建新密钥 → 更新 .cos.env → 跑一次 `publish-apk.mjs --sync` 验证。

## 附录 C：出问题时的兜底

1. **下载出问题（302 目标 404/403）**：立刻
   `sudo -n deploy/enable-cos-download.sh --rollback`，站点恢复本机静态文件，用户无感。
2. **上传出问题**：不影响线上下载（本机文件还在），先修密钥/策略，再重跑 `npm run apk:publish`。
3. **本机 APK 被误删**：从 COS 拉回即可
   `curl -fSLo /tmp/mian02.apk https://anzhuangbao-1441295645.cos.ap-guangzhou.myqcloud.com/apk/mian02-latest`
   再 `install -o www -g www -m 644` 放回 `apk/download/`。
4. **vhost 被改坏**：备份文件在 `/www/server/panel/vhost/nginx/python_backend.conf.bak-cos-*`，
   `sudo -n cp -a <备份> /www/server/panel/vhost/nginx/python_backend.conf` 后 `sudo -n /www/server/nginx/sbin/nginx -t && sudo -n /www/server/nginx/sbin/nginx -s reload`
