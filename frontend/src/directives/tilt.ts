import type { Directive } from 'vue'

export const tilt: Directive<HTMLElement> = {
  mounted(el) {
    el.style.transformStyle = 'preserve-3d'
    el.style.transition = 'transform .18s ease, box-shadow .18s ease'

    const onMove = (e: MouseEvent) => {
      const r = el.getBoundingClientRect()
      const x = (e.clientX - r.left) / r.width - 0.5
      const y = (e.clientY - r.top) / r.height - 0.5
      el.style.transform = `rotateY(${x * 6}deg) rotateX(${-y * 6}deg)`
      el.style.boxShadow = `0 ${6 + Math.abs(y * 8)}px 14px rgba(0,0,0,.10)`
    }

    const onLeave = () => {
      el.style.transform = ''
      el.style.boxShadow = ''
    }

    el.addEventListener('mousemove', onMove)
    el.addEventListener('mouseleave', onLeave)

    ;(el as any).__tiltMove = onMove
    ;(el as any).__tiltLeave = onLeave
  },
  unmounted(el) {
    el.removeEventListener('mousemove', (el as any).__tiltMove)
    el.removeEventListener('mouseleave', (el as any).__tiltLeave)
    delete (el as any).__tiltMove
    delete (el as any).__tiltLeave
  },
}
