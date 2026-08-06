<template>
  <div :class="['mc', { mini }]" @click="$emit('click')">
    <div v-if="bubble && !mini" class="mc-bubble"><span>{{ bubble }}</span></div>

    <div class="mc-scene" :class="[`s-${state}`]">
      <div v-if="!mini" class="mc-glow"></div>

      <div v-if="!mini" class="mc-particles">
        <i v-for="n in 10" :key="n" :class="['mc-p', `p${n}`]"></i>
      </div>

      <div class="mc-core">
        <img src="/images/mascot.png" alt="绵小城" class="mc-img" draggable="false" />
        <div v-if="state === 'thinking'" class="mc-thought">
          <span></span><span></span><span></span>
        </div>
      </div>

      <div v-if="!mini" class="mc-shadow"></div>
    </div>

  </div>
</template>

<script setup lang="ts">
defineProps<{ state?: 'idle' | 'thinking' | 'speaking'; bubble?: string; mini?: boolean }>()
defineEmits<{ click: [] }>()
</script>

<style scoped>
.mc {
  display: inline-flex; flex-direction: column; align-items: center;
  cursor: pointer; position: relative; user-select: none;
  animation: bounceIn 0.35s ease-out;
}

@keyframes bounceIn {
  0% { opacity: 0; transform: scale(0.3); }
  50% { opacity: 1; transform: scale(1.05); }
  70% { transform: scale(0.9); }
  100% { transform: scale(1); }
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slideInUp {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

.mc-bubble {
  position: absolute; top: 0; left: 50%; transform: translateX(-50%) translateY(-100%);
  background: rgba(255,255,255,.95); backdrop-filter: blur(12px);
  border: 1px solid rgba(99,102,241,.15); border-radius: 12px;
  padding: 6px 14px; font-size: 12px; color: #444; white-space: nowrap;
  box-shadow: 0 4px 20px rgba(99,102,241,.1);
  animation: slideInUp 0.4s ease-out;
}
.mc-bubble::after {
  content: ''; position: absolute; bottom: -5px; left: 50%; transform: translateX(-50%) rotate(45deg);
  width: 10px; height: 10px; background: rgba(255,255,255,.95);
  border-right: 1px solid rgba(99,102,241,.15); border-bottom: 1px solid rgba(99,102,241,.15);
}

.mc-scene {
  position: relative; width: 140px; height: 160px;
  display: flex; align-items: center; justify-content: center;
  animation: float 2s ease-in-out infinite;
}

@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-8px); }
}

.mc.mini .mc-scene { 
  width: 40px; height: 40px;
  animation: none;
}

.mc-glow {
  position: absolute; width: 100px; height: 100px; border-radius: 50%;
  background: radial-gradient(circle, rgba(99,102,241,.12) 0%, transparent 70%);
  animation: glow-pulse 2s ease-in-out infinite;
}

.mc-particles { position: absolute; inset: 0; pointer-events: none; }
.mc-p {
  position: absolute; border-radius: 50%;
  background: radial-gradient(circle, var(--pc, #818cf8) 0%, transparent 70%);
  opacity: 0; animation: p-rise var(--pd, 4s) var(--delay, 0s) ease-in-out infinite;
}
.p1{--pc:#818cf8;--pd:3.5s;--delay:0s;width:5px;height:5px;left:12%;bottom:25%}
.p2{--pc:#a78bfa;--pd:4s;--delay:.4s;width:4px;height:4px;left:80%;bottom:35%}
.p3{--pc:#c4b5fd;--pd:3.8s;--delay:.8s;width:4px;height:4px;left:20%;bottom:65%}
.p4{--pc:#818cf8;--pd:4.2s;--delay:1.2s;width:3px;height:3px;left:85%;bottom:55%}
.p5{--pc:#6366f1;--pd:3.6s;--delay:1.6s;width:4px;height:4px;left:8%;bottom:50%}
.p6{--pc:#a78bfa;--pd:4.5s;--delay:2s;width:3px;height:3px;left:70%;bottom:18%}
.p7{--pc:#c4b5fd;--pd:3.9s;--delay:2.4s;width:3px;height:3px;left:40%;bottom:72%}
.p8{--pc:#818cf8;--pd:4.1s;--delay:.2s;width:4px;height:4px;left:88%;bottom:68%}
.p9{--pc:#6366f1;--pd:3.7s;--delay:1s;width:3px;height:3px;left:30%;bottom:20%}
.p10{--pc:#a78bfa;--pd:4.3s;--delay:1.8s;width:3px;height:3px;left:60%;bottom:58%}

.mc-core {
  position: relative; z-index: 2;
  transition: transform 0.15s ease;
}
.mc.mini .mc-core { }

.mc-img {
  width: 120px; height: 120px; object-fit: contain;
  pointer-events: none; user-select: none;
  transition: transform 0.15s ease;
}
.mc.mini .mc-img { width: 36px; height: 36px; }

.mc-thought {
  position: absolute; top: -4px; right: -12px;
  display: flex; gap: 3px; align-items: flex-end;
}
.mc-thought span {
  width: 5px; height: 5px; border-radius: 50%; background: #818cf8;
  animation: thought-bounce 1.2s ease-in-out infinite;
}
.mc-thought span:nth-child(2) { width: 6px; height: 6px; animation-delay: .15s; }
.mc-thought span:nth-child(3) { width: 7px; height: 7px; animation-delay: .3s; }

.mc-shadow {
  position: absolute; bottom: 8px; left: 50%; transform: translateX(-50%);
  width: 50px; height: 6px; border-radius: 50%;
  background: radial-gradient(ellipse, rgba(99,102,241,.1) 0%, transparent 70%);
  animation: shadow-pulse 2s ease-in-out infinite;
}

@keyframes core-float {
  0%,100% { transform: translateY(0); }
  50% { transform: translateY(-6px); }
}
@keyframes glow-pulse {
  0%,100% { opacity: .6; transform: scale(1); }
  50% { opacity: 1; transform: scale(1.1); }
}
@keyframes shadow-pulse {
  0%,100% { opacity: .6; transform: translateX(-50%) scaleX(1); }
  50% { opacity: .3; transform: translateX(-50%) scaleX(.85); }
}
@keyframes thought-bounce {
  0%,80%,100% { transform: translateY(0); opacity: .4; }
  40% { transform: translateY(-6px); opacity: 1; }
}
@keyframes p-rise {
  0% { transform: translateY(0) scale(0); opacity: 0; }
  20% { opacity: .5; transform: scale(1); }
  80% { opacity: .2; }
  100% { transform: translateY(-70px) scale(.3); opacity: 0; }
}

.s-speaking .mc-core { 
  animation: speak-bounce 0.2s ease-in-out infinite alternate;
}

@keyframes speak-bounce {
  0% { transform: translateY(0); }
  100% { transform: translateY(-3px); }
}

.s-thinking .mc-core { 
  animation: think-wobble 0.5s ease-in-out infinite;
}

@keyframes think-wobble {
  0%, 100% { transform: rotate(0); }
  25% { transform: rotate(-3deg); }
  75% { transform: rotate(3deg); }
}

@keyframes core-wobble {
  0%,100% { transform: rotate(0) translateY(0); }
  25% { transform: rotate(-2deg) translateY(-2px); }
  75% { transform: rotate(2deg) translateY(-2px); }
}
</style>
