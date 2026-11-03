/**
 * 上次登录账号。
 *
 * 退出登录时 `removeToken()` 会清掉登录态缓存（campus_user），回到登录页还得重输一遍学号/工号。
 * 这里把「本机上次登录的账号」单独落一个 key：退出登录**不清除**，登录页据此把学号填回输入框。
 * 只存学号/工号与登录时间，不含密码，也不存昵称、头像等其它信息。
 */
const LAST_ACCOUNT_KEY = 'campus_last_account'

export interface LastAccount {
  username: string
  /** 上次登录时间（毫秒时间戳） */
  loginAt: number
}

export function getLastAccount(): LastAccount | null {
  const raw = localStorage.getItem(LAST_ACCOUNT_KEY)
  if (!raw) return null
  try {
    const parsed = JSON.parse(raw) as LastAccount
    // 学号/工号是回填的唯一内容，缺失即视为无效缓存
    return parsed?.username ? parsed : null
  } catch {
    // 旧结构或手工篡改：当作没有，不影响登录
    return null
  }
}

/** 登录成功后记录；退出登录时不要调用对应的删除逻辑 */
export function saveLastAccount(username: string) {
  if (!username) return
  try {
    localStorage.setItem(LAST_ACCOUNT_KEY, JSON.stringify({ username, loginAt: Date.now() }))
  } catch {
    // 隐私模式 / 存储已满：回填失效不影响登录本身
  }
}
