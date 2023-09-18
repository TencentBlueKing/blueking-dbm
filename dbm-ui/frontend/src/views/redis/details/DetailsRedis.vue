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
    class="cluster-details">
    <BkTab
      v-model:active="activePanel"
      class="content-tabs"
      type="card-tab">
      <BkTabPanel
        :label="$t('集群拓扑')"
        name="topo" />
      <BkTabPanel
        :label="$t('基本信息')"
        name="info" />
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
        :cluster-type="DBTypes.REDIS"
        :db-type="DBTypes.REDIS" />
      <BaseInfo
        v-if="activePanel === 'info' && data"
        :data="data" />
      <ClusterEventChange
        v-if="activePanel === 'record'"
        :id="currentClusterId" />
      <MonitorDashboard
        v-if="activePanel === 'monitor'"
        :id="currentClusterId"
        :cluster-type="currentClusterType" />
    </div>
  </div>
</template>

<script setup lang="ts">
  import { getResourceDetails } from '@services/clusters';
  import type { ResourceRedisItem } from '@services/types/clusters';

  import {
    useGlobalBizs,
  } from '@stores';

  import { DBTypes } from '@common/const';

  import ClusterTopo from '@components/cluster-details/ClusterTopo.vue';
  import ClusterEventChange from '@components/cluster-event-change/EventChange.vue';
  import MonitorDashboard from '@components/cluster-monitor/MonitorDashboard.vue';

  import BaseInfo from './BaseInfo.vue';

  const emits = defineEmits<{
    'change': [value: ResourceRedisItem]
  }>();

  const globalBizsStore = useGlobalBizs();
  const route = useRoute();

  const isLoading = ref(false);
  const activePanel = ref('topo');
  const data = ref<ResourceRedisItem>();
  const currentClusterId = computed(() => Number(route.query.cluster_id));
  const currentClusterType = computed(() => data.value?.cluster_type ?? '');

  watch(currentClusterId, () => {
    fetchResourceDetails();
  }, { immediate: true });

  /**
   * 获取集群详情
   */
  function fetchResourceDetails() {
    if (!currentClusterId.value) return;

    const params = {
      type: DBTypes.REDIS,
      bk_biz_id: globalBizsStore.currentBizId,
      id: currentClusterId.value,
    };
    isLoading.value = true;
    getResourceDetails<ResourceRedisItem>(DBTypes.REDIS, params)
      .then((res) => {
        data.value = res;
        emits('change', res);
      })
      .finally(() => {
        isLoading.value = false;
      });
  }
</script>

<style lang="less" scoped>
  .cluster-details {
    height: 100%;

    .content-tabs {
      :deep(.bk-tab-content) {
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
