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
  <Teleport to="#dbContentHeaderAppend">
    <div
      v-if="isStretchLayoutOpen"
      class="replica-set-breadcrumbs-box">
      <BkTag>{{ data.cluster_name }}</BkTag>
      <div class="replica-set-breadcrumbs-box-status">
        <span>{{ t('状态') }} :</span>
        <RenderClusterStatus
          class="ml-8"
          :data="data.status" />
      </div>
      <div class="replica-set-breadcrumbs-box-button">
        <BkButton
          size="small"
          @click="handleCopyMasterDomainDisplayName">
          {{ t('复制访问地址') }}
        </BkButton>
        <BkDropdown
          class="ml-4">
          <BkButton
            class="more-button "
            size="small">
            <DbIcon type="more" />
          </BkButton>
          <template #content>
            <BkDropdownMenu>
              <BkDropdownItem>
                <BkButton
                  :disabled="data.operationDisabled"
                  text
                  @click="handleDisableCluster">
                  {{ t('禁用集群') }}
                </BkButton>
              </BkDropdownItem>
            </BkDropdownMenu>
          </template>
        </BkDropdown>
      </div>
    </div>
  </Teleport>
  <div
    v-bkloading="{loading: isLoading}"
    class="cluster-details">
    <BkTab
      v-model:active="activePanelKey"
      class="content-tabs"
      type="card-tab">
      <BkTabPanel
        :label="t('集群拓扑')"
        name="topo" />
      <BkTabPanel
        :label="t('基本信息')"
        name="info" />
      <BkTabPanel
        :label="t('变更记录')"
        name="record" />
      <BkTabPanel
        v-for="item in monitorPanelList"
        :key="item.name"
        :label="item.label"
        :name="item.name" />
    </BkTab>
    <div class="content-wrapper">
      <ClusterTopo
        v-if="activePanelKey === 'topo'"
        :id="clusterId"
        :cluster-type="ClusterTypes.MONGODB"
        :db-type="DBTypes.MONGODB" />
      <BaseInfo
        v-if="activePanelKey === 'info' && data"
        :data="data" />
      <ClusterEventChange
        v-if="activePanelKey === 'record'"
        :id="clusterId" />
      <MonitorDashboard
        v-if="activePanelKey === activePanel?.name"
        :url="activePanel?.link" />
    </div>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import MongodbDetailModel from '@services/model/mongodb/mongodb-detail';
  import { getMongoClusterDetails } from '@services/source/mongodb';
  import { getMonitorUrls } from '@services/source/monitorGrafana';

  import {
    useCopy,
    useStretchLayout,
  } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import {
    ClusterTypes,
    DBTypes,
  } from '@common/const';

  import RenderClusterStatus from '@components/cluster-common/RenderStatus.vue';
  import ClusterTopo from '@components/cluster-details/ClusterTopo.vue';
  import ClusterEventChange from '@components/cluster-event-change/EventChange.vue';
  import MonitorDashboard from '@components/cluster-monitor/MonitorDashboard.vue';

  import { useDisableCluster } from '../../hooks/useDisableCluster';

  import BaseInfo from './BaseInfo.vue';

  interface Props {
    clusterId: number;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();
  const { isOpen: isStretchLayoutOpen } = useStretchLayout();
  const copy = useCopy();
  const disableCluster = useDisableCluster();

  const activePanelKey = ref('topo');
  const data = ref(new MongodbDetailModel());
  const currentClusterType = ref('');
  const monitorPanelList = ref<{
    label: string,
    name: string,
    link: string,
  }[]>([]);

  const activePanel = computed(() => {
    const targetPanel = monitorPanelList.value.find(item => item.name === activePanelKey.value);
    return targetPanel;
  });

  const {
    loading: isLoading,
    run: fetchResourceDetails,
  } = useRequest(getMongoClusterDetails, {
    manual: true,
    onSuccess(result) {
      data.value = result;
      currentClusterType.value = result.cluster_type;
    },
  });

  const { run: runGetMonitorUrls } = useRequest(getMonitorUrls, {
    manual: true,
    onSuccess(res) {
      if (res.urls.length > 0) {
        monitorPanelList.value = res.urls.map(item => ({
          label: item.view,
          name: item.view,
          link: item.url,
        }));
      }
    },
  });

  watch(() => [props.clusterId, currentClusterType.value], () => {
    if (!props.clusterId) {
      return;
    }
    fetchResourceDetails({
      cluster_id: props.clusterId,
    });
    if (!currentClusterType.value) {
      return;
    }
    runGetMonitorUrls({
      bk_biz_id: currentBizId,
      cluster_type: currentClusterType.value,
      cluster_id: props.clusterId,
    });
  }, {
    immediate: true,
  });

  const handleCopyMasterDomainDisplayName = () => {
    copy(data.value.masterDomainDisplayName);
  };

  const handleDisableCluster = () => {
    disableCluster(data.value);
  };
</script>

<style lang="less">
.replica-set-breadcrumbs-box {
  display: flex;
  width: 100%;
  margin-left: 8px;
  font-size: 12px;
  align-items: center;

  .replica-set-breadcrumbs-box-status {
    display: flex;
    margin-left: 30px;
    align-items: center;
  }

  .replica-set-breadcrumbs-box-button {
    display: flex;
    margin-left: auto;
    align-items: center;

    .more-button {
      padding: 3px 6px;
    }
  }
}
</style>

<style lang="less" scoped>
  .cluster-details {
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
  }
</style>
