<template>
  <Teleport to="body">
    <Transition name="sheet">
      <div v-if="visible" class="sheet-mask" @click.self="close">
        <div class="sheet" role="dialog" aria-modal="true">
          <div class="sheet-grabber"></div>

          <div class="sheet-header">
            <div class="sheet-title">{{ conv?.title || '对话' }}</div>
            <div v-if="subtitle" class="sheet-subtitle">{{ subtitle }}</div>
          </div>

          <div class="sheet-group">
            <button type="button" class="sheet-item" @click="pick('rename')">
              <span class="sheet-icon"><el-icon :size="18"><Edit /></el-icon></span>
              <span class="sheet-label">重命名</span>
            </button>
            <button type="button" class="sheet-item" @click="pick(conv?.pinned ? 'unpin' : 'pin')">
              <span class="sheet-icon"><el-icon :size="18"><Top /></el-icon></span>
              <span class="sheet-label">{{ conv?.pinned ? '取消置顶' : '置顶' }}</span>
            </button>
          </div>

          <div v-if="stages.length" class="sheet-group">
            <div class="sheet-sub">
              <span>项目阶段</span>
              <span class="sheet-sub-hint">{{ conv?.project_stage || '未设置' }}</span>
            </div>
            <div class="sheet-stages">
              <button
                v-for="s in stages"
                :key="s"
                type="button"
                :class="['sheet-stage', { active: s === conv?.project_stage }]"
                @click="pickStage(s)"
              >
                <el-icon v-if="s === conv?.project_stage" :size="12"><Check /></el-icon>
                <span>{{ s }}</span>
              </button>
            </div>
          </div>

          <div class="sheet-group">
            <button type="button" class="sheet-item danger" @click="pick('delete')">
              <span class="sheet-icon danger"><el-icon :size="18"><Delete /></el-icon></span>
              <span class="sheet-label">删除对话</span>
            </button>
          </div>

          <button type="button" class="sheet-cancel" @click="close">取消</button>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Check, Delete, Edit, Top } from '@element-plus/icons-vue'
import type { Conversation } from '@/stores/conversation'
import { conversationSubtitle, stagesOf } from './conversationMeta'

/** 面板内的动作命令（仅本地使用，<script setup> 不允许 ES 模块导出） */
type SheetCommand = 'rename' | 'pin' | 'unpin' | 'delete'

const props = defineProps<{
  visible: boolean
  conv: Conversation | null
}>()

/** command 取值：rename | pin | unpin | delete */
const emit = defineEmits<{
  'update:visible': [value: boolean]
  command: [cmd: string]
  stage: [stage: string]
}>()

const stages = computed(() => stagesOf(props.conv?.project_template))
/** 副标题：更新时间 + 项目阶段进度 */
const subtitle = computed(() => conversationSubtitle(props.conv))

function close() {
  emit('update:visible', false)
}

/** 先收起面板再执行动作：prompt / confirm 弹窗需要面板让位 */
function pick(cmd: SheetCommand) {
  close()
  emit('command', cmd)
}

function pickStage(stage: string) {
  close()
  emit('stage', stage)
}
</script>

<style scoped>
.sheet-mask {
  position: fixed; inset: 0; z-index: 3000;
  background: rgba(15, 23, 42, .45);
  display: flex; align-items: flex-end;
  -webkit-backdrop-filter: blur(3px);
  backdrop-filter: blur(3px);
}
/* 豆包式底部动作表：白底 + 发丝分隔线 + 纯图标（不用色块图标） */
.sheet {
  width: 100%; max-width: 440px; margin: 0 auto;
  background: #fff;
  border-radius: 16px 16px 0 0;
  padding: 6px 12px calc(12px + env(safe-area-inset-bottom, 0px));
  box-shadow: 0 -8px 32px rgba(15, 23, 42, .22);
  max-height: 84vh; overflow-y: auto;
  overscroll-behavior: contain;
}
.sheet-grabber {
  width: 36px; height: 4px; border-radius: 2px;
  background: #e2e4e9; margin: 6px auto 10px;
}
.sheet-header { padding: 0 6px 12px; text-align: center; }
.sheet-title {
  font-size: 15px; font-weight: 600; color: #1f2937;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.sheet-subtitle {
  margin-top: 4px; font-size: 12px; color: #9aa0a6;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.sheet-group {
  background: #f7f8fa; border-radius: 12px; margin-bottom: 10px;
  overflow: hidden;
}
.sheet-item {
  display: flex; align-items: center; gap: 12px; width: 100%;
  min-height: 52px; padding: 10px 14px;
  border: none; background: transparent;
  font-size: 15px; color: #374151; text-align: left; cursor: pointer;
  transition: background .15s ease;
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
}
.sheet-item + .sheet-item { box-shadow: inset 0 1px 0 rgba(15, 23, 42, .05); }
.sheet-item:hover, .sheet-item:active { background: rgba(15, 23, 42, .04); }
.sheet-icon {
  flex-shrink: 0; width: 22px; display: flex; align-items: center; justify-content: center;
  color: #6b7280;
}
.sheet-icon.danger { color: #ef4444; }
.sheet-label { flex: 1; min-width: 0; }
.sheet-item.danger .sheet-label { color: #ef4444; }
.sheet-item.danger:hover, .sheet-item.danger:active { background: rgba(239, 68, 68, .06); }

.sheet-sub {
  display: flex; align-items: baseline; justify-content: space-between; gap: 8px;
  font-size: 12.5px; color: #6b7280; padding: 12px 14px 8px;
}
.sheet-sub-hint { font-size: 12px; color: #6366f1; }
.sheet-stages { display: flex; flex-wrap: wrap; gap: 8px; padding: 0 12px 14px; }
.sheet-stage {
  display: inline-flex; align-items: center; gap: 4px;
  border: 1px solid #e6e8ee; background: #fff; color: #6b7280;
  border-radius: 999px; padding: 8px 14px; font-size: 13px; cursor: pointer;
  transition: all .15s ease;
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
}
.sheet-stage:hover { border-color: rgba(99,102,241,.4); color: #6366f1; }
.sheet-stage:active { background: rgba(99,102,241,.08); }
.sheet-stage.active {
  background: rgba(99,102,241,.1); border-color: rgba(99,102,241,.45);
  color: #4f46e5; font-weight: 600;
}
.sheet-cancel {
  width: 100%; min-height: 50px; padding: 12px;
  border: none; border-radius: 12px; background: #f7f8fa;
  font-size: 15px; font-weight: 500; color: #4b5563; cursor: pointer;
  touch-action: manipulation;
}
.sheet-cancel:hover, .sheet-cancel:active { background: rgba(15, 23, 42, .06); }

.sheet-enter-active, .sheet-leave-active { transition: opacity .2s ease; }
.sheet-enter-active .sheet, .sheet-leave-active .sheet {
  transition: transform .24s cubic-bezier(.4, 0, .2, 1);
}
.sheet-enter-from, .sheet-leave-to { opacity: 0; }
.sheet-enter-from .sheet, .sheet-leave-to .sheet { transform: translateY(100%); }
</style>