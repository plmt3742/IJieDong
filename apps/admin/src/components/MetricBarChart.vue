<script setup lang="ts">
import * as echarts from 'echarts/core'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { EChartsOption } from 'echarts'
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

echarts.use([BarChart, GridComponent, TooltipComponent, CanvasRenderer])

interface Props {
  option: EChartsOption
  height?: number
}

const props = withDefaults(defineProps<Props>(), { height: 320 })

const host = ref<HTMLDivElement | null>(null)
let chart: echarts.ECharts | null = null
let observer: ResizeObserver | null = null

function render(): void {
  if (!chart) return
  chart.setOption(props.option, true)
}

function resize(): void {
  chart?.resize()
}

onMounted(() => {
  if (!host.value) return
  chart = echarts.init(host.value)
  render()
  observer = new ResizeObserver(() => resize())
  observer.observe(host.value)
})

onBeforeUnmount(() => {
  observer?.disconnect()
  observer = null
  chart?.dispose()
  chart = null
})

watch(
  () => props.option,
  () => render(),
  { deep: true },
)
</script>

<template>
  <div ref="host" class="metric-chart" :style="{ height: `${height}px` }" />
</template>

<style scoped>
.metric-chart {
  width: 100%;
}
</style>
