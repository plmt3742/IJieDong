<script setup lang="ts">
import ComingSoonPage from '@/components/ComingSoonPage.vue'
</script>

<template>
  <ComingSoonPage
    code="AD12"
    title="组件库"
    description="计划用于维护图表、卡片与状态组件，并约束 AI 答案只渲染已注册的 ChartSpec 组件。"
    :planned="[
      '组件注册表：类型、版本、适用场景与静态渲染边界',
      '图表预览：柱/条/饼/折线与表格降级',
      '组件启停与版本对比',
      'AI 调用协议与校验结果记录',
    ]"
  />
</template>
