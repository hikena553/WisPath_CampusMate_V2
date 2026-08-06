<template>
  <div class="home-page">
    <header class="top-header">
      <div class="header-inner">
        <div class="logo">智慧校园AI服务平台</div>
        <div class="header-right">
          <el-dropdown @command="handleLogin">
            <el-button type="primary" plain>
              登录
              <el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="student">学生端</el-dropdown-item>
                <el-dropdown-item command="teacher">教师端</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </div>
    </header>

    <section class="hero">
      <div class="hero-content">
        <h1>绵阳城市学院</h1>
        <p>智慧校园AI服务平台 · 绵小城</p>
      </div>
    </section>

    <div class="container">
      <CampusVR />
      <Announcements />
      <CampusShowcase />
    </div>

    <footer class="footer">
      <p>绵阳城市学院 · 智慧校园AI服务平台</p>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { ArrowDown } from '@element-plus/icons-vue'
import CampusVR from '@/components/home/CampusVR.vue'
import Announcements from '@/components/home/Announcements.vue'
import CampusShowcase from '@/components/home/CampusShowcase.vue'

const router = useRouter()

function handleLogin(role: string) {
  router.push(`/login?role=${role}`)
}
</script>

<style scoped>
.home-page { min-height: 100vh; background: #fff; }
.top-header { position: sticky; top: 0; z-index: 100; background: #fff; border-bottom: 1px solid #eee; }
.header-inner { max-width: 1200px; margin: 0 auto; padding: 0 24px; height: 64px; display: flex; justify-content: space-between; align-items: center; }
.logo { font-size: 20px; font-weight: bold; color: #409eff; }
.header-right { display: flex; align-items: center; gap: 12px; }
.hero { background: linear-gradient(135deg, #409eff 0%, #1a6eff 100%); color: #fff; padding: 80px 24px; text-align: center; }
.hero h1 { font-size: 42px; margin-bottom: 12px; }
.hero p { font-size: 18px; opacity: 0.9; }
.container { max-width: 1200px; margin: 0 auto; padding: 0 24px; }
.footer { text-align: center; padding: 40px 24px; color: #999; font-size: 14px; border-top: 1px solid #eee; margin-top: 40px; }
</style>
