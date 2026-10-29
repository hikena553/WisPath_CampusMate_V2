<script setup lang="ts">
import type { BadgeTier } from '@/api/badge'

/**
 * 勋章本体（可复用纯展示组件）。
 * 造型参考游戏成就徽章：上层六边盾牌 + 金属包边 + 深色内芯 + 底部绶带，
 * 不用细圆环描边；尺寸全部由 size 推导，迷你勋章、勋章墙、放大查看三处共用同一外观。
 */
withDefaults(defineProps<{
  icon: string
  tier: BadgeTier
  earned?: boolean
  size?: number
  ribbon?: boolean
}>(), {
  earned: true,
  size: 52,
  ribbon: true,
})
</script>

<template>
  <span
    class="bm"
    :class="[`tier-${tier}`, { 'is-locked': !earned, 'no-ribbon': !ribbon, 'is-mini': size <= 30 }]"
    :style="{ '--bm-size': `${size}px` }"
  >
    <span class="bm-shield">
      <i class="bm-core" aria-hidden="true"></i>
      <i class="bm-emoji">{{ icon }}</i>
    </span>
    <i v-if="ribbon" class="bm-ribbon" aria-hidden="true">
      <b v-if="size >= 36">★</b><b v-if="size >= 36">★</b><b v-if="size >= 36">★</b>
    </i>
  </span>
</template>

<style scoped>
.bm {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: var(--bm-size);
  height: calc(var(--bm-size) * 1.22);
  flex: none;
}
/* 徽章外形：每个等级一种轮廓（六边盾 / 八边盾 / 徽冠 / 水晶），避免一眼全是同一个框 */
.bm-shield {
  position: relative;
  z-index: 1;
  width: var(--bm-size);
  height: calc(var(--bm-size) * 1.06);
  clip-path: var(--shape);
  background: var(--frame);
  filter:
    drop-shadow(0 calc(var(--bm-size) * 0.04) calc(var(--bm-size) * 0.055) rgba(17, 20, 24, 0.28))
    drop-shadow(0 0 calc(var(--bm-size) * 0.09) var(--glow));
  transition: transform 0.18s ease, filter 0.18s ease;
}
/* 金属表面加工纹：铜=斜拉丝、银=细直纹、金=顶部镀光、钻=切面棱光 */
.bm-shield::before {
  content: '';
  position: absolute;
  inset: 0;
  z-index: 1;
  background: var(--texture, none);
  mix-blend-mode: soft-light;
  opacity: 0.9;
  pointer-events: none;
}
/* 金属表面高光：左上受光 + 右下压暗，形成斜面质感 */
.bm-shield::after {
  content: '';
  position: absolute;
  inset: 0;
  z-index: 1;
  background:
    linear-gradient(148deg, rgba(255, 255, 255, 0.72) 0%, rgba(255, 255, 255, 0) 42%),
    linear-gradient(330deg, rgba(0, 0, 0, 0.22) 0%, rgba(0, 0, 0, 0) 46%);
  pointer-events: none;
}
/* 内芯：深色珐琅面，让徽记从金属边上跳出来 */
.bm-core {
  position: absolute;
  inset: var(--core-inset, calc(var(--bm-size) * 0.055));
  z-index: 0;
  clip-path: var(--shape);
  background:
    radial-gradient(78% 62% at 50% 44%, var(--core-glow) 0%, rgba(255, 255, 255, 0) 72%),
    radial-gradient(90% 70% at 50% 20%, var(--core-hi) 0%, rgba(255, 255, 255, 0) 60%),
    linear-gradient(165deg, var(--core-a) 0%, var(--core-b) 100%);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.14);
}
.bm-emoji {
  position: absolute;
  inset: 0 0 calc(var(--bm-size) * 0.05);
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: center;
  font-style: normal;
  font-size: max(9px, calc(var(--bm-size) * 0.42));
  line-height: 1;
  filter: drop-shadow(0 2px 3px rgba(0, 0, 0, 0.45));
}
/* 底部绶带：倒三角收口，压在盾牌下方，给勋章一个「颁发」的仪式感 */
.bm-ribbon {
  position: absolute;
  bottom: 0;
  left: 50%;
  z-index: 0;
  width: calc(var(--bm-size) * 0.64);
  height: calc(var(--bm-size) * 0.22);
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: calc(var(--bm-size) * 0.05);
  clip-path: polygon(0 0, 100% 0, 87% 100%, 50% 78%, 13% 100%);
  background: linear-gradient(160deg, var(--ribbon-a) 0%, var(--ribbon-b) 100%);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.4);
}
.bm-ribbon b {
  color: rgba(255, 255, 255, 0.92);
  font-size: calc(var(--bm-size) * 0.085);
  font-weight: 400;
  line-height: 1;
  text-shadow: 0 1px 1px rgba(0, 0, 0, 0.25);
}
.bm.no-ribbon { height: calc(var(--bm-size) * 1.06); }

/* 迷你尺寸（个人中心勋章条）：加厚金属包边、放大徽记。
   配色与内芯一律沿用同一套分级色，保证和勋章墙 / 放大层看到的是同一枚勋章，
   只是小尺寸下把更多面积让给金属边，避免缩成一颗看不清的深色块。 */
.bm.is-mini { --core-inset: 16%; }
.bm.is-mini .bm-emoji { font-size: calc(var(--bm-size) * 0.46); }

/* 未点亮：金属降为雾面银灰，内芯变浅，徽记去色但仍看得清轮廓 */
.bm.is-locked .bm-shield {
  background: linear-gradient(160deg, #f7f9fb 0%, #d5dce4 32%, #b4bec9 62%, #e6ebf0 82%, #9aa5b1 100%);
  filter: drop-shadow(0 calc(var(--bm-size) * 0.04) calc(var(--bm-size) * 0.05) rgba(17, 20, 24, 0.18));
}
.bm.is-locked .bm-core {
  background:
    radial-gradient(90% 70% at 50% 22%, rgba(255, 255, 255, 0.95) 0%, rgba(255, 255, 255, 0) 62%),
    linear-gradient(165deg, #f6f8fa 0%, #e2e7ed 100%);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.7);
}
.bm.is-locked .bm-ribbon { background: linear-gradient(160deg, #c9d0d9 0%, #a5aeb9 100%); }
.bm.is-locked .bm-ribbon b { color: rgba(255, 255, 255, 0.7); }
.bm.is-locked .bm-emoji { filter: grayscale(1) contrast(0.92); opacity: 0.45; }

/* 分级配色：不同轮廓 + 不同金属纹 + 深色珐琅内芯 + 同色辉光 */
.tier-bronze {
  --shape: polygon(50% 0%, 95% 14%, 95% 63%, 50% 100%, 5% 63%, 5% 14%);
  --frame: linear-gradient(160deg, #f6d6a8 0%, #d99a55 28%, #a86a31 56%, #eec89b 78%, #8a5424 100%);
  --texture: repeating-linear-gradient(135deg, rgba(255, 255, 255, 0.2) 0 2px, rgba(0, 0, 0, 0.14) 2px 4px);
  --glow: rgba(217, 154, 85, 0.34);
  --core-a: #33271c; --core-b: #15100c; --core-hi: rgba(236, 200, 155, 0.2); --core-glow: rgba(230, 160, 80, 0.34);
  --ribbon-a: #a06a37; --ribbon-b: #6a4320;
}
.tier-silver {
  --shape: polygon(22% 0%, 78% 0%, 100% 22%, 100% 60%, 50% 100%, 0% 60%, 0% 22%);
  --frame: linear-gradient(160deg, #ffffff 0%, #d3dde8 30%, #8e9cad 58%, #f0f5fa 78%, #6f7d8c 100%);
  --texture: repeating-linear-gradient(90deg, rgba(255, 255, 255, 0.24) 0 1px, rgba(0, 0, 0, 0.1) 1px 3px);
  --glow: rgba(160, 176, 192, 0.32);
  --core-a: #27303b; --core-b: #11161c; --core-hi: rgba(214, 228, 240, 0.2); --core-glow: rgba(196, 216, 236, 0.3);
  --ribbon-a: #8b98a6; --ribbon-b: #5b6675;
}
.tier-gold {
  --shape: polygon(50% 0%, 64% 8%, 84% 4%, 96% 34%, 96% 64%, 50% 100%, 4% 64%, 4% 34%, 16% 4%, 36% 8%);
  --frame: linear-gradient(160deg, #fff6d1 0%, #f7d261 30%, #c68f12 58%, #ffe9a6 78%, #9c6f0a 100%);
  --texture: radial-gradient(120% 80% at 50% 0%, rgba(255, 255, 255, 0.5) 0%, rgba(255, 255, 255, 0) 62%);
  --glow: rgba(247, 210, 97, 0.42);
  --core-a: #332b15; --core-b: #17120a; --core-hi: rgba(255, 233, 166, 0.24); --core-glow: rgba(255, 205, 80, 0.36);
  --ribbon-a: #b8851a; --ribbon-b: #78530a;
}
.tier-diamond {
  --shape: polygon(50% 0%, 86% 24%, 70% 84%, 50% 100%, 30% 84%, 14% 24%);
  --frame: linear-gradient(160deg, #f1feff 0%, #a5e8f7 30%, #4599bd 58%, #dbf6ff 78%, #2f7395 100%);
  --texture: conic-gradient(from 0deg at 50% 50%, rgba(255, 255, 255, 0.35) 0 12%, rgba(0, 0, 0, 0.14) 12% 25%, rgba(255, 255, 255, 0.3) 25% 37%, rgba(0, 0, 0, 0.15) 37% 50%, rgba(255, 255, 255, 0.35) 50% 62%, rgba(0, 0, 0, 0.14) 62% 75%, rgba(255, 255, 255, 0.3) 75% 87%, rgba(0, 0, 0, 0.15) 87% 100%);
  --glow: rgba(117, 205, 235, 0.45);
  --core-a: #163039; --core-b: #081419; --core-hi: rgba(198, 240, 250, 0.24); --core-glow: rgba(110, 220, 255, 0.34);
  --ribbon-a: #3f8ba8; --ribbon-b: #235669;
}
</style>
