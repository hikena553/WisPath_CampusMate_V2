<template>
  <div class="campus-showcase">
    <h2 class="section-title">校园风采</h2>
    <el-skeleton :loading="loading" animated :count="3">
      <el-row :gutter="24">
        <el-col v-for="item in figures" :key="item.id" :xs="24" :sm="12" :md="8">
          <el-card class="figure-card" shadow="hover">
            <div class="figure-avatar">
              <el-avatar :size="72" :src="item.avatar">{{ item.name[0] }}</el-avatar>
            </div>
            <h3>{{ item.name }}</h3>
            <p class="figure-title">{{ item.title }}</p>
            <p class="figure-desc">{{ item.description }}</p>
          </el-card>
        </el-col>
      </el-row>
      <el-empty v-if="!loading && figures.length === 0" description="暂无数据" />
    </el-skeleton>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getFigures } from '@/api/campus'
import type { CampusFigure } from '@/types'

const figures = ref<CampusFigure[]>([])
const loading = ref(true)

onMounted(async () => {
  try {
    figures.value = await getFigures()
  } catch {
    figures.value = []
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.campus-showcase { padding: 40px 0; max-width: 1100px; margin: 0 auto; }
.section-title { font-size: 28px; color: #333; margin-bottom: 24px; text-align: center; }
.figure-card { text-align: center; margin-bottom: 24px; }
.figure-avatar { margin: 16px 0; }
.figure-card h3 { font-size: 18px; color: #333; margin-bottom: 6px; }
.figure-title { color: #409eff; font-size: 14px; margin-bottom: 10px; }
.figure-desc { color: #666; font-size: 13px; line-height: 1.6; text-align: left; }
</style>
