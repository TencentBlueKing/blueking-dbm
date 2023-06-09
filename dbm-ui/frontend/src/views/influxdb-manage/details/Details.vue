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
  <MainBreadcrumbs>
    <template #append>
      <div class="status">
        <span class="status__label">{{ $t('状态') }}：</span>
        <span class="status__value">
          <DbStatus :theme="statusInfo.theme">{{ statusInfo.text }}</DbStatus>
        </span>
      </div>
    </template>
  </MainBreadcrumbs>
  <BkResizeLayout
    :border="false"
    class="cluster-details"
    collapsible
    initial-divide="280px"
    :max="380"
    :min="280">
    <template #aside>
      <AsideList @change="handleChangeInstance" />
    </template>
    <template #main>
      <div class="cluster-details__main">
        <DbCard
          class="cluster-details__base"
          mode="collapse"
          :title="$t('基本信息')">
          <BkLoading :loading="isLoading">
            <EditInfo
              :columns="baseColumns"
              :data="details"
              width="30%" />
          </BkLoading>
        </DbCard>
        <BkTab
          v-model:active="activeTab"
          class="cluster-details__tab"
          type="unborder-card">
          <BkTabPanel
            :label="$t('变更记录')"
            name="event">
            <EventChange
              :id="instInfo.id"
              class="pd-24"
              is-fetch-instance />
          </BkTabPanel>
          <BkTabPanel
            :label="$t('监控仪表盘')"
            name="monitor">
            <MonitorDashboard
              :id="instInfo.id"
              class="pd-24"
              :cluster-type="details?.role ?? ''"
              is-fetch-instance />
          </BkTabPanel>
        </BkTab>
      </div>
    </template>
  </BkResizeLayout>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { getInstanceDetails } from '@services/influxdb';

  import { useGlobalBizs, useMainViewStore } from '@stores';

  import EventChange from '@components/cluster-event-change/EventChange.vue';
  import MonitorDashboard from '@components/cluster-monitor/MonitorDashboard.vue';
  import EditInfo from '@components/editable-info/index.vue';
  import MainBreadcrumbs from '@components/layouts/MainBreadcrumbs.vue';

  import AsideList from './AsideList.vue';

  import type InfluxDBInstanceModel from '@/services/model/influxdb/influxdbInstance';

  // 设置主视图padding
  const mainViewStore = useMainViewStore();
  mainViewStore.hasPadding = false;
  mainViewStore.customBreadcrumbs = true;

  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();

  const isLoading = ref(false);
  const instInfo = reactive({
    id: 0,
    address: '',
  });
  const activeTab = ref('event');
  const details = ref<InfluxDBInstanceModel | undefined>();

  const statusInfo = computed(() => {
    const info = {
      theme: 'danger',
      text: t('异常'),
    };
    if (!details.value) return info;

    const { status } = details.value;

    if (status === 'running') {
      info.theme = 'success';
      info.text = t('正常');
    }

    if (status === 'restoring') {
      info.theme = 'loading';
      info.text = t('重建中');
    }

    return info;
  });

  const baseColumns = [
    [
      {
        label: 'ID',
        key: 'id',
      },
      {
        label: t('实例'),
        key: 'instance_address',
      },
    ],
    [
      {
        label: t('所属分组'),
        key: 'group_name',
      },
      {
        label: t('管控区域'),
        key: 'bk_cloud_name',
      },
    ],
    [
      {
        label: t('创建人'),
        key: 'creator',
      },
      {
        label: t('部署时间'),
        key: 'create_at',
      },
    ],
  ];

  const fetchInstanceDetails = () => {
    isLoading.value = true;
    getInstanceDetails({
      bk_biz_id: currentBizId,
      instance_address: instInfo.address,
    })
      .then((res) => {
        details.value = res;
        mainViewStore.$patch({
          breadCrumbsTitle: t('InfluxDB实例详情xx', { name: res.instance_address }),
        });
      })
      .finally(() => {
        isLoading.value = false;
      });
  };

  const handleChangeInstance = ({ id, instance }: {id:number, instance: string}) => {
    instInfo.id = id;
    instInfo.address = instance;
    fetchInstanceDetails();
  };
</script>

<style lang="less" scoped>
.cluster-details {
  height: calc(100% - 52px);

  :deep(.bk-resize-layout-aside-content) {
    width: calc(100% + 1px);
  }

  &__main {
    display: flex;
    height: 100%;
    overflow: hidden;
    flex-direction: column;
    align-items: center;

    .db-card {
      width: 100%;

      &.cluster-details__base {
        max-height: 188px;
        flex-shrink: 0;
      }
    }
  }

  &__tab {
    width: 100%;
    overflow: hidden;
    background-color: white;
    flex: 1;

    :deep(.bk-tab-header) {
      margin: 0 24px;
    }

    :deep(.bk-tab-content) {
      height: calc(100% - 42px);
      padding: 0;
    }
  }
}
</style>
