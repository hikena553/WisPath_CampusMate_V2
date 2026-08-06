<template>
  <div class="announcements">
    <h2 class="section-title">教务处通知公告</h2>
    <el-skeleton :loading="loading" animated :count="5">
      <div class="announcement-list">
        <a v-for="(item, idx) in list" :key="idx" :href="item.url || '#'" target="_blank" class="announcement-item">
          <span class="announcement-title">{{ item.title }}</span>
          <span v-if="item.date" class="announcement-date">{{ item.date }}</span>
        </a>
      </div>
      <el-empty v-if="!loading && list.length === 0" description="暂无通知" />
    </el-skeleton>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getAnnouncements } from '@/api/campus'
import type { Announcement } from '@/types'

const list = ref<Announcement[]>([])
const loading = ref(true)

onMounted(async () => {
  try {
    list.value = await getAnnouncements()
  } catch {
    list.value = []
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.announcements { padding: 40px 0; max-width: 900px; margin: 0 auto; }
.section-title { font-size: 28px; color: #333; margin-bottom: 24px; text-align: center; }
.announcement-list { display: flex; flex-direction: column; gap: 12px; }
.announcement-item { display: flex; justify-content: space-between; align-items: center; padding: 14px 20px; background: #f8f9fa; border-radius: 8px; text-decoration: none; transition: background 0.2s; }
.announcement-item:hover { background: #e8f0fe; }
.announcement-title { color: #333; font-size: 15px; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; margin-right: 16px; }
.announcement-date { color: #999; font-size: 13px; white-space: nowrap; }
</style>
