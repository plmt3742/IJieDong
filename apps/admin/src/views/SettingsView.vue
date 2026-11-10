<script setup lang="ts">
import ComingSoonPage from '@/components/ComingSoonPage.vue'
</script>

<template>
  <ComingSoonPage
    code="AD10 / AD11 / AD13"
    title="设置"
    description="计划承载指标目录、数据质量与覆盖率、导出任务三类 P1 设置项。"
    :planned="[
      '指标目录：口径、适用层级、精度与启停',
      '数据质量：区域 × 指标 × 年份的覆盖与异常',
      '导出任务：记录、失败重试与过期文件清理',
      '系统参数与维护联系人信息',
    ]"
  />
</template>
