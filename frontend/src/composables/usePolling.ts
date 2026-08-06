import { ref, onUnmounted } from 'vue'

export function usePolling(fn: () => Promise<void>, interval = 30000) {
  const pollingActive = ref(false)
  let timer: ReturnType<typeof setInterval> | null = null

  function start() {
    if (timer) return
    pollingActive.value = true
    fn()
    timer = setInterval(fn, interval)
  }

  function stop() {
    if (timer) {
      clearInterval(timer)
      timer = null
    }
    pollingActive.value = false
  }

  onUnmounted(stop)

  return { start, stop, pollingActive }
}
