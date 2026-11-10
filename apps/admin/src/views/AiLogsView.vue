<script setup lang="ts">
import ComingSoonPage from '@/components/ComingSoonPage.vue'
</script>

<template>
  <ComingSoonPage
    code="AD09"
    title="问答记录"
    description="计划用于查看 AI 问答的问题、答案、调用工具与反馈，支撑内容安全与效果评估。"
    :planned="[
      '会话与消息列表：按用户、时间、状态筛选',
      '答案详情：结论、引用、ChartSpec 与数据快照',
      '工具调用链路与耗时、token 用量',
      '反馈与纠错记录，供评测集沉淀',
    ]"
  />
</template>
