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
    v-bkloading="{ loading: isLoading }"
    class="riak-cluster-details">
    <BkTab
      v-model:active="activePanelKey"
      class="content-tabs"
      type="card-tab">
      <BkTabPanel
        :label="t('集群拓扑')"
        name="topo" />
      <BkTabPanel
        :label="t('节点列表')"
        name="nodeList" />
      <BkTabPanel
        :label="t('基本信息')"
        name="info" />
      <BkTabPanel name="record">
        <template #label>
          <div>
            <span>{{ t('变更记录') }}</span>
            <BkTag
              v-if="loadingCount"
              v-bk-tooltips="t('有n个任务正在进行中', [loadingCount])"
              class="loading-count-tag"
              radius="50px"
              theme="info">
              <template #icon>
                <DbStatus
                  theme="loading"
                  type="linear" />
              </template>
              {{ loadingCount }}
            </BkTag>
          </div>
        </template>
      </BkTabPanel>
      <BkTabPanel
        v-for="monitorPanelItem in monitorPanelList"
        :key="monitorPanelItem.name"
        :label="monitorPanelItem.label"
        :name="monitorPanelItem.name" />
    </BkTab>
    <div class="content-wrapper">
      <ClusterTopo
        v-if="activePanelKey === 'topo'"
        :id="clusterId"
        :cluster-type="ClusterTypes.RIAK"
        :db-type="DBTypes.RIAK" />
      <NodeList
        v-if="activePanelKey === 'nodeList' && data"
        :key="clusterId"
        :data="data" />
      <BaseInfo
        v-if="activePanelKey === 'info' && data"
        :data="data" />
      <ClusterEventChange
        v-if="activePanelKey === 'record'"
        :id="clusterId"
        v-model:loading-count="loadingCount" />
      <MonitorDashboard
        v-if="activePanelKey === activePanel?.name"
        :url="activePanel?.link" />
    </div>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import RiakModel from '@services/model/riak/riak';
  import { getMonitorUrls } from '@services/source/monitorGrafana';
  import { getRiakDetail } from '@services/source/riak';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes, DBTypes } from '@common/const';

  import ClusterTopo from '@components/cluster-details/ClusterTopo.vue';
  import MonitorDashboard from '@components/cluster-monitor/MonitorDashboard.vue';
  import DbStatus from '@components/db-status/index.vue';

  import BaseInfo from './components/BaseInfo.vue';
  import ClusterEventChange from './components/EventChange.vue';
  import NodeList from './components/NodeList.vue';

  interface Props {
    clusterId: number;
  }

  interface Emits {
    (e: 'detailChange', data: RiakModel): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();

  const activePanelKey = ref('topo');
  const loadingCount = ref(0);
  const data = ref<RiakModel>();

  const monitorPanelList = ref<Record<'label' | 'name' | 'link', string>[]>([]);

  const activePanel = computed(() =>
    monitorPanelList.value.find((panelItem) => panelItem.name === activePanelKey.value),
  );

  const { loading: isLoading, run: fetchResourceDetails } = useRequest(getRiakDetail, {
    manual: true,
    onSuccess(result) {
      data.value = result;
      emits('detailChange', result);
    },
  });

  const { run: runGetMonitorUrls } = useRequest(getMonitorUrls, {
    manual: true,
    onSuccess(monitorUrlsResult) {
      if (monitorUrlsResult.urls.length > 0) {
        monitorPanelList.value = monitorUrlsResult.urls.map((urlItem) => ({
          label: urlItem.view,
          name: urlItem.view,
          link: urlItem.url,
        }));
      }
    },
  });

  watch(
    () => props.clusterId,
    () => {
      if (!props.clusterId) {
        return;
      }
      fetchResourceDetails({
        id: props.clusterId,
      });
      runGetMonitorUrls({
        bk_biz_id: currentBizId,
        cluster_type: ClusterTypes.RIAK,
        cluster_id: props.clusterId,
      });
    },
    {
      immediate: true,
    },
  );
</script>

<style lang="less" scoped>
  .riak-cluster-details {
    height: 100%;
    background: #fff;

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

    .loading-count-tag {
      height: 18px;
      padding: 0 6px;
      margin: 2px 0 2px 4px;

      :deep(.bk-loading-indicator) {
        scale: 0.8;
        margin-right: -2px;
      }
    }
  }
</style>
