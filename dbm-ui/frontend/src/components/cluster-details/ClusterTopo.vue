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
    :loading="topoState.loading"
    style="width: 100%; height: 100%;">
    <DbCard
      ref="clusterTopoRef"
      class="cluster-details__topo"
      title="">
      <template #header-right>
        <div
          class="flow-tools"
          @click.stop>
          <i
            v-bk-tooltips="$t('放大')"
            class="flow-tools__icon db-icon-plus-circle"
            @click.stop="handleZoomIn" />
          <i
            v-bk-tooltips="$t('缩小')"
            class="flow-tools__icon db-icon-minus-circle"
            @click.stop="handleZoomOut" />
          <i
            v-bk-tooltips="$t('还原')"
            class="flow-tools__icon db-icon-position"
            @click.stop="handleZoomReset" />
          <i
            v-bk-tooltips="screenIcon.text"
            class="flow-tools__icon"
            :class="[screenIcon.icon]"
            @click.stop="toggle" />
        </div>
      </template>
      <div
        :id="graphState.topoId"
        class="cluster-details__graph" />
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
            class="node-details__item">
            <span class="node-details__label">{{ item.label }}：</span>
            <span class="node-details__value">
              <Component
                :is="item.render(instDetails[item.key])"
                v-if="item.render" />
              <template v-else>{{ instDetails[item.key] || '--' }}</template>
            </span>
          </div>
          <a
            v-if="instState.nodeData && showMore"
            class="node-details__link"
            :href="instState.nodeData.url"
            target="_blank">
            {{ $t('更多详情') }}
            <i class="db-icon-link" />
          </a>
        </template>
      </BkLoading>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { getEsTopoGraph } from '@services/source/es';
  import { getHdfsTopoGraph } from '@services/source/hdfs';
  import { getKafkaTopoGraph } from '@services/source/kafka';
  import { getPulsarTopoGraph } from '@services/source/pulsar';
  import { getRedisTopoGraph } from '@services/source/redis';
  import { getRiakTopoGraph } from '@services/source/riak';
  import { getSpiderTopoGraph } from '@services/source/spider';
  import { getTendbhaTopoGraph } from '@services/source/tendbha';
  import { getTendbsingleTopoGraph } from '@services/source/tendbsingle';

  import { ClusterTypes } from '@common/const';

  import { useFullscreen } from '@vueuse/core';

  import {
    GraphData,
    type GraphLine,
    type GraphNode,
    type NodeConfig,
  } from './common/graphData';
  import { detailColumns, useRenderGraph } from './common/useRenderGraph';

  interface TopoState {
    loading: boolean,
    locations: GraphNode[],
    lines: GraphLine[]
  }

  interface Props {
    // eslint-disable-next-line vue/no-unused-properties
    dbType: string,
    clusterType: string,
    id: number,
    nodeCofig?: NodeConfig
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const showMore = computed(() => props.clusterType === ClusterTypes.TENDBHA);

  const apiMap: Record<string, (params: { cluster_id: number }) => Promise<any>> = {
    es: getEsTopoGraph,
    hdfs: getHdfsTopoGraph,
    kafka: getKafkaTopoGraph,
    pulsar: getPulsarTopoGraph,
    redis: getRedisTopoGraph,
    tendbsingle: getTendbsingleTopoGraph,
    tendbha: getTendbhaTopoGraph,
    tendbcluster: getSpiderTopoGraph,
    riak: getRiakTopoGraph,
  };

  /** 拓扑功能 */
  const topoState = reactive<TopoState>({
    loading: false,
    locations: [],
    lines: [],
  });
  const graphDataInst = new GraphData(props.clusterType, props.nodeCofig);
  const {
    graphState,
    instState,
    instDetails,
    renderDraph,
    handleZoomIn,
    handleZoomOut,
    handleZoomReset,
  } = useRenderGraph(props, graphDataInst.nodeConfig);

  /**
   * 获取拓扑数据
   */
  watch(() => props.id, (id) => {
    if (id) {
      fetchResourceTopo(id).then(() => {
        renderDraph(topoState.locations, topoState.lines);
      });
    }
  }, { immediate: true });

  /**
   * 拓扑全屏切换
   */
  const clusterTopoRef = ref<HTMLDivElement>();
  const { isFullscreen, toggle } = useFullscreen(clusterTopoRef);
  const screenIcon = computed(() => ({
    icon: isFullscreen.value ? 'db-icon-un-full-screen' : 'db-icon-full-screen',
    text: isFullscreen.value ? t('取消全屏') : t('全屏'),
  }));

  /**
   * 获取集群拓扑
   * @param id 集群资源ID
   */
  function fetchResourceTopo(id: number) {
    topoState.loading = true;
    return apiMap[props.clusterType]({ cluster_id: id })
      .then((res) => {
        try {
          const {
            locations,
            lines,
          } = graphDataInst.formatGraphData(res, props.dbType);
          topoState.locations = locations;
          topoState.lines = lines;
        } catch (e) {
          topoState.locations = [];
          topoState.lines = [];
        }
      })
      .catch(() => {
        topoState.locations = [];
        topoState.lines = [];
      })
      .finally(() => {
        topoState.loading = false;
      });
  }
</script>

<style lang="less" scoped>
  @import "@styles/mixins.less";

  .cluster-details__topo {
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

      &__icon {
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

  .cluster-details__graph {
    height: 100%;

    :deep(.bk-graph-svg) {
      path {
        pointer-events: none;
      }
    }

    :deep(.cluster-group) {
      width: 100%;
      height: 100%;
      font-size: @font-size-mini;
      cursor: default;
      background: @bg-white;
      border-radius: 4px;
      box-shadow: 0 2px 4px 0 rgb(25 25 41 / 5%);

      &__title {
        padding: 12px 14px 8px;
        .flex-center();
      }

      &__icon {
        width: 24px;
        margin-right: 8px;
        font-weight: bold;
        line-height: 24px;
        color: @white-color;
        text-align: center;
        background-color: #4bc7ad;
        border-radius: 2px;
        flex-shrink: 0;

        &--round {
          border-radius: 50%;
        }
      }

      &__label {
        font-size: @font-size-mini;
      }
    }

    :deep(.db-graph-label) {
      height: 20px;
      padding: 0 8px;
      font-size: @font-size-mini;
      line-height: 18px;
      color: @default-color;
      white-space: nowrap;
      background-color: #fafbfd;
      border: 1px solid rgb(151 155 165 / 30%);
      border-radius: 2px;
    }

    :deep(.cluster-node) {
      padding: 0 14px 0 46px;
      font-size: @font-size-mini;
      line-height: 28px;
      cursor: default;

      &.has-link {
        cursor: pointer;

        &:hover {
          background-color: @bg-dark-gray;
        }
      }

      &:hover {
        .cluster-node__link {
          display: block;
        }
      }

      &__tag {
        height: 20px;
        padding: 0 8px;
        margin: 0 4px;
        line-height: 18px;
        background-color: #FAFBFD;
        border: 1px solid #979BA5;
        border-radius: 2px;
        flex-shrink: 0;
      }

      &__link {
        display: none;
      }
    }

    :deep(.riak-node) {
      height: 100%;
      background: #FFF;
      border-radius: 4px;
      box-shadow: 0 2px 4px 0 #1919290d;

      .riak-node-content {
        line-height: 44px;
      }
    }
  }

  .node-details {
    min-width: 252px;
    min-height: 240px;
    padding: 6px 8px;

    &__item {
      display: flex;
      padding-bottom: 8px;
    }

    &__label {
      width: 90px;
      padding-right: 4px;
      text-align: right;
      flex-shrink: 0;
    }

    &__value {
      flex: 1;
      color: @title-color;
    }

    &__link {
      display: block;
      padding-top: 8px;
      text-align: center;
    }
  }
</style>
