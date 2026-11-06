<template>
  <div ref="root" class="rs" :class="{ 'is-disabled': disabled }">
    <button
      type="button"
      class="rs-trigger"
      :class="{ 'is-open': open, 'is-filled': !!selectedOption }"
      :disabled="disabled"
      @click="toggle"
    >
      <span class="rs-value" :class="{ 'is-placeholder': !selectedOption }">
        {{ selectedOption ? selectedOption.label : placeholder }}
      </span>
      <span class="rs-arrow" :class="{ open }">⌄</span>
    </button>

    <Transition name="rs-pop">
      <div v-if="open" class="rs-popup" role="listbox">
        <div class="rs-popup-head">{{ placeholder }}</div>
        <div class="rs-popup-list">
          <button
            v-for="opt in options"
            :key="opt.id"
            type="button"
            class="rs-option"
            :class="{ 'is-selected': opt.id === modelValue }"
            role="option"
            :aria-selected="opt.id === modelValue"
            @click="select(opt.id)"
          >
            {{ opt.label }}
          </button>
          <p v-if="!options.length" class="rs-empty">暂无可选项</p>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

export interface RegSelectOption {
  id: number
  label: string
}

const props = withDefaults(
  defineProps<{
    modelValue: number
    options: RegSelectOption[]
    placeholder?: string
    disabled?: boolean
  }>(),
  {
    placeholder: '请选择',
    disabled: false,
  },
)

const emit = defineEmits<{
  (e: 'update:modelValue', v: number): void
  (e: 'change'): void
}>()

const open = ref(false)
const root = ref<HTMLElement | null>(null)
const selectedOption = computed(() => props.options.find((o) => o.id === props.modelValue) || null)

function toggle() {
  if (props.disabled) return
  open.value = !open.value
}

function close() {
  open.value = false
}

function select(id: number) {
  emit('update:modelValue', id)
  emit('change')
  close()
}

function onDocClick(e: MouseEvent) {
  if (!open.value) return
  if (root.value && !root.value.contains(e.target as Node)) close()
}

onMounted(() => document.addEventListener('click', onDocClick, true))
onBeforeUnmount(() => document.removeEventListener('click', onDocClick, true))
</script>

<style scoped>
.rs {
  position: relative;
}

/* 触发器：小号胶囊（椭圆矩形） */
.rs-trigger {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  height: 44px;
  padding: 0 18px;
  border: 1px solid #e8e8ec;
  border-radius: 22px;
  background: #ffffff;
  color: #16161a;
  font-size: 14.5px;
  font-family: inherit;
  cursor: pointer;
  outline: none;
  transition: border-color 0.16s ease, box-shadow 0.16s ease;
  -webkit-tap-highlight-color: transparent;
}
.rs-trigger.is-open {
  border-color: #111111;
  box-shadow: 0 0 0 3px rgba(17, 17, 17, 0.08);
}
.rs-trigger:disabled {
  color: #b4b4bc;
  background: #f7f7f8;
  cursor: default;
}
.rs-value {
  min-width: 0;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.rs-value.is-placeholder {
  color: #a4a4ac;
  font-size: 14px;
}
.rs-arrow {
  flex-shrink: 0;
  margin-left: 8px;
  color: #a4a4ac;
  font-size: 13px;
  line-height: 1;
  transition: transform 0.18s ease;
}
.rs-arrow.open {
  transform: rotate(180deg);
}

/* 弹出面板：缩小 + 椭圆矩形圆角 */
.rs-popup {
  position: absolute;
  left: 0;
  right: 0;
  top: calc(100% + 6px);
  z-index: 40;
  padding: 8px;
  border-radius: 20px;
  background: #ffffff;
  box-shadow:
    0 8px 28px rgba(20, 20, 25, 0.12),
    0 1px 2px rgba(20, 20, 25, 0.06);
}
.rs-popup-head {
  padding: 7px 10px 5px;
  font-size: 12px;
  color: #a4a4ac;
}
.rs-popup-list {
  max-height: 240px;
  overflow-y: auto;
  scrollbar-width: none;
}
.rs-popup-list::-webkit-scrollbar {
  display: none;
}
@media (max-width: 767px) {
  /* 移动端弹层限高：矮屏 / 键盘弹出时不会被挤出可视区 */
  .rs-popup-list {
    max-height: min(240px, 34vh);
  }
}
.rs-option {
  display: block;
  width: 100%;
  height: 40px;
  padding: 0 12px;
  border: none;
  border-radius: 14px;
  background: transparent;
  color: #16161a;
  font-size: 14.5px;
  font-family: inherit;
  text-align: left;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}
.rs-option:active {
  background: #f2f2f4;
}
.rs-option.is-selected {
  background: #111111;
  color: #ffffff;
  font-weight: 600;
}
.rs-empty {
  margin: 0;
  padding: 14px;
  font-size: 13px;
  color: #a4a4ac;
  text-align: center;
}

.rs-pop-enter-active,
.rs-pop-leave-active {
  transition:
    opacity 0.16s ease,
    transform 0.16s ease;
}
.rs-pop-enter-from,
.rs-pop-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
