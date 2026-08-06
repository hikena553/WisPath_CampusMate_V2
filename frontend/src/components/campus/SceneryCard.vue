<template>
  <el-card :body-style="{ padding: '0' }" shadow="hover">
    <el-image :src="scenery.image_url" style="width:100%;height:200px" fit="cover" />
    <div style="padding:14px">
      <h3>{{ scenery.title }}</h3>
      <p style="color:#999">{{ scenery.location }}</p>
      <p>{{ scenery.description }}</p>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import type { CampusScenery } from '@/types'
defineProps<{ scenery: CampusScenery }>()
</script>
