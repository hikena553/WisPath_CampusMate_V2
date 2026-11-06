/**
 * 第三方登录总开关。
 *
 * 短信通道与 QQ 互联仍在申请中，暂不向前台开放：
 * - 登录页不展示「其他登录方式」中的手机号 / QQ 一键登录；
 * - 注册页不展示手机号短信验证与 QQ 授权窗口，改为直接填写手机号、QQ 号。
 *
 * 资质申请通过、后端 `.env` 配置好短信与 QQ 密钥后，把这里改为 true 即可恢复。
 */
export const THIRD_PARTY_AUTH_ENABLED: boolean = false
