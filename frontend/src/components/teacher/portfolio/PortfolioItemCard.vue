<template>
  <div class="pf-card">
    <div class="pf-card-head">
      <span class="pf-badge" :style="{ color: color, background: tint }">
        {{ PORTFOLIO_TYPE_LABEL[item.item_type] }}
      </span>
      <span v-if="item.occurred_on" class="pf-date">{{ item.occurred_on }}</span>
      <el-tag v-if="item.visibility === 'public'" size="small" type="success" effect="plain" round>
        公开展示
      </el-tag>
      <el-tag v-else size="small" type="info" effect="plain" round>仅自己</el-tag>
    </div>

    <div class="pf-title">{{ item.title }}</div>

    <div v-if="item.reflection" class="pf-reflection">
      <el-icon :size="12" class="pf-quote"><ChatLineSquare /></el-icon>
      <span>{{ item.reflection }}</span>
    </div>

    <div v-if="item.evidence.length" class="pf-evidence-list">
      <a
        v-for="(e, i) in item.evidence"
        :key="i"
        class="pf-ev"
        :href="e.url"
        target="_blank"
        rel="noopener noreferrer"
      >
        <el-icon :size="13"><Paperclip /></el-icon>
        {{ e.name || e.url }}
      </a>
    </div>

    <div v-if="item.review_comment" class="pf-review">
      <span class="pf-review-lb">评价</span>{{ item.review_comment }}
    </div>

    <div class="pf-actions">
      <button class="pf-link" @click="emit('edit', item)">编辑</button>
      <button class="pf-link pf-link-danger" @click="emit('delete', item)">删除</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { ChatLineSquare, Paperclip } from '@element-plus/icons-vue'
import {
  PORTFOLIO_TYPE_COLOR,
  PORTFOLIO_TYPE_LABEL,
  type PortfolioItem,
} from '@/api/teacherPortfolio'

const props = defineProps<{ item: PortfolioItem }>()
const emit = defineEmits<{ edit: [item: PortfolioItem]; delete: [item: PortfolioItem] }>()

const color = computed(() => PORTFOLIO_TYPE_COLOR[props.item.item_type])
const tint = computed(() => `${PORTFOLIO_TYPE_COLOR[props.item.item_type]}14`)
</script>

<style scoped>
.pf-card {
  background: #fff;
  border: 1px solid #f0f1f3;
  border-radius: 12px;
  padding: 13px 15px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.pf-card-head {
  display: flex;
  align-items: center;
  gap: 8px;
}
.pf-badge {
  font-size: 11.5px;
  font-weight: 600;
  padding: 2px 9px;
  border-radius: 999px;
}
.pf-date {
  font-size: 11.5px;
  color: #98a2b3;
}
.pf-card-head .el-tag { margin-left: auto; }

.pf-title {
  font-size: 14px;
  font-weight: 600;
  color: #101828;
  line-height: 1.5;
}

.pf-reflection {
  display: flex;
  gap: 6px;
  font-size: 12.5px;
  color: #475467;
  line-height: 1.6;
  background: #fcfcfd;
  border-left: 2px solid #eaecf0;
  padding: 6px 10px;
  border-radius: 0 8px 8px 0;
}
.pf-quote {
  color: #98a2b3;
  flex-shrink: 0;
  margin-top: 3px;
}

.pf-evidence-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.pf-ev {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #2563eb;
  text-decoration: none;
  background: #eff4ff;
  padding: 3px 9px;
  border-radius: 999px;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.pf-ev:hover { text-decoration: underline; }

.pf-review {
  font-size: 12.5px;
  color: #6941c6;
  background: #f4f3ff;
  border-radius: 8px;
  padding: 7px 10px;
}
.pf-review-lb {
  font-weight: 600;
  margin-right: 6px;
}

.pf-actions {
  display: flex;
  gap: 14px;
  margin-top: 2px;
}
.pf-link {
  border: none;
  background: none;
  padding: 0;
  font-size: 12px;
  color: #2563eb;
  cursor: pointer;
  font-family: inherit;
}
.pf-link-danger { color: #d92d20; }
</style>