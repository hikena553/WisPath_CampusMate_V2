import { computed, type Ref } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { RadarChart, PieChart, BarChart, LineChart } from 'echarts/charts'
import { TooltipComponent, LegendComponent, RadarComponent, GridComponent } from 'echarts/components'
import type { ClassStats, ClassEvaluation } from '@/api/teacher'

// echarts 全局注册副作用：模块被任一组件 import 时执行一次，全局生效
use([CanvasRenderer, RadarChart, PieChart, BarChart, LineChart, TooltipComponent, LegendComponent, RadarComponent, GridComponent])

/**
 * 班级图表 options 工厂：桌面数据分析区与移动端图表子页共用，
 * 保证两处图表配置单一来源、不重复实现。
 */
export function useClassCharts(classStats: Ref<ClassStats>, evalData: Ref<ClassEvaluation>) {
  // ===== Class Evaluation Radar =====
  const evaluationRadarOptions = computed(() => {
    const g = evalData.value.growth
    if (!g || Object.keys(g).length === 0) return null
    const vals = [g.honor || 0, g.competition || 0, g.practice || 0, g.paper || 0, g.achievement || 0]
    const max = Math.max(...vals, 1)
    return {
      animation: false,
      tooltip: { trigger: 'item' },
      radar: {
        indicator: [
          { name: '荣誉', max: Math.max(max, 1) },
          { name: '竞赛', max: Math.max(max, 1) },
          { name: '实践', max: Math.max(max, 1) },
          { name: '论文', max: Math.max(max, 1) },
          { name: '成果', max: Math.max(max, 1) },
        ],
        axisName: { color: '#666', fontSize: 12 },
        splitArea: {
          areaStyle: {
            color: ['rgba(91,141,239,0.02)', 'rgba(91,141,239,0.06)'],
          },
        },
        splitLine: { lineStyle: { color: 'rgba(0,0,0,0.06)' } },
        axisLine: { lineStyle: { color: 'rgba(0,0,0,0.08)' } },
      },
      series: [{
        type: 'radar',
        data: [{
          value: vals,
          name: '班级综合',
          areaStyle: { color: 'rgba(91,141,239,0.25)' },
          lineStyle: { color: '#5b8def', width: 2 },
          itemStyle: { color: '#5b8def' },
        }],
      }],
    }
  })

  // ===== 性别比例饼图 =====
  const genderPieOptions = computed(() => {
    const data = classStats.value.gender_stats
    if (!data || Object.keys(data).length === 0) return null

    const colors = ['#5b8def', '#f56c6c', '#67c23a', '#e6a23c', '#909399']
    const pieData = Object.entries(data).map(([name, value], index) => ({
      name,
      value,
      itemStyle: { color: colors[index % colors.length] }
    }))

    return {
      tooltip: {
        trigger: 'item',
        formatter: '{b}: {c}人 ({d}%)'
      },
      legend: {
        orient: 'horizontal',
        bottom: 5,
        textStyle: { color: '#666', fontSize: 11 }
      },
      animation: false,
      series: [{
        name: '性别分布',
        type: 'pie',
        radius: ['35%', '65%'],
        center: ['50%', '42%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 4,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: { show: false },
        emphasis: {
          label: { show: true, fontSize: 13, fontWeight: 'bold' }
        },
        data: pieData,
      }]
    }
  })

  // ===== 心理危机比例饼图 =====
  const crisisPieOptions = computed(() => {
    const data = classStats.value.crisis_stats
    if (!data) return null

    const colors = ['#f56c6c', '#e6a23c', '#67c23a', '#909399']
    const names = ['高危', '中危', '低危', '已解决']
    const values = [data.severe || 0, data.moderate || 0, data.mild || 0, data.resolved || 0]

    const total = values.reduce((sum, v) => sum + v, 0)
    if (total === 0) return null

    const pieData = names.map((name, index) => ({
      name,
      value: values[index],
      itemStyle: { color: colors[index] }
    }))

    return {
      tooltip: {
        trigger: 'item',
        formatter: '{b}: {c}人 ({d}%)'
      },
      legend: {
        orient: 'horizontal',
        bottom: 5,
        textStyle: { color: '#666', fontSize: 11 }
      },
      animation: false,
      series: [{
        name: '危机分布',
        type: 'pie',
        radius: ['35%', '65%'],
        center: ['50%', '42%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 4,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: { show: false },
        emphasis: {
          label: { show: true, fontSize: 13, fontWeight: 'bold' }
        },
        data: pieData,
      }]
    }
  })

  // ===== 成绩分布柱状图 =====
  const gradeBarOptions = computed(() => {
    const data = classStats.value.grade_stats
    if (!data) return null

    const categories = ['优秀', '良好', '中等', '及格', '不及格']
    const values = [data.excellent || 0, data.good || 0, data.medium || 0, data.pass || 0, data.fail || 0]

    const total = values.reduce((sum, v) => sum + v, 0)
    if (total === 0) return null

    const colors = ['#67c23a', '#5b8def', '#e6a23c', '#f56c6c', '#909399']

    return {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' }
      },
      grid: {
        left: '3%', right: '4%', bottom: '8%', top: '8%', containLabel: true
      },
      xAxis: {
        type: 'category',
        data: categories,
        axisLabel: { color: '#666', fontSize: 11 }
      },
      yAxis: {
        type: 'value',
        axisLabel: { color: '#666' }
      },
      animation: false,
      series: [{
        name: '人数',
        type: 'bar',
        barWidth: '50%',
        data: values.map((value, index) => ({
          value,
          itemStyle: { color: colors[index], borderRadius: [3, 3, 0, 0] }
        })),
      }],
    }
  })

  // ===== 政治面貌饼图 =====
  const politicalPieOptions = computed(() => {
    const data = classStats.value.political_stats
    if (!data || Object.keys(data).length === 0) return null

    const total = Object.values(data).reduce((sum, v) => sum + v, 0)
    if (total === 0) return null

    const colors = ['#5b8def', '#67c23a', '#e6a23c', '#f56c6c', '#909399']
    const pieData = Object.entries(data).map(([name, value], index) => ({
      name,
      value,
      itemStyle: { color: colors[index % colors.length] }
    }))

    return {
      tooltip: {
        trigger: 'item',
        formatter: '{b}: {c}人 ({d}%)'
      },
      legend: {
        orient: 'horizontal',
        bottom: 5,
        textStyle: { color: '#666', fontSize: 11 }
      },
      animation: false,
      series: [{
        name: '政治面貌',
        type: 'pie',
        radius: ['35%', '65%'],
        center: ['50%', '42%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 4,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: { show: false },
        emphasis: {
          label: { show: true, fontSize: 13, fontWeight: 'bold' }
        },
        data: pieData,
      }]
    }
  })

  // ===== 预警趋势折线图 =====
  const crisisTrendOptions = computed(() => {
    const data = classStats.value.crisis_trend
    if (!data || data.length === 0) return null

    return {
      tooltip: {
        trigger: 'axis',
        formatter: '{b}<br/>预警数量: {c}'
      },
      grid: {
        left: '3%', right: '4%', bottom: '8%', top: '8%', containLabel: true
      },
      xAxis: {
        type: 'category',
        data: data.map(d => d.month),
        axisLabel: { color: '#666', fontSize: 11 }
      },
      yAxis: {
        type: 'value',
        axisLabel: { color: '#666' }
      },
      animation: false,
      series: [{
        name: '预警数量',
        type: 'line',
        data: data.map(d => d.count),
        smooth: true,
        lineStyle: { color: '#f56c6c', width: 2 },
        itemStyle: { color: '#f56c6c' },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(245,108,108,0.3)' },
              { offset: 1, color: 'rgba(245,108,108,0.05)' }
            ]
          }
        }
      }]
    }
  })

  // ===== 生源地柱状图 =====
  const hometownBarOptions = computed(() => {
    const data = classStats.value.hometown_stats
    if (!data || Object.keys(data).length === 0) return null

    const categories = Object.keys(data)
    const values = Object.values(data)

    const total = values.reduce((sum, v) => sum + v, 0)
    if (total === 0) return null

    return {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' }
      },
      grid: {
        left: '3%', right: '4%', bottom: '10%', top: '8%', containLabel: true
      },
      xAxis: {
        type: 'category',
        data: categories,
        axisLabel: { color: '#666', fontSize: 11, rotate: categories.length > 5 ? 30 : 0 }
      },
      yAxis: {
        type: 'value',
        axisLabel: { color: '#666' }
      },
      animation: false,
      series: [{
        name: '人数',
        type: 'bar',
        data: values,
        itemStyle: {
          color: '#5b8def',
          borderRadius: [3, 3, 0, 0]
        }
      }]
    }
  })

  return {
    evaluationRadarOptions,
    genderPieOptions,
    crisisPieOptions,
    gradeBarOptions,
    politicalPieOptions,
    crisisTrendOptions,
    hometownBarOptions,
  }
}