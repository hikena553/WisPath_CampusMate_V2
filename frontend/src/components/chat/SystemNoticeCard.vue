<!--
  微信「服务通知」式卡片。

  系统通知不是聊天内容：它是一张带字段的凭证（谁发的、什么事、什么时间）。
  做成气泡会把「门店名称 / 联系电话 / 下单时间」这种键值对压成一段豆腐块，
  所以按通知卡来排：来源 → 标题 → 字段表，三段之间用留白分隔。

  不再有底部入口：通知只做告知，跳转交回业务页自己的入口，
  卡片上一行「进入×××」既抢了字段表的注意力，也要额外维护一份路由映射。
-->
<template>
  <article class="sn-card">
    <header class="sn-head">
      <span class="sn-icon" :style="{ background: card.app.color }" aria-hidden="true">
        {{ card.app.glyph }}
      </span>
      <span class="sn-app">{{ card.app.name }}</span>
      <span class="sn-more" aria-hidden="true"><i></i><i></i><i></i></span>
    </header>

    <h4 class="sn-title">{{ card.title }}</h4>

    <dl class="sn-fields">
      <div v-for="f in card.fields" :key="f.label" class="sn-field">
        <dt>{{ f.label }}</dt>
        <dd>{{ f.value }}</dd>
      </div>
    </dl>
  </article>
</template>

<script setup lang="ts">
import type { SystemNoticeCard } from '@/utils/systemNotice'

defineProps<{ card: SystemNoticeCard }>()
</script>

<style scoped>
.sn-card {
  /* 桌面端会话窗口很宽，卡片跟着拉满会像一张表格；限个宽度居中，读起来才是一张卡。
     width:100% 不能省：父级是列向 flex，左右 auto 外边距会盖掉 stretch，
     卡片会缩成「最宽那行文字」的宽度，两边空出一大片。 */
  width: 100%;
  max-width: 520px;
  margin: 0 auto;
  /* 底栏撤掉后由卡片自己收口，四边留白对称 */
  padding: 15px 14px;
  background: #fff;
  border-radius: 10px;
  /* 极轻的一层影：微信里卡片就是靠这点影子从灰底上浮起来的，再重就显得脏 */
  box-shadow: 0 1px 2px rgba(16, 24, 40, 0.05);
}

/* ---------- 来源行 ---------- */
.sn-head {
  display: flex;
  align-items: center;
  gap: 8px;
}
.sn-icon {
  flex-shrink: 0;
  display: grid;
  place-items: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  line-height: 1;
}
.sn-app {
  flex: 1;
  min-width: 0;
  font-size: 13px;
  color: #1f2329;
}
/* 右上角的「···」：微信里点开是小程序菜单，这里没有菜单可给，只作视觉占位 */
.sn-more {
  display: inline-flex;
  align-items: center;
  gap: 2.5px;
  padding: 4px 2px;
}
.sn-more i {
  width: 3px;
  height: 3px;
  border-radius: 50%;
  background: #c4c8ce;
}

/* ---------- 标题 ---------- */
.sn-title {
  /* 与来源行拉开一段：这一段留白就是微信卡片「头 / 身」的分界，压掉了整张卡会显得很挤 */
  margin: 20px 0 0;
  font-size: 15.5px;
  font-weight: 600;
  line-height: 1.4;
  color: #111827;
}

/* ---------- 字段表 ---------- */
.sn-fields {
  margin: 13px 0 0;
  display: flex;
  flex-direction: column;
  gap: 9px;
}
.sn-field {
  display: flex;
  gap: 10px;
  font-size: 13px;
  line-height: 1.5;
}
.sn-field dt {
  /* 标签列定宽：不定宽的话每行文字都会从不同位置起头，键值对就散了 */
  flex-shrink: 0;
  width: 64px;
  color: #8d9199;
}
.sn-field dd {
  flex: 1;
  min-width: 0;
  margin: 0;
  color: #1f2329;
  word-break: break-word;
}
</style>
