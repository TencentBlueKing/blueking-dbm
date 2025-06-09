<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License athttps://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <BkLoading
    :loading="pageLoading"
    style="width: 100%; height: 100%">
    <DbCard
      ref="clusterTopoRef"
      class="cluster-details-topo"
      title="">
      <template #header-right>
        <div
          class="flow-tools"
          @click.stop>
          <DbIcon
            v-bk-tooltips="t('放大')"
            class="flow-tools-icon"
            type="plus-circle"
            @click.stop="handleZoomIn" />
          <DbIcon
            v-bk-tooltips="t('缩小')"
            class="flow-tools-icon"
            type="minus-circle"
            @click.stop="handleZoomOut" />
          <DbIcon
            v-bk-tooltips="t('还原')"
            class="flow-tools-icon"
            type="position"
            @click.stop="handleZoomReset" />
          <DbIcon
            v-bk-tooltips="screenIcon.text"
            class="flow-tools-icon"
            :type="screenIcon.icon"
            @click.stop="toggle" />
        </div>
      </template>
      <div
        id="clusterTopoGraphMain"
        class="cluster-details-graph" />
    </DbCard>
  </BkLoading>
  <div
    v-show="false"
    id="node-details-tips">
    <div class="node-details">
      <BkLoading :loading="instState.isLoading">
        <h5 class="pb-12">
          {{ instState.activeId }}
        </h5>
        <template v-if="instDetails">
          <div
            v-for="item of detailColumns"
            :key="item.key"
            class="node-details-item">
            <span class="node-details-label">{{ item.label }}：</span>
            <span class="node-details-value">
              <Component
                :is="item.render(instDetails[item.key])"
                v-if="item.render" />
              <template v-else>{{ instDetails[item.key] || '--' }}</template>
            </span>
          </div>
          <a
            v-if="instState.nodeData?.url && showMore"
            class="node-details-link"
            :href="instState.nodeData.url"
            target="_blank">
            {{ t('更多详情') }}
            <i class="db-icon-link" />
          </a>
        </template>
      </BkLoading>
    </div>
  </div>
</template>
<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import { getDorisTopoGraph } from '@services/source/doris';
  import { getEsTopoGraph } from '@services/source/es';
  import { getHdfsTopoGraph } from '@services/source/hdfs';
  import { getKafkaTopoGraph } from '@services/source/kafka';
  import { getMongoClustersTopoGraph } from '@services/source/mongodb';
  import { getPulsarTopoGraph } from '@services/source/pulsar';
  import { getRedisTopoGraph } from '@services/source/redis';
  import { getRiakTopoGraph } from '@services/source/riak';
  import { getHaClusterTopoGraph } from '@services/source/sqlserveHaCluster';
  import { getSingleClusterTopoGraph } from '@services/source/sqlserverSingleCluster';
  import { getTendbclusterTopoGraph } from '@services/source/tendbcluster';
  import { getTendbhaTopoGraph } from '@services/source/tendbha';
  import { getTendbsingleTopoGraph } from '@services/source/tendbsingle';
  import { type ResourceTopo } from '@services/types';

  import { ClusterTypes } from '@common/const';

  import DbStatus from '@components/db-status/index.vue';

  import { useFullscreen } from '@vueuse/core';

  import { type NodeConfig } from './common/graphData';
  import { useRenderGraph } from './common/useRenderGraph';

  interface Props {
    clusterType: string;
    // eslint-disable-next-line vue/no-unused-properties
    dbType: string;
    id: number;
    // eslint-disable-next-line vue/no-unused-properties
    nodeConfig?: NodeConfig;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const { handleZoomIn, handleZoomOut, handleZoomReset, instDetails, instState, renderDraph } = useRenderGraph(props);

  const clusterTopoRef = ref<HTMLDivElement>();
  const pageLoading = ref(false);

  const { isFullscreen, toggle } = useFullscreen(clusterTopoRef);

  const showMore = computed(() => props.clusterType === ClusterTypes.TENDBHA);
  const screenIcon = computed(() => ({
    icon: isFullscreen.value ? 'un-full-screen' : 'full-screen',
    text: isFullscreen.value ? t('取消全屏') : t('全屏'),
  }));

  const detailColumns = [
    {
      key: 'role',
      label: t('部署角色'),
    },
    {
      key: 'db_version',
      label: t('版本'),
    },
    {
      key: 'status',
      label: t('状态'),
      render: (status: 'running' | 'unavailable') => {
        if (!status) {
          return <span>--</span>;
        }

        const statusMap = {
          running: {
            text: t('运行中'),
            theme: 'success',
          },
          unavailable: {
            text: t('异常'),
            theme: 'danger',
          },
        };
        const info = statusMap[status] || statusMap.unavailable;
        return <DbStatus theme={info.theme}>{info.text}</DbStatus>;
      },
    },
    {
      key: 'ip',
      label: t('主机IP'),
    },
    {
      key: 'bk_idc_city_name',
      label: t('地域'),
    },
    {
      key: 'bk_sub_zone',
      label: t('园区'),
    },
    {
      key: 'bk_cpu',
      label: 'CPU',
      render: (value: number) => <span>{Number.isFinite(value) ? `${value}${t('核')}` : '--'}</span>,
    },
    {
      key: 'bk_mem',
      label: t('内存'),
      render: (value: number) => <span>{Number.isFinite(value) ? `${value}MB` : '--'}</span>,
    },
    {
      key: 'bk_disk',
      label: t('硬盘'),
      render: (value: number) => <span>{Number.isFinite(value) ? `${value}GB` : '--'}</span>,
    },
  ] as any;

  const apiMap: Record<string, (params: { cluster_id: number }) => Promise<any>> = {
    doris: getDorisTopoGraph,
    es: getEsTopoGraph,
    hdfs: getHdfsTopoGraph,
    kafka: getKafkaTopoGraph,
    mongodb: getMongoClustersTopoGraph,
    pulsar: getPulsarTopoGraph,
    redis: getRedisTopoGraph,
    riak: getRiakTopoGraph,
    sqlserver_ha: getHaClusterTopoGraph,
    sqlserver_single: getSingleClusterTopoGraph,
    tendbcluster: getTendbclusterTopoGraph,
    tendbha: getTendbhaTopoGraph,
    tendbsingle: getTendbsingleTopoGraph,
  };

  let topoData: ResourceTopo | null = null;

  watch(
    () => props.id,
    () => {
      if (props.id) {
        setTimeout(() => {
          fetchResourceTopo(props.id);
        });
      }
    },
    { immediate: true },
  );

  watch(isFullscreen, () => {
    if (topoData) {
      setTimeout(() => {
        renderDraph(topoData!);
      });
    }
  });

  const fetchResourceTopo = (id: number) => {
    pageLoading.value = true;
    return apiMap[props.clusterType]({ cluster_id: id })
      .then((data: ResourceTopo) => {
        topoData = data;
        renderDraph(data);
      })
      .finally(() => {
        pageLoading.value = false;
      });
  };
</script>
<style lang="less" scoped>
  @import '@styles/mixins.less';

  .cluster-details-topo {
    height: 100%;
    padding: 14px 0 0;

    :deep(.db-card__header) {
      padding: 0 24px 16px;
    }

    :deep(.db-card__content) {
      height: calc(100% - 36px);
      background-color: @bg-gray;
    }

    .flow-tools {
      .flex-center();

      .flow-tools-icon {
        display: block;
        margin-left: 16px;
        font-size: @font-size-large;
        text-align: center;
        cursor: pointer;

        &:hover {
          color: @primary-color;
        }
      }
    }
  }

  .cluster-details-graph {
    height: 100%;
  }

  .node-details {
    min-width: 252px;
    min-height: 240px;
    padding: 6px 8px;

    .node-details-item {
      display: flex;
      padding-bottom: 8px;
    }

    .node-details-label {
      width: 90px;
      padding-right: 4px;
      text-align: right;
      flex-shrink: 0;
    }

    .node-details-value {
      flex: 1;
      color: @title-color;
    }

    .node-details-link {
      display: block;
      padding-top: 8px;
      text-align: center;
    }
  }
</style>
