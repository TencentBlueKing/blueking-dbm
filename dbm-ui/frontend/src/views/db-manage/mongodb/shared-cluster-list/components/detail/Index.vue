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
      v-if="isStretchLayoutOpen && data"
      class="shared-cluster-breadcrumbs-box">
      <BkTag>{{ data.cluster_name }}</BkTag>
      <div class="shared-cluster-breadcrumbs-box-status">
        <span>{{ t('状态') }} :</span>
        <RenderClusterStatus
          class="ml-8"
          :data="data.status" />
      </div>
      <div class="shared-cluster-breadcrumbs-box-button">
        <BkButton
          :disabled="data.isOffline"
          size="small"
          @click="handleShowAccessEntry">
          {{ t('获取访问方式') }}
        </BkButton>
        <BkButton
          class="ml-4"
          size="small"
          @click="handleToCapacityChange">
          {{ t('集群容量变更') }}
        </BkButton>
        <BkDropdown class="ml-4">
          <BkButton
            class="more-button"
            size="small">
            <DbIcon type="more" />
          </BkButton>
          <template #content>
            <BkDropdownMenu class="dropdown-menu-with-button">
              <BkDropdownItem>
                <BkButton
                  :disabled="Boolean(data.operationTicketId)"
                  text
                  @click="handleDisableCluster([data])">
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
    v-bkloading="{ loading: isLoading }"
    class="cluster-details">
    <BkTab
      v-model:active="activePanelKey"
      class="content-tabs"
      type="card-tab">
      <BkTabPanel
        v-if="checkDbConsole('mongodb.sharedClusterList.clusterTopo')"
        :label="t('集群拓扑')"
        name="topo" />
      <BkTabPanel
        v-if="checkDbConsole('mongodb.sharedClusterList.basicInfo')"
        :label="t('基本信息')"
        name="info" />
      <BkTabPanel
        v-if="checkDbConsole('mongodb.sharedClusterList.changeLog')"
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
  <AccessEntry
    v-if="data"
    v-model:is-show="accessEntryInfoShow"
    :data="data" />
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getMongoClusterDetails } from '@services/source/mongodb';
  import { getMonitorUrls } from '@services/source/monitorGrafana';

  import { useStretchLayout } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes, DBTypes, TicketTypes } from '@common/const';

  import RenderClusterStatus from '@components/cluster-status/Index.vue';

  import ClusterTopo from '@views/db-manage/common/cluster-details/ClusterTopo.vue';
  import ClusterEventChange from '@views/db-manage/common/cluster-event-change/EventChange.vue';
  import MonitorDashboard from '@views/db-manage/common/cluster-monitor/MonitorDashboard.vue';
  import { useOperateClusterBasic } from '@views/db-manage/common/hooks';
  import AccessEntry from '@views/db-manage/mongodb/components/AccessEntry.vue';

  import { checkDbConsole } from '@utils';

  import BaseInfo from './BaseInfo.vue';

  interface Props {
    clusterId: number;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const router = useRouter();
  const { currentBizId } = useGlobalBizs();
  const { isOpen: isStretchLayoutOpen } = useStretchLayout();
  const { handleDisableCluster } = useOperateClusterBasic(ClusterTypes.MONGODB, {
    onSuccess: () => fetchResourceDetails({ cluster_id: props.clusterId }),
  });

  const activePanelKey = ref('topo');
  const monitorPanelList = ref<
    {
      label: string;
      link: string;
      name: string;
    }[]
  >([]);
  const accessEntryInfoShow = ref(false);

  const activePanel = computed(() => monitorPanelList.value.find((item) => item.name === activePanelKey.value));

  const {
    data,
    loading: isLoading,
    run: fetchResourceDetails,
  } = useRequest(getMongoClusterDetails, {
    manual: true,
  });

  const { run: runGetMonitorUrls } = useRequest(getMonitorUrls, {
    manual: true,
    onSuccess(res) {
      if (res.urls.length > 0) {
        monitorPanelList.value = res.urls.map((item) => ({
          label: item.view,
          link: item.url,
          name: item.view,
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
        cluster_id: props.clusterId,
      });
      runGetMonitorUrls({
        bk_biz_id: currentBizId,
        cluster_id: props.clusterId,
        cluster_type: ClusterTypes.MONGO_SHARED_CLUSTER,
      });
    },
    {
      immediate: true,
    },
  );

  const handleShowAccessEntry = () => {
    accessEntryInfoShow.value = true;
  };

  const handleToCapacityChange = () => {
    const routeInfo = router.resolve({
      name: TicketTypes.MONGODB_SCALE_UPDOWN,
      query: {
        masterDomain: data.value?.master_domain,
      },
    });
    window.open(routeInfo.href, '_blank');
  };
</script>

<style lang="less">
  .shared-cluster-breadcrumbs-box {
    display: flex;
    width: 100%;
    margin-left: 8px;
    font-size: 12px;
    align-items: center;

    .shared-cluster-breadcrumbs-box-status {
      display: flex;
      margin-left: 30px;
      align-items: center;
    }

    .shared-cluster-breadcrumbs-box-button {
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
      height: calc(100vh - var(--notice-height) - 168px);
      padding: 0 24px;
      overflow: auto;
    }
  }
</style>
