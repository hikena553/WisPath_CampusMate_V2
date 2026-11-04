/**
 * 后端时间戳解析（全站统一口径）。
 *
 * 后端在 SQLite 上存的是「无时区的 UTC」：列类型是 DateTime，
 * 默认值取 `datetime.now(timezone.utc)`，落库后时区信息就丢了，
 * Pydantic 序列化出来是 `2026-11-04T16:12:11.139150` 这种**不带 Z** 的字符串。
 *
 * JS 的 `new Date('2026-11-04T16:12:11')` 会按**本地时间**解析，
 * 于是在 UTC+8 下，刚发出去的帖子会被算成 8 小时前 ——
 * 列表里显得像「昨天」，详情里则直接差出一个日期。
 *
 * 这里统一补齐时区再解析：本来就带 `Z` / `+08:00` 的原样交给 Date，
 * 不带的一律按 UTC 处理。时间戳本身仍是 UTC 语义，展示层再转本地时区。
 */
export function parseServerTime(value: string | null | undefined): number {
  if (!value) return Number.NaN
  const s = String(value).trim()
  if (!s) return Number.NaN
  // 已经带时区标记（Z / +08:00 / +0800）的不用补
  if (/(?:Z|[+-]\d{2}:?\d{2})$/.test(s)) return Date.parse(s)
  // `2026-11-04 16:12:11` 这种空格分隔的写法也一并兜住
  return Date.parse(`${s.replace(' ', 'T')}Z`)
}
