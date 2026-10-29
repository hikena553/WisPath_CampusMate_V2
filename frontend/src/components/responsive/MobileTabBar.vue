<template>
  <!-- 外层只负责「固定 + 居中 + 限宽」；白色底托放在胶囊**前面**（同层靠前的兄弟），
       这样胶囊的投影会画在底托之上，胶囊轮廓仍然是完整的，不会和底托糊成一块 -->
  <div class="dock-wrap">
    <div class="dock-base" aria-hidden="true" />
    <div class="mobile-tab-bar">
      <div
        v-for="item in items"
        :key="item.key"
        :class="['tab-item', { active: activeKey === item.key, center: item.center }]"
        @click="$emit('select', item)"
      >
        <div class="tab-icon-wrap">
          <template v-if="item.iconImg">
            <img :src="item.iconImg" class="tab-icon-img" />
          </template>
          <template v-else>
            <el-icon :size="item.center ? 22 : 20"><component :is="item.icon" /></el-icon>
          </template>
          <span v-if="item.badge && unreadCount" class="tab-badge">{{ unreadCount > 99 ? '99+' : unreadCount }}</span>
        </div>
        <span class="tab-label">{{ item.label }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Component } from 'vue'

interface TabItem {
  key: string
  label: string
  icon?: Component
  iconImg?: string
  route: string
  center?: boolean
  badge?: boolean
}

defineProps<{
  items: TabItem[]
  activeKey: string
  unreadCount?: number
}>()

defineEmits<{
  select: [item: TabItem]
}>()
</script>

<style scoped>
/* ================= 悬浮胶囊导航 =================
   形态：一枚**纯白实底**的悬浮胶囊，下半身融进一条**实心白底托**（参考「千问办公」那种底部栏）：
   - 左右各留 14px 内缩、底部留 12px（叠加 safe-area），四周都是页面留白；
   - 圆角取 999px（半高以上即正圆弧端），因此是「胶囊」而不是圆角矩形；
   - 底色是实白 #fff，不做半透明毛玻璃：内容滚过时被完全挡住；
   - 底托（.dock-base）从**胶囊的正中高度**起铺到屏幕底部：胶囊下半身直接没入底托，
     往下整块都是不透明的白，页面卡片/图片不会再从胶囊底下、两侧露出来；
   - 轮廓外挂一圈**白色辉光**（box-shadow 白色外发光）：压在深色图片/彩色卡片上时，
     边缘会晕开一层白光，和参考图那种「白面板浮在蓝色背景上」的观感一致；
   - 选中态是胶囊内部的浅灰小胶囊（#f0f1f4），白底上对比刚好、不抢眼；
   - 内容可以滚到胶囊下方（见 composables/useDockInset.ts）。
   注意：胶囊不吃 .safe-area-bottom（全局那条规则会加 padding-bottom，
   把 62px 的内容区撑高、胶囊变成歪的），安全区改由 bottom 的 calc 承担。 */
.dock-wrap {
  position: fixed;
  left: 50%;
  /* 居中用 translate，避免 left/right 同时写死时无法内缩 */
  transform: translateX(-50%);
  bottom: calc(12px + env(safe-area-inset-bottom, 0px));
  width: calc(100% - 28px);
  /* 手机容器宽 440px 时的内缩上限，宽屏预览下与手机容器左右留白对齐 */
  max-width: 412px;
  z-index: 1000;
}

/* 白色底托：从胶囊的**一半高度**（top: 50%）一直铺到屏幕底部（含安全区），
   宽度铺满手机容器。胶囊下半身与它同色，直接融成一块，所以「半高以下是实心白」。
   放在胶囊前面当兄弟节点，胶囊的投影/辉光才能压在它上面（父子关系会被父级背景层盖掉）。 */
.dock-base {
  position: absolute;
  top: 50%;
  /* 用 bottom 拉伸而不是写死 height：底边要贴住屏幕底部，多出来的 1px 补胶囊描边 */
  bottom: calc(-13px - env(safe-area-inset-bottom, 0px));
  left: 50%;
  transform: translateX(-50%);
  /* 比胶囊宽：把胶囊两侧那两条缝也一起盖住，否则卡片边缘会从旁边露出来 */
  width: 100vw;
  max-width: 440px;
  background: var(--tab-bar-bg, #ffffff);
  /* 顶边那圈白色辉光：在深色内容上会晕开一层白光 */
  box-shadow:
    0 0 18px rgba(255, 255, 255, 0.85),
    0 0 42px rgba(255, 255, 255, 0.5);
  pointer-events: none;
}

.mobile-tab-bar {
  position: relative;
  width: 100%;
  height: 62px;
  padding: 0 8px;
  box-sizing: border-box;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-radius: 999px;
  /* 纯白实底：不透明，滚动内容经过时被完全挡住，观感干净、图标文字也不受背景干扰 */
  background: var(--tab-bar-bg, #ffffff);
  /* 描边只留一丝：胶囊下半身已没入底托，这里只是给「圆拱顶」在纯白页面上兜一点边 */
  border: 1px solid var(--tab-bar-border, rgba(15, 23, 42, 0.03));
  /* 只留白色辉光，不要深色投影：深投影会落在下面的白底托上，变成一条脏灰带 */
  box-shadow:
    0 0 16px rgba(255, 255, 255, 0.9),
    0 0 38px rgba(255, 255, 255, 0.55);
}

.tab-item {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 3px;
  flex: 1;
  height: 46px;
  border-radius: 999px;
  cursor: pointer;
  /* 纯白底上未选中态用中深灰（比纯黑柔和、比浅灰有分量），
     文字与图标同时靠颜色区分选中/未选中 */
  color: var(--tab-idle-color, #4b5158);
  -webkit-tap-highlight-color: transparent;
  /* 切换时颜色需要过渡，否则选中/取消选中会「瞬切」，与胶囊托的弹性动画不同步 */
  transition: color 0.22s ease;
}

/* 选中态底托：一枚贴在胶囊内部的浅灰小胶囊（不是放大图标，避免点击后「弹一下变大」）。
   纯白胶囊上，一块 #f0f1f4 的灰底就足够把选中项托出来，也不必再加投影 */
.tab-item::before {
  content: '';
  position: absolute;
  inset: 3px 4px;
  border-radius: 999px;
  background: var(--tab-active-chip, #f0f1f4);
  opacity: 0;
  transform: scale(0.84);
  transition:
    opacity 0.2s ease,
    transform 0.28s cubic-bezier(0.34, 1.45, 0.64, 1);
}

.tab-item.active::before {
  opacity: 1;
  transform: scale(1);
}

/* 图标与文字必须压在底托之上 */
.tab-item > * {
  position: relative;
  z-index: 1;
}

.tab-item.active {
  /* 用变量承接：学生端驾驶舱 v2 把选中色改成近黑（见 StudentLayout 的 --tab-active），
     其它端不覆盖变量，保持原品牌蓝，行为不变 */
  color: var(--tab-active-color, #409eff);
}

.tab-item:active {
  transform: scale(0.95);
  transition: transform 0.12s ease-out;
}

/* 中间标签：胶囊内的白色 logo 圆托（主入口强调，不显示文字）
   旧版是「凸出底栏上沿」的圆托 + 4px 白色描边，那是为通栏设计的；
   换成悬浮胶囊后圆托再凸出就会顶破胶囊轮廓，因此改成内嵌圆托：
   直径 40px、描边 1px、靠投影浮起，选中时只加强光环不做缩放。 */
.tab-item.center {
  position: relative;
}

.tab-item.center::before {
  display: none;
}

.tab-item.center .tab-icon-wrap {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--tab-center-bg, radial-gradient(circle at 32% 26%, #ffffff 0%, #eff6ff 58%, #dbeafe 100%));
  box-shadow:
    0 0 0 1px var(--tab-center-ring, rgba(64, 158, 255, 0.22)),
    0 4px 10px rgba(15, 23, 42, 0.1),
    0 2px 6px var(--tab-center-glow, rgba(64, 158, 255, 0.24));
  transition: box-shadow 0.26s ease;
}

.tab-item.center .tab-icon-img {
  width: 80%;
  height: 80%;
  border-radius: 0;
  margin-top: 0;
}

.tab-item.center .tab-label {
  display: none;
}

/* 选中态：只加强光环与投影 */
.tab-item.center.active .tab-icon-wrap {
  box-shadow:
    0 0 0 2px var(--tab-center-ring, rgba(64, 158, 255, 0.22)),
    0 6px 14px var(--tab-center-glow-strong, rgba(64, 158, 255, 0.34));
}

.tab-label {
  font-size: 10px;
  font-weight: 500;
  line-height: 1;
  letter-spacing: 0.2px;
  white-space: nowrap;
}

.tab-icon-img {
  width: 22px;
  height: 22px;
  object-fit: contain;
}

.tab-icon-wrap {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

.tab-badge {
  position: absolute;
  top: -4px;
  right: -10px;
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  border-radius: 8px;
  background: #f56c6c;
  color: #fff;
  font-size: 10px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
}
</style>
