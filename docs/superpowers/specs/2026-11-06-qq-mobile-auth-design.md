# QQ 移动端登录/注册 设计（QQ 互联移动应用）

日期：2026-11-06 ｜ 状态：已确认，实施中

## 背景

- Web 端 QQ 互联网站应用 OAuth（authorize → callback → exchange）代码已全量存在，但卡在网站应用资质（备案域名），由 `features.ts` 的 `THIRD_PARTY_AUTH_ENABLED=false` 关闭。
- 用户已在 QQ 互联平台注册**移动应用（Android）**：AppID `1906302158`，登记签名 `8f34d72960bc51e872a904cd1b2e6590`。移动应用不需要备案域名，走 Android 官方 SDK 授权。
- 注册页已强制收集 QQ 号（仅找回密码辅助，非登录凭据）。

## 目标形态

App 内（Capacitor 壳）：

```
登录页「QQ」按钮 → 原生插件拉起手机 QQ 授权（AppID 1906302158）
  → access_token + openid
  → POST /api/auth/qq/mobile/authorize（服务端向 graph.qq.com 核验）
      ├─ 已绑定校园账号 → 登录进首页
      └─ 未绑定 → 一次性注册票据 → /register?qq_ticket=..&qq_nickname=..
            → 补全学号/姓名/密码/学院/专业 → 注册并自动登录
```

浏览器端一切行为不变（Web QQ 入口与短信维持关闭）。注册页 QQ 授权后继续完善学籍信息，即「QQ 注册、注册后继续完善登录信息」。

## 后端

1. `qq_oauth_service.verify_mobile_token(access_token, openid)`：调 `graph.qq.com/oauth2.0/me`，校验 `client_id == QQ_APP_ID` 且 openid 一致，顺带取昵称（best effort）。access_token 用后即弃，**不落库**。
2. `POST /api/auth/qq/mobile/authorize`：200 + `{status: "login", login: <LoginResponse>}` 或 `{status: "unregistered", register_ticket, nickname}`（复用 `create_register_ticket`，15 分钟）。MEDIA/ADMIN 拒绝；限流。**只要求 QQ_APP_ID 配置（不要求 AppKey）**——AppKey 仅网站应用 OAuth 需要。
3. `POST /api/auth/qq/mobile/bind`：已登录用户绑定 openid，占用 409。
4. 修存量 bug：`POST /register` 在「仅 QQ 票据、无手机号」时 `_require_phone(None)` 400（网页版 QQ 授权注册本就因此不可用）。改为 QQ 票据通道手机号选填；phone 为 None 时跳过唯一性查询（防 `== None` 误匹配 NULL 行）。schema/模型/迁移均不动。

## Android（Capacitor 壳）

- 官方 QQ OpenSDK aar → `android/app/libs/`。
- `QQAuthPlugin`（`isQQInstalled` / `login` / `logout`）；`MainActivity.onCreate` 注册插件；`handleOnActivityResult` → `Tencent.onActivityResultData` 转发授权结果。
- Manifest：`AuthActivity`（scheme `tencent${qqAppId}`，exported）+ `AssistActivity` + `<queries><package com.tencent.mobileqq/></queries>`（API 30+ 包可见性，targetSdk 35 必需）。
- AppID 单一来源：gradle `QQ_APP_ID`（env 可覆盖，默认 1906302158）→ manifestPlaceholder + `BuildConfig.QQ_APP_ID`。FileProvider 已有（`${applicationId}.fileprovider`），零改动。

## 前端

- `features.ts` 新增 `QQ_NATIVE_AUTH_ENABLED = true`；`THIRD_PARTY_AUTH_ENABLED` 维持 false 不动。
- `utils/qqAuth.ts`：`Capacitor.isNativePlatform()` + 插件探测与调用；不满足则抛「不可用」，调用方回退现状。
- `api/auth.ts`：`qqMobileAuthorizeApi` / `qqMobileBindApi`。
- 登录页：App 内 QQ 按钮 = QQ 授权登录（取代该按钮原「本机一键登录回退」）；手机号一键登录按钮不动；错误映射：未装 QQ → 引导、取消 → 轻提示、其余 → detail。
- 注册页：3 处 gate（verify-tabs 显示、validate、onMounted ticket 读取）从 `thirdPartyAuthEnabled` 扩为 `thirdPartyAuthEnabled || qqNativeEnabled`；QQ 模式手机号选填（提交 null）；`captchaRequired` 同步扩展（qq_ticket 存在时后端本就跳过图形验证码）。
- 个人中心 `QuickLoginBind`：App 内绑定/重新授权走插件 + mobile/bind。

## 上线清单

- `.env`：`QQ_APP_ID=1906302158`（AppKey 后补不影响移动链路）。
- ⚠️ QQ 互联后台 Android 包名必须为 `com.mian02.campus`（登记的 `SmartCampus` 是 APK 文件名，需在控制台改并重新提审），签名 MD5 与出包 keystore 一致。
- 应用过审前用协作者/管理员 QQ 号测试；模拟器演示需装手机 QQ。

## 验证

- 后端 pytest（mock graph.qq.com）：绑定登录 / 未注册票据 / 绑定冲突 / 非法 token / MEDIA·ADMIN 拒绝 / QQ 票据注册免手机号。
- 后端 `import app.main` 冒烟；前端 `npm run build` 零错 + vitest；Android gradle 出包。
- Web 回归：浏览器端三页行为与现状完全一致。
- 服务收尾：验证用 uvicorn/vite 全部杀干净。
