/**
 * 全站共用的 body 滚动锁（引用计数版）。
 *
 * 页内浮层会层层叠加（搜索页 → 资讯详情 → 阅读器），每层各自打开时都要锁住背景滚动。
 * 早先各处直接写 `document.body.style.overflow`：后关闭的那层把值清空，
 * 会把仍在打开的上层一起解锁 —— 背景跟着手指滚。改成计数后，
 * 只有最后一层关闭才真正恢复滚动。
 */
let lockCount = 0
let savedOverflow = ''

export function lockBodyScroll() {
  lockCount += 1
  if (lockCount === 1) {
    savedOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
  }
}

export function unlockBodyScroll() {
  if (lockCount === 0) return
  lockCount -= 1
  if (lockCount === 0) {
    document.body.style.overflow = savedOverflow
    savedOverflow = ''
  }
}
