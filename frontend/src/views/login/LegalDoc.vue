<template>
  <Teleport to="body">
    <div class="legal-layer">
      <header class="legal-bar">
        <button type="button" class="legal-back" @click="$emit('close')">
          <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M15 5l-7 7 7 7" />
          </svg>
          <span>返回</span>
        </button>
        <span class="legal-title">{{ doc.title }}</span>
        <span class="legal-placeholder"></span>
      </header>

      <div class="legal-body">
        <p class="legal-meta">更新日期：2026 年 10 月</p>
        <h1>{{ doc.title }}</h1>
        <p class="legal-intro">{{ doc.intro }}</p>

        <section v-for="(section, index) in doc.sections" :key="section.heading">
          <h2><span>{{ String(index + 1).padStart(2, '0') }}</span>{{ section.heading }}</h2>
          <p v-for="paragraph in section.paragraphs" :key="paragraph">{{ paragraph }}</p>
        </section>

        <p class="legal-foot">如对内容有疑问，请联系学校信息中心或辅导员。</p>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ type: 'agreement' | 'privacy' }>()
defineEmits<{ (e: 'close'): void }>()

const DOCS = {
  agreement: {
    title: '用户协议',
    intro:
      '欢迎使用绵小城。本协议适用于绵阳城市学院在校学生与教师使用本产品的全部场景，请在使用前仔细阅读。',
    sections: [
      {
        heading: '服务说明',
        paragraphs: [
          '绵小城面向本校师生提供学习记录、成长档案、办事服务与智能问答等功能。部分功能需登录后使用，游客仅可浏览公开内容。',
        ],
      },
      {
        heading: '账号与密码',
        paragraphs: [
          '账号由学校统一分配，不开放自助注册。首次登录后请立即修改初始密码，并妥善保管账号信息。',
          '账号仅限本人使用，不得转借、出租或出售。因个人保管不当造成的损失由账号持有人承担。',
        ],
      },
      {
        heading: '使用规范',
        paragraphs: [
          '请勿利用本产品发布违法、侵权、虚假或骚扰性内容，也请勿干扰系统正常运行、尝试获取他人数据。',
          '学校有权对违反规范的内容进行处理，并视情节暂停相关功能的使用权限。',
        ],
      },
      {
        heading: '协议变更',
        paragraphs: ['产品功能或管理要求调整时，我们可能更新本协议，并在登录页或站内公告中提示。'],
      },
    ],
  },
  privacy: {
    title: '隐私政策',
    intro: '我们只收集完成校园服务所必需的信息，并尽最大努力保护你的数据安全。',
    sections: [
      {
        heading: '我们收集的信息',
        paragraphs: [
          '账号信息：学号/工号、姓名、院系、班级、身份角色。',
          '联系方式：由你主动维护的手机号与 QQ，仅用于身份核验与快捷登录。',
          '使用信息：学习计划、成长记录、作品集、办事申请等你主动创建的内容。',
        ],
      },
      {
        heading: '信息的使用',
        paragraphs: [
          '用于身份识别、功能展示、办事流程流转与必要的安全校验，不用于与校园服务无关的商业用途。',
          '智能问答仅在提供服务所需范围内处理你的提问内容。',
        ],
      },
      {
        heading: '存储与保护',
        paragraphs: [
          '密码以不可逆方式加密存储，系统不会保存明文密码。',
          '我们采取访问控制、日志审计等措施防止数据被未授权访问、篡改或泄露。',
        ],
      },
      {
        heading: '你的权利',
        paragraphs: [
          '你可以在个人资料中查看与修改联系方式，也可以联系管理员申请更正或删除相关记录。',
          '如对信息处理有疑问，可通过辅导员或信息中心与我们联系。',
        ],
      },
    ],
  },
} as const

const doc = computed(() => DOCS[props.type])
</script>

<style scoped>
.legal-layer {
  position: fixed;
  inset: 0;
  z-index: 3000;
  display: flex;
  flex-direction: column;
  background: #ffffff;
  color: #16161a;
  animation: legal-in 0.26s cubic-bezier(0.22, 1, 0.36, 1);
}

.legal-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: calc(env(safe-area-inset-top) + 10px) 16px 10px;
  border-bottom: 1px solid #f0f0f2;
  background: rgba(255, 255, 255, 0.96);
  backdrop-filter: blur(8px);
}

.legal-back {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 6px 4px;
  border: none;
  background: transparent;
  color: #3d3d43;
  font-size: 13.5px;
  cursor: pointer;
}

.legal-title {
  font-size: 14px;
  font-weight: 600;
}

.legal-placeholder {
  width: 52px;
}

.legal-body {
  flex: 1;
  overflow-y: auto;
  padding: 22px 22px calc(env(safe-area-inset-bottom) + 40px);
  -webkit-overflow-scrolling: touch;
}

.legal-meta {
  margin: 0;
  font-size: 11px;
  color: #a1a1a6;
}

.legal-body h1 {
  margin: 10px 0 0;
  font-size: 24px;
  font-weight: 700;
  letter-spacing: 0.4px;
}

.legal-intro {
  margin: 12px 0 0;
  font-size: 13px;
  line-height: 1.85;
  color: #6f6f78;
}

.legal-body section {
  margin-top: 26px;
}

.legal-body h2 {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin: 0 0 8px;
  font-size: 14.5px;
  font-weight: 600;
}

.legal-body h2 span {
  font-size: 10.5px;
  font-weight: 500;
  color: #b0b0b5;
  letter-spacing: 1px;
}

.legal-body section p {
  margin: 7px 0 0;
  font-size: 13px;
  line-height: 1.9;
  color: #5c5c63;
}

.legal-foot {
  margin: 34px 0 0;
  padding-top: 16px;
  border-top: 1px solid #f0f0f2;
  font-size: 11.5px;
  color: #a1a1a6;
}

@keyframes legal-in {
  from {
    transform: translateX(24px);
    opacity: 0;
  }
}

/* ===== 桌面端：控制正文版心宽度，避免长文在宽屏上拉成一行 ===== */
@media (min-width: 900px) {
  .legal-bar {
    padding: 16px 32px;
  }
  .legal-title {
    font-size: 14px;
  }
  .legal-body {
    padding: 40px 24px 64px;
  }
  .legal-body > h1,
  .legal-body > p,
  .legal-body > section {
    max-width: 720px;
    margin-left: auto;
    margin-right: auto;
  }
  .legal-body h1 {
    margin-top: 12px;
    font-size: 28px;
  }
  .legal-intro {
    font-size: 14px;
  }
  .legal-body section {
    margin-top: 30px;
  }
  .legal-body h2 {
    font-size: 15.5px;
  }
  .legal-body section p {
    font-size: 13.5px;
    line-height: 1.95;
  }
}
</style>
