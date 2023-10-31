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
  <div
    v-bkloading="{loading: isLoading}"
    class="pulsar-detail-page">
    <BkTab
      v-model:active="activePanel"
      class="detail-tab"
      type="card-tab">
      <BkTabPanel
        :label="$t('集群拓扑')"
        name="topo" />
      <BkTabPanel
        :label="$t('节点列表')"
        name="nodeList" />
      <BkTabPanel
        :label="$t('基本信息')"
        name="baseInfo" />
      <BkTabPanel
        :label="$t('变更记录')"
        name="record" />
      <BkTabPanel
        :label="$t('监控仪表盘')"
        name="monitor" />
    </BkTab>
    <div class="content-wrapper">
      <ClusterTopo
        v-if="activePanel === 'topo'"
        :id="clusterId"
        cluster-type="pulsar"
        db-type="bigdata" />
      <BaseInfo
        v-if="activePanel === 'baseInfo' && clusterData"
        :data="clusterData" />
      <NodeList
        v-if="activePanel === 'nodeList'"
        :key="clusterId"
        :cluster-id="clusterId" />
      <ClusterEventChange
        v-if="activePanel === 'record'"
        :id="clusterId" />
      <MonitorDashboard
        v-if="activePanel === 'monitor'"
        :id="clusterId"
        cluster-type="pulsar" />
    </div>
  </div>
</template>
<script setup lang="ts">
  import { ref } from 'vue';
  import { useRequest } from 'vue-request';

  import { getClusterDetail } from '@services/pulsar';

  import { useGlobalBizs } from '@stores';

  import ClusterTopo from '@components/cluster-details/ClusterTopo.vue';
  import ClusterEventChange from '@components/cluster-event-change/EventChange.vue';
  import MonitorDashboard from '@components/cluster-monitor/MonitorDashboard.vue';

  import BaseInfo from './components/BaseInfo.vue';
  import NodeList from './components/node-list/Index.vue';

  interface Props {
    clusterId: number;
  }

  const props = defineProps<Props>();

  const activePanel = ref('topo');
  const globalBizsStore = useGlobalBizs();

  const {
    loading: isLoading,
    data: clusterData,
    run: fetchResourceDetails,
  } = useRequest(getClusterDetail, {
    manual: true,
  });

  watch(() => props.clusterId, () => {
    if (props.clusterId) {
      fetchResourceDetails({
        bk_biz_id: globalBizsStore.currentBizId,
        cluster_id: props.clusterId,
      });
    }
  }, {
    immediate: true,
  });
</script>
<style lang="less">
  .pulsar-detail-page {
    height: 100%;
    background: #fff;

    .detail-tab {
      .bk-tab-content {
        padding: 0;
      }
    }

    .content-wrapper {
      height: calc(100vh - 168px);
      padding: 0 24px;
      overflow: auto;
    }
  }
</style>
