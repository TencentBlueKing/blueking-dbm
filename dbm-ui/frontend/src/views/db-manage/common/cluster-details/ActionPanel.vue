<template>
  <div class="cluster-detail-action-panel-box">
    <BkTab
      v-model:active="activePanelKey"
      class="content-tabs"
      type="card-tab">
      <slot name="topo">
        <BkTabPanel
          :label="t('集群拓扑')"
          name="topo">
          <!-- prettier-ignore -->
          <ClusterInstance
            v-if="activePanelKey === 'topo'"
            :cluster-id="clusterData.id"
            :cluster-type="(clusterData.cluster_type as ISupportClusterType)"
            :db-type="dbType" />
        </BkTabPanel>
      </slot>
      <slot name="host">
        <BkTabPanel
          :label="t('集群主机')"
          name="hostList">
          <!-- prettier-ignore -->
          <HostList
            v-if="activePanelKey === 'hostList'"
            :cluster-id="clusterData.id"
            :cluster-type="(clusterData.cluster_type as ISupportClusterType)" />
        </BkTabPanel>
      </slot>
      <slot name="info">
        <BkTabPanel
          :label="t('基本信息')"
          name="info">
          <slot
            v-if="activePanelKey === 'info' && clusterData"
            name="infoContent">
            <BaseInfo :data="clusterData" />
          </slot>
        </BkTabPanel>
      </slot>
      <slot name="record">
        <BkTabPanel
          :label="t('变更记录')"
          name="record">
          <EventChange
            v-if="activePanelKey === 'record'"
            :id="clusterData.id" />
        </BkTabPanel>
      </slot>
      <template v-if="monitorPanelList && monitorPanelList.urls.length > 0">
        <BkTabPanel
          v-for="monirotItem in monitorPanelList.urls"
          :key="monirotItem.view"
          :label="monirotItem.view"
          :name="monirotItem.view">
          <MonitorDashboard
            v-if="activePanelKey === monirotItem.view"
            :url="monirotItem.url" />
        </BkTabPanel>
      </template>
    </BkTab>
  </div>
</template>
<script setup lang="ts">
  import type { VNode } from 'vue';
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getMonitorUrls } from '@services/source/monitorGrafana';

  import { clusterTypeInfos } from '@common/const';

  import BaseInfo from './components/BaseInfo.vue';
  import ClusterInstance from './components/cluster-instance/Index.vue';
  import EventChange from './components/EventChange.vue';
  import HostList from './components/HostList.vue';
  import MonitorDashboard from './components/MonitorDashboard.vue';

  interface Props {
    clusterData: ComponentProps<typeof BaseInfo>['data'];
  }

  interface Slots {
    host: () => VNode;
    info: () => VNode;
    infoContent: () => VNode;
    record: () => VNode;
    topo: () => VNode;
  }

  type ISupportClusterType = ComponentProps<typeof ClusterInstance>['clusterType'];

  const props = defineProps<Props>();
  defineSlots<Slots>();

  const { t } = useI18n();

  const activePanelKey = ref('');

  const dbType = computed(() => clusterTypeInfos[props.clusterData.cluster_type].dbType);

  watch(
    () => props.clusterData,
    () => {
      activePanelKey.value = '';
    },
    {
      immediate: true,
    },
  );

  const { data: monitorPanelList } = useRequest(getMonitorUrls, {
    defaultParams: [
      {
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        cluster_id: props.clusterData.id,
        cluster_type: props.clusterData.cluster_type,
      },
    ],
  });
</script>
<style lang="less">
  .cluster-detail-action-panel-box {
    .bk-tab-panel {
      padding: 0 20px;
    }

    .bk-tab-content {
      padding: 0;
    }

    .content-wrapper {
      height: calc(100vh - 168px);
      padding: 0 24px;
      overflow: auto;
    }
  }
</style>
