<template>
  <DbCard
    class="bar-chart"
    mode="collapse"
    :title="t('主机数量 - 按DB类型统计')">
    <div class="y-axis-top">{{ t('数量（台）') }}</div>
    <div
      ref="chart"
      style="height: 200px" />
  </DbCard>
</template>

<script setup lang="ts">
  import { BarChart } from 'echarts/charts';
  import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components';
  import * as echarts from 'echarts/core';
  import { CanvasRenderer } from 'echarts/renderers';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getGroupCount } from '@services/source/dbresourceResource';

  import { DBTypeInfos, DBTypes } from '@common/const';

  const { t } = useI18n();

  echarts.use([TooltipComponent, LegendComponent, GridComponent, BarChart, CanvasRenderer]);

  const chart = ref();
  let chartInstance: echarts.ECharts;

  const option = ref({
    tooltip: {
      trigger: 'item',
      borderColor: 'transparent',
      backgroundColor: 'rgba(255, 255, 255, 0.96)',
      textStyle: {
        color: '#63656E',
        fontSize: 12,
      },
      formatter: `
        <p style="margin-bottom: 4px;">{a}</p>
        <p class="var-row">{b} : <span style="font-weight:bold;">{c} 台</span></p>
        <style>
          .var-row {
            position: relative;
            padding-left: 14px;
          }
          .var-row::before {
            position: absolute;
            content: '';
            width: 8px;
            height: 2px;
            background: #3A84FF;
            top: 50%;
            transform: translateY(-50%);
            left: 0;
          }
        </style>
      `,
    },
    legend: {
      show: true,
      bottom: 0,
    },
    grid: {
      left: 0,
      right: 0,
      bottom: 40,
      containLabel: true,
    },
    xAxis: [
      {
        type: 'category',
        data: [] as string[],
        axisTick: {
          alignWithLabel: true,
        },
      },
    ],
    yAxis: [
      {
        type: 'value',
        nameGap: 20,
      },
    ],
    series: [
      {
        name: t('主机数量'),
        type: 'bar',
        barWidth: '32px',
        data: [] as number[],
        label: {
          show: true,
          position: 'top',
        },
        itemStyle: {
          color: '#3A84FF',
        },
      },
    ],
  });

  const { run: fetchData } = useRequest(getGroupCount, {
    initialData: [],
    manual: true,
    onSuccess(data) {
      option.value.xAxis[0].data = data.map((item) => DBTypeInfos[item.rs_type as DBTypes]?.name || t('公共'));
      option.value.series[0].data = data.map((item) => item.count);
      chartInstance.setOption(option.value);
    },
  });

  onMounted(() => {
    chartInstance = echarts.init(chart.value);
    fetchData();
  });
</script>

<style lang="less" scoped>
  .bar-chart {
    transform: translate(0, 0);

    :deep(.db-card__content) {
      padding: 0 22px;
    }

    .y-axis-top {
      position: fixed;
      top: 65px;
      font-size: 12px;
      color: #63656e;
    }
  }
</style>
