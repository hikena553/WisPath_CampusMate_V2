# QQ OpenSDK aar 放置目录

把从 **QQ 互联控制台**（https://open.qq.com → 应用管理 → 对应移动应用 → SDK 下载 → Android）
下载的官方 `open_sdk_*.aar` 原样放进本目录，重新执行 `npm run apk` 即可启用 App 内 QQ 授权登录。

- 本目录没有 aar 时工程照常构建，只是 `QQAuthPlugin` 不参与编译、不注册（见
  `app/build.gradle` 的 sourceSets 条件剔除与 `MainActivity` 的条件注册）。
- **没有 aar 时网页侧的 QQ 入口会自动隐藏**：`src/utils/qqAuth.ts` 的
  `qqNativeAuthAvailable()` 会同时探测「原生壳」与「插件是否注册」，登录页 / 注册页 /
  个人中心不再展示点了必然失败的 QQ 按钮，也不会再弹「QQ 登录失败，请使用账号密码登录」。
  `npm run apk` 检测不到 aar 时会在日志里给出告警。
- aar 必须用官方包：QQ 客户端会校验调用方的包名（`com.mian02.campus`）与签名，
  第三方改包会导致授权失败且过不了腾讯审核。
- AppID 单一来源在 `app/build.gradle`（默认 1906302158，环境变量 `QQ_APP_ID` 可覆盖），
  manifest 的 `tencent{appid}` scheme 与插件运行时 `createInstance` 都读它。
