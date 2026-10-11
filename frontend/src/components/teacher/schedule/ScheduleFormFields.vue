<template>
  <!-- 添加日程表单字段：桌面端弹窗与移动端子页共用同一套字段与样式，
       避免两端各写一份导致观感与交互再次分叉。 -->
  <div class="sf">
    <div class="sf-field">
      <label class="sf-label">日期</label>
      <el-date-picker
        :model-value="date"
        type="date"
        format="YYYY年MM月DD日"
        value-format="YYYY-MM-DD"
        placeholder="选择日期"
        :clearable="false"
        style="width:100%"
        @update:model-value="emit('update:date', String($event))"
      />
    </div>

    <div class="sf-field">
      <label class="sf-label">日程内容</label>
      <el-input
        :model-value="content"
        type="textarea"
        :rows="3"
        resize="none"
        placeholder="写点什么，例如：期中考试监考 / 班级例会 / 与某位同学谈话"
        @update:model-value="emit('update:content', $event)"
      />
      <div class="sf-templates">
        <span class="sf-templates-label">常用</span>
        <button
          v-for="t in templates"
          :key="t"
          class="sf-template"
          type="button"
          @click="applyTemplate(t)"
        >{{ t }}</button>
      </div>
    </div>

    <div class="sf-field">
      <label class="sf-label">紧急程度</label>
      <div class="sf-urgency">
        <button
          v-for="u in urgencyOptions"
          :key="u.value"
          class="sf-urgency-opt"
          :class="[`is-${u.value}`, { active: urgency === u.value }]"
          type="button"
          @click="emit('update:urgency', u.value)"
        >{{ u.label }}</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { ScheduleUrgency } from '@/api/teacher'

const props = withDefaults(defineProps<{
  date: string
  content: string
  urgency: ScheduleUrgency
  urgencyOptions?: { value: ScheduleUrgency; label: string }[]
}>(), {
  urgencyOptions: () => [
    { value: 'normal', label: '普通' },
    { value: 'important', label: '重要' },
    { value: 'urgent', label: '紧急' },
  ],
})

const emit = defineEmits<{
  'update:date': [value: string]
  'update:content': [value: string]
  'update:urgency': [value: ScheduleUrgency]
}>()

/** 高频事项一键填入，省去每次从头敲字 */
const templates = ['期中考试监考', '班级例会', '学生谈心谈话', '家长沟通', '听课评课']

function applyTemplate(text: string) {
  const current = props.content.trim()
  if (current.includes(text)) return
  emit('update:content', current ? `${current}\n${text}` : text)
}
</script>

<style scoped>
.sf {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.sf-field {
  display: flex;
  flex-direction: column;
}
.sf-label {
  margin-bottom: 8px;
  font-size: 13px;
  font-weight: 600;
  color: #344054;
}

.sf-templates {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}
.sf-templates-label {
  font-size: 11.5px;
  color: #98a2b3;
}
.sf-template {
  padding: 3px 10px;
  border: 1px solid #e4e7ec;
  border-radius: 999px;
  background: #fff;
  color: #475467;
  font-family: inherit;
  font-size: 11.5px;
  line-height: 1.5;
  cursor: pointer;
}
.sf-template:hover { border-color: #cfdcf3; color: #1d4ed8; background: #f8fafc; }

.sf-urgency {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}
.sf-urgency-opt {
  height: 38px;
  border: 1px solid #e4e7ec;
  border-radius: 10px;
  background: #fff;
  color: #475467;
  font-family: inherit;
  font-size: 13px;
  cursor: pointer;
}
.sf-urgency-opt:hover { border-color: #cfdcf3; }
.sf-urgency-opt.active {
  border-color: #2563eb;
  background: #eff4ff;
  color: #1d4ed8;
  font-weight: 600;
}
.sf-urgency-opt.is-important.active {
  border-color: #f59e0b;
  background: #fffaeb;
  color: #b54708;
}
.sf-urgency-opt.is-urgent.active {
  border-color: #d92d20;
  background: #fef3f2;
  color: #d92d20;
}

/* 输入控件的发丝边与聚焦描边，和教师端其余表单保持一致 */
.sf :deep(.el-input__wrapper) {
  border-radius: 10px;
  box-shadow: 0 0 0 1px #e4e7ec inset;
}
.sf :deep(.el-input__wrapper:hover) { box-shadow: 0 0 0 1px #cfdcf3 inset; }
.sf :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px #2563eb inset, 0 0 0 3px rgba(37, 99, 235, 0.1);
}
.sf :deep(.el-textarea__inner) {
  border-radius: 10px;
  box-shadow: 0 0 0 1px #e4e7ec inset;
  font-size: 14px;
  line-height: 1.6;
  padding: 10px 12px;
}
.sf :deep(.el-textarea__inner:hover) { box-shadow: 0 0 0 1px #cfdcf3 inset; }
.sf :deep(.el-textarea__inner:focus) {
  box-shadow: 0 0 0 1px #2563eb inset, 0 0 0 3px rgba(37, 99, 235, 0.1);
}
</style>