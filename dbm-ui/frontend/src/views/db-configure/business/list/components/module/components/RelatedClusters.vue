<template>
  <span class="module-info-item related-clusters-wrapper">
    <span class="module-info-label">{{ t('关联集群') }}：</span>
    <span
      v-if="relatedClusterCount > 0"
      ref="relatedClustersRef"
      class="related-clusters-count">
      {{ relatedClusterCount }}
    </span>
    <span v-else>--</span>
  </span>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import { ClusterTypes } from '@common/const';
  import { dbTippy } from '@common/tippy';

  import type { RelatedCluster } from '@views/db-configure/common/types';

  interface Props {
    clusterType?: ClusterTypes;
    relatedClusterCount: number;
    relatedClusterList?: RelatedCluster[];
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const router = useRouter();

  /** 集群类型到路由名称的映射 */
  const clusterTypeToRouteName: Partial<Record<ClusterTypes, string>> = {
    [ClusterTypes.DORIS]: 'dorisClusterDetail',
    [ClusterTypes.ES]: 'elasticSearchClusterDetail',
    [ClusterTypes.HDFS]: 'hdfsClusterDetail',
    [ClusterTypes.INFLUXDB]: 'influxDbClusterDetail',
    [ClusterTypes.KAFKA]: 'kafkaClusterDetail',
    [ClusterTypes.MONGODB]: 'mongodbSharedClusterDetail',
    [ClusterTypes.ORACLE]: 'oracleSingleClusterDetail',
    [ClusterTypes.PULSAR]: 'pulsarClusterDetail',
    [ClusterTypes.REDIS]: 'redisClusterDetail',
    [ClusterTypes.REDIS_CLUSTER]: 'redisClusterHaDetail',
    [ClusterTypes.REDIS_INSTANCE]: 'redisInstanceDetail',
    [ClusterTypes.RIAK]: 'riakClusterDetail',
    [ClusterTypes.SQLSERVER_HA]: 'SqlServerHaClusterDetail',
    [ClusterTypes.SQLSERVER_SINGLE]: 'SqlServerSingleClusterDetail',
    [ClusterTypes.TENDBCLUSTER]: 'tendbClusterDetail',
    [ClusterTypes.TENDBHA]: 'tendbHaDetail',
    [ClusterTypes.TENDBSINGLE]: 'tendbsingleDetail',
  };

  /** 关联集群 tooltip 白底纵向展示 */
  const relatedClustersRef = ref<HTMLElement>();
  let relatedClustersTippy: any = null;

  /** 导航到集群详情页的参数配置 Tab（新标签页打开） */
  const goToClusterDetail = (clusterId: number) => {
    const routeName = props.clusterType ? clusterTypeToRouteName[props.clusterType] : null;
    if (!routeName) return;

    const routeUrl = router.resolve({
      name: routeName,
      params: {
        clusterId,
      },
      query: {
        __cluster_detail_panel__: 'paramConfig',
      },
    });
    window.open(routeUrl.href, '_blank');
  };

  /** 创建 tooltip 内容（DOM 元素，支持点击事件） */
  const createTooltipContent = (): HTMLElement => {
    const list = props.relatedClusterList || [];
    if (list.length === 0) return document.createElement('div');

    const wrapper = document.createElement('div');
    wrapper.className = 'related-clusters-tooltip';

    const listEl = document.createElement('div');
    listEl.className = 'related-clusters-list';

    list.forEach((cluster) => {
      const item = document.createElement('div');
      item.className = 'related-cluster-item';
      item.textContent = cluster.name;
      item.style.cursor = 'pointer';
      item.style.color = '#3a84ff';
      item.style.lineHeight = '28px';
      item.style.padding = '0 12px';
      item.addEventListener('click', (e) => {
        e.stopPropagation();
        goToClusterDetail(cluster.id);
        relatedClustersTippy?.hide();
      });
      listEl.appendChild(item);
    });

    wrapper.appendChild(listEl);
    return wrapper;
  };

  watchPostEffect(() => {
    const el = relatedClustersRef.value;
    const list = props.relatedClusterList || [];
    relatedClustersTippy?.destroy();
    relatedClustersTippy = null;
    if (el && list.length > 0) {
      const content = createTooltipContent();
      relatedClustersTippy = dbTippy(el, {
        allowHTML: true,
        appendTo: () => document.body,
        arrow: true,
        content,
        hideOnClick: true,
        interactive: true,
        placement: 'top',
        theme: 'light',
        trigger: 'click',
        zIndex: 9999,
      });
    }
  });

  onUnmounted(() => {
    relatedClustersTippy?.destroy();
  });
</script>

<style lang="less" scoped>
  .related-clusters-wrapper {
    .related-clusters-count {
      margin-left: 4px;
      font-weight: 700;
      color: #3a84ff;
      cursor: pointer;
    }
  }
</style>

<style lang="less">
  .related-clusters-tooltip {
    padding: 4px 0;

    .related-clusters-list {
      max-height: 240px;
      overflow-y: auto;
    }

    .related-cluster-item {
      line-height: 28px;
      padding: 0 12px;
      color: #3a84ff;
      cursor: pointer;

      &:hover {
        background-color: #f0f1f5;
      }
    }
  }
</style>
