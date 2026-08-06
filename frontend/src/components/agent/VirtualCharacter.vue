<template>
  <div class="character" :class="state">
    <div class="halo"></div>
    <div class="char-body">
      <div class="char-img-wrap">
        <img src="/images/06.png" alt="绵小城" class="char-img" />
      </div>
      <div class="arm left"><div class="hand"></div></div>
      <div class="arm right"><div class="hand"></div></div>
    </div>
    <div class="particles">
      <div class="dot d1"></div><div class="dot d2"></div><div class="dot d3"></div>
      <div class="dot d4"></div><div class="dot d5"></div>
    </div>
    <div class="name-tag">绵小城</div>
  </div>
</template>

<script setup lang="ts">
defineProps<{ state?: 'idle' | 'thinking' | 'speaking' }>()
</script>

<style scoped>
.character {
  position: relative;
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  user-select: none;
}

.halo {
  position: absolute;
  width: 180px;
  height: 180px;
  top: -20px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(64,158,255,0.15) 0%, rgba(64,158,255,0.06) 40%, transparent 70%);
  animation: halo-pulse 2s ease-in-out infinite;
}
@keyframes halo-pulse {
  0%, 100% { transform: scale(1); opacity: 0.6; }
  50% { transform: scale(1.12); opacity: 1; }
}

.char-body {
  position: relative;
  width: 140px;
  height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.char-img-wrap {
  width: 130px;
  height: 190px;
  border-radius: 20px;
  overflow: hidden;
  z-index: 2;
  animation: h-float 2s ease-in-out infinite;
  filter: drop-shadow(0 6px 24px rgba(64,158,255,0.35));
}
.char-img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}
.character.thinking .char-img-wrap { animation: h-think 0.5s ease-in-out infinite; }
.character.speaking .char-img-wrap { animation: h-speak 0.2s ease-in-out infinite alternate; }

@keyframes h-float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-8px); }
}
@keyframes h-think {
  0%, 100% { transform: translateY(0) rotate(-3deg); }
  50% { transform: translateY(-10px) rotate(3deg); }
}
@keyframes h-speak {
  0% { transform: translateY(-2px) scale(1.02); }
  100% { transform: translateY(2px) scale(0.98); }
}

.arm {
  position: absolute;
  top: 80px;
  width: 12px;
  height: 30px;
  background: linear-gradient(180deg, #5cabff, #3a7bc8);
  border-radius: 8px;
  z-index: 1;
}
.arm.left { left: 0; transform-origin: top center; animation: arm-wave-l 2s ease-in-out infinite; }
.arm.right { right: 0; transform-origin: top center; animation: arm-wave-r 2s ease-in-out infinite; }
.hand {
  position: absolute;
  bottom: -4px;
  left: 50%;
  transform: translateX(-50%);
  width: 14px;
  height: 14px;
  background: radial-gradient(circle at 40% 40%, #ffd5c0, #f0b89a);
  border-radius: 50%;
}
.character.thinking .arm.left { animation: arm-think-l 0.5s ease-in-out infinite; }
.character.thinking .arm.right { animation: arm-think-r 0.5s ease-in-out infinite; }
.character.speaking .arm.left { animation: arm-speak 0.2s ease-in-out infinite alternate; }
.character.speaking .arm.right { animation: arm-speak 0.2s ease-in-out infinite alternate-reverse; }

@keyframes arm-wave-l { 0%, 100% { transform: rotate(12deg); } 50% { transform: rotate(22deg); } }
@keyframes arm-wave-r { 0%, 100% { transform: rotate(-12deg); } 50% { transform: rotate(-22deg); } }
@keyframes arm-think-l { 0%, 100% { transform: rotate(8deg); } 50% { transform: rotate(32deg); } }
@keyframes arm-think-r { 0%, 100% { transform: rotate(-8deg); } 50% { transform: rotate(-32deg); } }
@keyframes arm-speak { 0% { transform: rotate(8deg); } 100% { transform: rotate(18deg); } }

.particles { position: absolute; width: 100%; height: 100%; top: 0; left: 0; pointer-events: none; }
.dot {
  position: absolute;
  width: 5px;
  height: 5px;
  background: rgba(64, 158, 255, 0.4);
  border-radius: 50%;
  animation: particle 4s ease-in-out infinite;
}
.d1 { top: -10px; left: 20px; animation-delay: 0s; }
.d2 { top: 10px; right: 12px; animation-delay: 0.8s; }
.d3 { top: 40px; left: 0; animation-delay: 1.6s; }
.d4 { top: 90px; right: 4px; animation-delay: 2.4s; }
.d5 { top: 130px; left: 10px; animation-delay: 3.2s; }
@keyframes particle {
  0%, 100% { opacity: 0; transform: scale(0.5) translateY(0); }
  50% { opacity: 1; transform: scale(1.2) translateY(-12px); }
}

.name-tag {
  margin-top: 4px;
  font-size: 13px;
  color: #409eff;
  font-weight: 600;
  letter-spacing: 2px;
  text-shadow: 0 1px 4px rgba(64,158,255,0.2);
}
</style>
