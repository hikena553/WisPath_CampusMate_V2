/**
 * body 滚动锁（引用计数版）
 *
 * 为什么需要引用计数：覆盖层是会叠的 —— 校园资讯的主页 → 搜索子页 → 资讯详情子页
 * 可以同时存在三层。每层关闭时都执行 `body.style.overflow = ''` 的话，
 * 上层关闭会把还在屏幕上的下层的锁一起抹掉，用户能在背景上滑动页面（真实 bug，
 * 此前 CampusSearchPage 靠 MutationObserver 反向补救）。
 *
 * 用法（两种风格等价，可混用）：
 *   1. const release = lockBodyScroll(); release()   // 幂等；最后一层释放时才恢复原值
 *   2. lockBodyScroll(); ...; unlockBodyScroll()     // 成对调用的旧风格
 *
 * 语义：
 * - 第一次加锁时记下原始 inline overflow，最后一层释放时原样写回（不假设是 ''）；
 * - release / unlockBodyScroll 均幂等，重复调用只有第一次生效。
 */

let lockCount = 0
let originalOverflow = ''

/** 当前是否有任何一层在持锁（调试与单测用） */
export function isBodyScrollLocked(): boolean {
  return lockCount > 0
}

// 每次 lockBodyScroll() 的释放句柄都登记在此，unlockBodyScroll 按后进先出释放；
// 若调用方已用返回的 release 提前释放，此处残留的是幂等空操作，无副作用。
const releases: Array<() => void> = []

/**
 * 锁住 body 滚动，返回释放函数。
 * 注意：恢复的是**加锁那一刻**的 inline 值，所以别在持锁期间用别的代码改 body.style.overflow。
 */
export function lockBodyScroll(): () => void {
  if (typeof document === 'undefined') return () => {}

  if (lockCount === 0) {
    originalOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
  }
  lockCount += 1

  let released = false
  const release = () => {
    if (released) return
    released = true
    lockCount = Math.max(0, lockCount - 1)
    if (lockCount === 0) {
      document.body.style.overflow = originalOverflow
      originalOverflow = ''
    }
  }
  releases.push(release)
  return release
}

/** 旧风格解锁：释放最近一次尚未释放的锁；多余调用幂等无害。 */
export function unlockBodyScroll(): void {
  const release = releases.pop()
  release?.()
}
