import { ref, watch } from 'vue'

const STORAGE_KEY = 'theme_mode'
const isDark = ref(localStorage.getItem(STORAGE_KEY) === 'dark')

function applyTheme(dark: boolean) {
  if (dark) {
    document.documentElement.classList.add('dark')
  } else {
    document.documentElement.classList.remove('dark')
  }
}

applyTheme(isDark.value)

watch(isDark, (val) => {
  applyTheme(val)
  localStorage.setItem(STORAGE_KEY, val ? 'dark' : 'light')
})

export function useTheme() {
  function toggle() {
    isDark.value = !isDark.value
  }

  function setTheme(mode: 'light' | 'dark') {
    isDark.value = mode === 'dark'
  }

  return {
    isDark,
    toggle,
    setTheme,
  }
}
