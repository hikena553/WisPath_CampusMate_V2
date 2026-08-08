import type { Directive } from 'vue'

export const tilt: Directive<HTMLElement> = {
  mounted(el) {
    el.style.transformStyle = 'preserve-3d'
    el.style.transition = 'transform .18s ease, box-shadow .18s ease'
    el.addEventListener('mousemove', (e: MouseEvent) => {
      const r = el.getBoundingClientRect()
      const x = (e.clientX - r.left) / r.width - 0.5
      const y = (e.clientY - r.top) / r.height - 0.5
      el.style.transform = `rotateY(${x * 6}deg) rotateX(${-y * 6}deg)`
      el.style.boxShadow = `0 ${6 + Math.abs(y * 8)}px 14px rgba(0,0,0,.10)`
    })
    el.addEventListener('mouseleave', () => {
      el.style.transform = ''
      el.style.boxShadow = ''
    })
  },
}
