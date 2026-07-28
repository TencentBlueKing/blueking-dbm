<template>
  <div
    v-if="isLoading"
    class="rotate-loading ml-4"
    style="display: inline-block">
    <DbIcon
      svg
      type="sync-pending" />
  </div>
  <template v-else>
    <span v-if="type === 'text'">
      {{ tagInfo?.text || '--' }}
    </span>
    <BkTag
      v-else-if="tagInfo && tagInfo.status === ClusterLoad.HIGH"
      v-bk-tooltips="loadReasonTips"
      class="cluster-load-tag ml-4"
      :class="{ 'cluster-load-tag-clickable': Boolean(clusterId) }"
      :size="size"
      :theme="tagInfo.theme"
      type="stroke"
      @click.stop="handleGoDetail">
      <template #icon>
        <DbIcon :type="tagInfo.icon" />
      </template>
      {{ tagInfo.tagText }}
    </BkTag>
  </template>
</template>

<script setup lang="ts">
  import BkTag from 'bkui-vue/lib/tag';
  import _ from 'lodash';
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { queryClusterLoad } from '@services/source/dbbase';

  import { ClusterLoad, clusterRedisTypeList, ClusterTypes } from '@common/const';

  interface Props {
    clusterId?: number;
    clusterType: string;
    domain: string;
    // eslint-disable-next-line vue/require-default-prop
    size?: ComponentProps<typeof BkTag>['size'];
    type?: 'tag' | 'text';
  }

  type Emits = (e: 'goDetail', id: number, event: MouseEvent) => void;

  const props = withDefaults(defineProps<Props>(), {
    clusterId: 0,
    type: 'tag',
  });

  const emits = defineEmits<Emits>();

  const route = useRoute();
  const { t } = useI18n();

  // 后端未回显时间窗口时的兜底值，单位小时
  const defaultTimeRange = 24;

  // 指标枚举与后端保持一致，展示顺序跟随后端返回的 key，前端不排序
  const loadMetricRenderMap: Record<string, (timeRange: number, peak: number) => string> = {
    connections: (timeRange, peak) => t('近nh连接峰值', [timeRange, Math.round(peak)]),
    cpu: (timeRange, peak) => t('近nhCPU峰值', [timeRange, Number(peak.toFixed(2))]),
    disk: (timeRange, peak) => t('近nh磁盘峰值', [timeRange, Number(peak.toFixed(2))]),
    io: (timeRange, peak) => t('近nhIO峰值', [timeRange, Number(peak.toFixed(2))]),
    mem: (timeRange, peak) => t('近nh内存峰值', [timeRange, Number(peak.toFixed(2))]),
  };

  const tagInfoMap: Record<
    ClusterLoad,
    {
      icon: string;
      status: ClusterLoad;
      tagText: string;
      text: string;
      theme: 'danger' | 'success';
    }
  > = {
    [ClusterLoad.HIGH]: {
      icon: 'gaofuzai',
      status: ClusterLoad.HIGH,
      tagText: t('高负载'),
      text: t('高'),
      theme: 'danger',
    },
    [ClusterLoad.LOW]: {
      icon: 'difuzai',
      status: ClusterLoad.LOW,
      tagText: t('低负载'),
      text: t('低'),
      theme: 'success',
    },
  };

  const tagInfo = computed(() => {
    if (
      clusterLoadData.value &&
      !_.isEmpty(clusterLoadData.value.cluster_load_status_map) &&
      clusterLoadData.value.cluster_load_status_map[props.domain]
    ) {
      const { status } = clusterLoadData.value.cluster_load_status_map[props.domain]!;
      return tagInfoMap[status];
    }
    return;
  });

  // 命中「高」的维度明细，同一维度跨机器类型合并为一行，取所有实例的最大值
  const loadReasonList = computed(() => {
    const machineLoadMap = clusterLoadData.value?.cluster_load_data_map?.[props.domain];
    if (!machineLoadMap) {
      return [];
    }

    const timeRange = clusterLoadData.value?.time_range ?? defaultTimeRange;
    // 重复 set 已有 key 不改变插入顺序，行序即该指标在响应中首次出现的位置
    const metricStatMap = new Map<string, { isHigh: boolean; peak: number }>();

    Object.values(machineLoadMap).forEach((metricMap) => {
      Object.entries(metricMap).forEach(([metric, metricData]) => {
        // 无监控数据、以及后端新增但前端没有文案模板的指标一律跳过
        if (!metricData || !loadMetricRenderMap[metric]) {
          return;
        }
        // status 是与实例键混在同一层的保留 key，位置不保证，需先剥离
        const { status = '', ...instanceMap } = metricData;
        const prevStat = metricStatMap.get(metric);
        const instanceValueList = Object.values(instanceMap).filter((value) => typeof value === 'number');
        metricStatMap.set(metric, {
          isHigh: Boolean(prevStat?.isHigh) || status === ClusterLoad.HIGH,
          peak: Math.max(prevStat?.peak ?? -Infinity, ...instanceValueList),
        });
      });
    });

    return Array.from(metricStatMap).reduce<string[]>(
      (result, [metric, { isHigh, peak }]) =>
        isHigh && peak > -Infinity ? [...result, loadMetricRenderMap[metric](timeRange, peak)] : result,
      [],
    );
  });

  const loadReasonTips = computed(() => loadReasonList.value.join('\n') || t('暂无负载明细数据'));

  const { data: clusterLoadData, loading: isLoading } = useRequest(
    (params) =>
      queryClusterLoad(params, {
        cache: route.name as string,
      }),
    {
      defaultParams: [
        {
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          cluster_type: props.clusterType === ClusterTypes.REDIS ? clusterRedisTypeList.join(',') : props.clusterType,
        },
      ],
      // pollingInterval: 10 * 1000,
    },
  );

  const handleGoDetail = (event: MouseEvent) => {
    if (props.clusterId) {
      emits('goDetail', props.clusterId, event);
    }
  };
</script>

<style lang="less">
  .cluster-load-tag {
    padding: 0 6px 0 4px !important;

    &.cluster-load-tag-clickable {
      cursor: pointer;
    }

    [class*='db-icon'] {
      display: inline !important;
      margin: 0 !important;
      color: unset !important;
    }
  }
</style>
