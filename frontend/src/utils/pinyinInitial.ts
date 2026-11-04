/**
 * 姓名首字母：通讯录的 A-Z 分组用。
 *
 * 不引拼音库（pinyin-pro 之类）—— 只需要「首字的首字母」，而浏览器自带的 ICU
 * 中文排序就是按拼音排的：拿首字和每组 pinyin 顺序最靠前的那个汉字比一次
 * `localeCompare(…, 'zh-CN')`，比它大就说明落在这一组或更后面。
 * 比「引一个几百 KB 的词典」便宜得多，也不需要维护码表。
 *
 * 已知取舍：多音字按 ICU 的默认读音走（曾 → C、重 → Z），姓名里会有个别偏差；
 * 对「找个人」这个场景足够，真要精确就得引词典，不值得。
 */

/** 每个字母分组的「第一个汉字」：拼音序最小、且该组里确实存在的字 */
const BOUNDARIES: Array<[string, string]> = [
  ['A', '阿'],
  ['B', '八'],
  ['C', '擦'],
  ['D', '搭'],
  ['E', '峨'],
  ['F', '发'],
  ['G', '噶'],
  ['H', '哈'],
  ['J', '击'],
  ['K', '喀'],
  ['L', '拉'],
  ['M', '妈'],
  ['N', '拿'],
  ['O', '哦'],
  ['P', '啪'],
  ['Q', '期'],
  ['R', '然'],
  ['S', '撒'],
  ['T', '塌'],
  ['W', '挖'],
  ['X', '昔'],
  ['Y', '压'],
  ['Z', '匝'],
]

/** 汉字范围：这之外的（英文、数字、符号、emoji）另有规则 */
const HAN = /[\u4e00-\u9fa5]/

/**
 * 取姓名的索引字母：中文按拼音首字母，英文按首字母大写，
 * 数字 / 符号 / 空 → 「#」（排到最后，和电话簿的习惯一致）。
 */
export function initialOf(name: string): string {
  const ch = (name || '').trim().charAt(0)
  if (!ch) return '#'
  if (/[a-zA-Z]/.test(ch)) return ch.toUpperCase()
  if (!HAN.test(ch)) return '#'
  let letter = '#'
  for (const [key, anchor] of BOUNDARIES) {
    // 边界是升序的：一旦比不过，后面的更比不过
    if (ch.localeCompare(anchor, 'zh-CN') >= 0) letter = key
    else break
  }
  return letter
}

/** 好友名单的排序：先按索引字母，再按姓名（同一字母内仍按拼音序） */
export const INDEX_KEYS = [...'ABCDEFGHIJKLMNOPQRSTUVWXYZ', '#']

export function indexOrder(letter: string): number {
  const i = INDEX_KEYS.indexOf(letter)
  return i >= 0 ? i : INDEX_KEYS.length
}
