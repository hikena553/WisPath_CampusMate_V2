/**
 * 「消息通知」系统会话的展示数据。
 *
 * 会话列表和消息搜索页都把它当成一条普通会话来显示，所以数据放在这里共用一份，
 * 避免两处各写一段文案、改一处漏一处。
 *
 * 通知本身按「微信服务通知卡片」的结构组织（来源 + 标题 + 若干字段），
 * 而不是一段纯文本：一条通知里通常有六七项信息，揉成一句话读起来很吃力。
 * 卡片不再带底部入口，要办的事由用户自己去对应业务页，通知只负责告知。
 *
 * 目前是纯前端展示（写死）。接后端时只改这个文件即可：
 *   summary / unread ← 通知列表的第一条与未读数
 *   systemNoticeCards() ← 库里那几条通知按这里的字段映射过来
 */
export interface SystemNoticeField {
  label: string
  value: string
}

export interface SystemNoticeCard {
  id: number
  /** 通知来源：圆形图标里的一个字 + 底色（对应微信里那个小程序 logo） */
  app: { name: string; glyph: string; color: string }
  /** 卡片大标题，例如「期末考试安排通知」 */
  title: string
  /** 灰字标签 + 黑字值的若干行 */
  fields: SystemNoticeField[]
  created_at: string
}

/**
 * 「从消息通知点进来」的来处标记。
 *
 * 挂在目标页地址上（`?from=msg-notice`），业务页据此决定返回键往哪走：
 * 学业中心那类「一个页面装着一排子页」的页，返回键默认是回它自己的驾驶舱主页，
 * 从通知进来时那样退会把人丢进一个他压根没去过的页面。
 */
export const NOTICE_ORIGIN = 'msg-notice'

/** 距离现在若干分钟前的时间（列表和卡片都用它，所以时间永远不会「过期」） */
export function minutesAgo(minutes: number): string {
  return new Date(Date.now() - minutes * 60e3).toISOString()
}

export const SYSTEM_NOTICE = {
  /** 会话 key：以 n- 开头，和私聊 s-<id>、群聊 g-<id> 区分开 */
  key: 'n-notice',
  name: '消息通知',
  summary: '期末成绩已发布，请及时查看本学期绩点与学分',
  /** 列表上那枚红点的初始值 */
  unread: 1,
} as const

/** 「消息通知」会话的地址：消息页 onMounted 会读 chat 参数把会话重新打开 */
export const SYSTEM_NOTICE_ROUTE: { name: string; query: { chat: string } } = {
  name: 'student-messages',
  query: { chat: SYSTEM_NOTICE.key },
}

/**
 * 打开「消息通知」后展示的三条系统通知（只读）。
 * 按时间正序排（旧 → 新）：会话窗口打开时会滚到底部，最新的一条必须在最下面。
 */
export function systemNoticeCards(): SystemNoticeCard[] {
  return [
    {
      id: -103,
      app: { name: '自习室', glyph: '习', color: '#0f9d8f' },
      title: '今日专注目标未完成',
      fields: [
        { label: '今日专注', value: '0 次 · 0 分钟' },
        { label: '本周目标', value: '5 小时（已完成 1.5 小时）' },
        { label: '建议时段', value: '今晚 19:00-21:00' },
        { label: '提示', value: '专注期间手机放包里，结束后自动记入学时' },
      ],
      created_at: minutesAgo(26 * 60),
    },
    {
      id: -102,
      app: { name: '学工部', glyph: '学', color: '#e8833a' },
      title: '请假申请已通过',
      fields: [
        { label: '请假类型', value: '病假 · 2 天' },
        { label: '起止时间', value: '2026-11-03 至 2026-11-04' },
        { label: '审批人', value: '辅导员 王老师' },
        { label: '提示', value: '返校后请到「我的申请」补交就诊证明' },
      ],
      created_at: minutesAgo(190),
    },
    {
      id: -101,
      app: { name: '教务处', glyph: '教', color: '#2f6fed' },
      title: '期末成绩已发布',
      fields: [
        { label: '学期', value: '2026—2027 学年第一学期' },
        { label: '平均绩点', value: '3.72 / 4.0' },
        { label: '已修学分', value: '24.5 分' },
        { label: '提示', value: '对成绩有疑问，可在发布后 3 个工作日内申请复核' },
      ],
      created_at: minutesAgo(26),
    },
  ]
}

/**
 * 卡片顶部那行居中的时间：`11月2日 下午2:03`
 *
 * 微信里服务通知的时间永远是「日期 + 12 小时制」，不用「昨天 / 3 分钟前」——
 * 这类通知是对账凭据，用户往往要回头核对具体时刻。
 */
export function formatNoticeTime(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  const h = d.getHours()
  const period = h < 6 ? '凌晨' : h < 12 ? '上午' : h < 13 ? '中午' : h < 18 ? '下午' : '晚上'
  const hour12 = h % 12 || 12
  const min = String(d.getMinutes()).padStart(2, '0')
  return `${d.getMonth() + 1}月${d.getDate()}日 ${period}${hour12}:${min}`
}
