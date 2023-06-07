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
  <div class="hdfs-detail-page">
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
        :id="currentClusterId"
        cluster-type="hdfs"
        db-type="bigdata"
        :node-cofig="{ startX: 400 }" />
      <BaseInfo
        v-if="activePanel === 'baseInfo'"
        :cluster-id="currentClusterId" />
      <NodeList
        v-if="activePanel === 'nodeList'"
        :key="currentClusterId"
        :cluster-id="currentClusterId" />
      <ClusterEventChange
        v-if="activePanel === 'record'"
        :id="currentClusterId" />
      <MonitorDashboard
        v-if="activePanel === 'monitor'"
        :id="currentClusterId"
        cluster-type="hdfs" />
    </div>
  </div>
</template>
<script setup lang="ts">
  import { ref } from 'vue';
  import { useRoute } from 'vue-router';

  import ClusterTopo from '@components/cluster-details/ClusterTopo.vue';
  import ClusterEventChange from '@components/cluster-event-change/EventChange.vue';
  import MonitorDashboard from '@components/cluster-monitor/MonitorDashboard.vue';

  import BaseInfo from './components/BaseInfo.vue';
  import NodeList from './components/node-list/Index.vue';

  const route = useRoute();

  const activePanel = ref('topo');
  const currentClusterId = computed(() => Number(route.query.cluster_id));
</script>
<style lang="less">
  .hdfs-detail-page {
    height: 100%;

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
