import { createApp, defineComponent, h, reactive, nextTick } from 'vue'
import { ElMessageBox, ElInput } from 'element-plus'
import ActionSheet from '@/components/common/ActionSheet.vue'

/**
 * useActionSheet —— 指令式「底部动作面板」确认 / 提示 / 单行输入。
 *
 * 移动端（<768px）：ElMessageBox 的居中对话框不符合移动端习惯，
 * 统一降级为底部半屏动作面板（ActionSheet.vue），微信 / iOS 范式；
 * 桌面端（>=768px）：保持 ElMessageBox（样式见 dialog-minimal.css）。
 *
 * 用法（与 ElMessageBox 几乎对齐，替换成本最低）：
 *   const ok = await actionConfirm('确定删除该项目？', '确认', { danger: true })
 *   await actionAlert('公告内容', '紧急公告')
 *   const name = await actionPrompt('请输入备注名', '备注', oldName)
 */

interface ConfirmOptions {
  /** 确认按钮文案，默认「确认」 */
  confirmButtonText?: string
  /** 取消按钮文案，默认「取消」 */
  cancelButtonText?: string
  /** 危险操作：确认按钮显示为红色 */
  danger?: boolean
}

interface AlertOptions {
  /** 内容按 HTML 渲染（仅限可信内容） */
  dangerouslyUseHTMLString?: boolean
  /** 确认按钮文案 */
  confirmButtonText?: string
}

interface PromptOptions {
  /** 输入框占位 */
  placeholder?: string
  /** 确认按钮文案 */
  confirmButtonText?: string
  /** 取消按钮文案 */
  cancelButtonText?: string
  /** 危险操作：确认按钮显示为红色 */
  danger?: boolean
}

function isMobileViewport(): boolean {
  return typeof window !== 'undefined' && window.matchMedia('(max-width: 767px)').matches
}

// ===== 单例宿主（惰性挂载） =====
interface SheetState {
  visible: boolean
  mode: 'confirm' | 'alert' | 'prompt'
  title: string
  message: string
  html: boolean
  danger: boolean
  inputValue: string
  placeholder: string
  confirmText: string
  cancelText: string
}

const state = reactive<SheetState>({
  visible: false,
  mode: 'confirm',
  title: '',
  message: '',
  html: false,
  danger: false,
  inputValue: '',
  placeholder: '',
  confirmText: '确认',
  cancelText: '取消',
})

type Resolver = (v: unknown) => void
let resolver: Resolver | null = null
let mounted = false

function finish(v: unknown) {
  state.visible = false
  const r = resolver
  resolver = null
  r?.(v)
}

const Host = defineComponent({
  name: 'ActionSheetHost',
  setup() {
    async function onConfirm() {
      if (state.mode === 'prompt') {
        const v = state.inputValue.trim()
        if (!v) return // 空输入不放行
        finish(v)
      } else {
        finish(true)
      }
    }
    function onCancel() { finish(state.mode === 'confirm' ? false : null) }
    return () => h(ActionSheet, {
      modelValue: state.visible,
      'onUpdate:modelValue': (v: boolean) => { if (!v) onCancel() },
      title: state.title,
      width: '420px',
    }, {
      default: () => [
        h('div', { class: 'action-sheet-msg' }, [
          state.html
            ? h('div', { class: 'action-sheet-text', innerHTML: state.message })
            : h('div', { class: 'action-sheet-text' }, state.message),
          state.mode === 'prompt'
            ? h(ElInput, {
                modelValue: state.inputValue,
                'onUpdate:modelValue': (v: string) => { state.inputValue = v },
                placeholder: state.placeholder,
                maxlength: 50,
                onKeydown: (e: Event | KeyboardEvent) => { const k = e as KeyboardEvent; if (k.key === 'Enter') onConfirm() },
                class: 'action-sheet-input',
              })
            : null,
        ]),
      ],
      footer: () => [
        h('button', { class: 'action-sheet-btn', type: 'button', onClick: onCancel }, state.cancelText),
        h('button', {
          class: ['action-sheet-btn', 'action-sheet-btn--primary', { 'action-sheet-btn--danger': state.danger }],
          type: 'button',
          onClick: onConfirm,
        }, state.confirmText),
      ],
    })
  },
})

// 宿主样式（非 scoped，跟随单例注入一次）
const HOST_CSS = `
.action-sheet-msg { display: flex; flex-direction: column; gap: 14px; }
.action-sheet-text { font-size: 13.5px; line-height: 1.7; color: #4a4f58; word-break: break-word; }
.action-sheet-input .el-input__wrapper { border-radius: 10px; }
.action-sheet-btn {
  flex: 1;
  height: 42px;
  border: 1px solid #e2e4ea;
  border-radius: 10px;
  background: #fff;
  font-size: 14.5px;
  font-weight: 600;
  color: #1c1e21;
  cursor: pointer;
}
.action-sheet-btn:active { background: #f4f5f8; }
.action-sheet-btn--primary { background: #1c1e21; border-color: #1c1e21; color: #fff; }
.action-sheet-btn--primary:active { background: #33363b; }
.action-sheet-btn--danger { background: #e5484d; border-color: #e5484d; color: #fff; }
.action-sheet-btn--danger:active { background: #d9383d; }
`
// 桌面端没有 ActionSheet 宿主时也需要这段按钮样式吗？不需要——桌面走 ElMessageBox。
function ensureHost() {
  if (mounted || typeof document === 'undefined') return
  const host = document.createElement('div')
  document.body.appendChild(host)
  const style = document.createElement('style')
  style.textContent = HOST_CSS
  document.head.appendChild(style)
  createApp(Host).mount(host)
  mounted = true
}

// 串行队列：前一个面板未关闭时，后续调用排队等待
let chain: Promise<unknown> = Promise.resolve()

function enqueue<T>(run: () => Promise<T>): Promise<T> {
  const next = chain.then(run, run)
  chain = next.then(() => undefined, () => undefined)
  return next
}

/** 确认对话：返回 true（确认）/ false（取消） */
export function actionConfirm(message: string, title = '确认', options: ConfirmOptions = {}): Promise<boolean> {
  if (!isMobileViewport()) {
    return ElMessageBox.confirm(message, title, {
      confirmButtonText: options.confirmButtonText,
      cancelButtonText: options.cancelButtonText,
      type: 'warning',
    }).then(() => true).catch(() => false)
  }
  return enqueue(() => new Promise<boolean>((resolve) => {
    ensureHost()
    Object.assign(state, {
      visible: false, mode: 'confirm', title, message, html: false,
      danger: !!options.danger,
      confirmText: options.confirmButtonText ?? '确认',
      cancelText: options.cancelButtonText ?? '取消',
    } satisfies Partial<SheetState>)
    resolver = resolve as Resolver
    nextTick(() => { state.visible = true })
  }))
}

/** 轻提示：只有确认按钮 */
export function actionAlert(message: string, title = '提示', options: AlertOptions = {}): Promise<void> {
  if (!isMobileViewport()) {
    return ElMessageBox.alert(message, title, {
      dangerouslyUseHTMLString: options.dangerouslyUseHTMLString,
      confirmButtonText: options.confirmButtonText,
    }).then(() => undefined)
  }
  return enqueue(() => new Promise<void>((resolve) => {
    ensureHost()
    Object.assign(state, {
      visible: false, mode: 'alert', title, message,
      html: !!options.dangerouslyUseHTMLString,
      confirmText: options.confirmButtonText ?? '知道了',
      cancelText: '取消', danger: false,
    } satisfies Partial<SheetState>)
    resolver = resolve as Resolver
    nextTick(() => { state.visible = true })
  }))
}

/** 单行输入：返回输入值；取消返回 null */
export function actionPrompt(message: string, title: string, defaultValue = '', options: PromptOptions = {}): Promise<string | null> {
  if (!isMobileViewport()) {
    return ElMessageBox.prompt(message, title, {
      inputValue: defaultValue,
      inputPlaceholder: options.placeholder,
      confirmButtonText: options.confirmButtonText,
      cancelButtonText: options.cancelButtonText,
    }).then(({ value }) => (value as string) ?? null).catch(() => null)
  }
  return enqueue(() => new Promise<string | null>((resolve) => {
    ensureHost()
    Object.assign(state, {
      visible: false, mode: 'prompt', title, message, html: false,
      inputValue: defaultValue ?? '',
      placeholder: options.placeholder ?? '请输入',
      confirmText: options.confirmButtonText ?? '确定',
      cancelText: options.cancelButtonText ?? '取消',
      danger: !!options.danger,
    } satisfies Partial<SheetState>)
    resolver = resolve as Resolver
    nextTick(() => { state.visible = true })
  }))
}
