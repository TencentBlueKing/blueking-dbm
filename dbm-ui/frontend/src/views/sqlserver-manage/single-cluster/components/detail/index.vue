<template>
  <div
    v-bkloading="{ loading: isLoading }"
    class="cluster-details">
    <BkTab
      v-model:active="activePanel"
      class="content-tabs"
      type="card-tab">
      <BkTabPanel
        key="集群拓扑"
        :label="t('集群拓扑')"
        name="topo" />
      <BkTabPanel
        :label="t('集群监控')"
        name="monitor" />
      <BkTabPanel
        :label="t('基本信息')"
        name="info" />
      <BkTabPanel
        :label="t('变更记录')"
        name="record" />
    </BkTab>
    <div class="content-wrapper">
      <ClusterTopo
        v-if="activePanel === 'topo'"
        :id="singleClusterData.clusterId"
        :cluster-type="ClusterTypes.SQLSERVER_SINGLE"
        :db-type="DBTypes.SQLSERVER" />
      <BaseInfo
        v-if="activePanel === 'info'"
        :single-cluster-data="singleClusterData" />
      <ClusterEventChange
        v-if="activePanel === 'record'"
        :id="singleClusterData.clusterId" />
      <MonitorDashboard
        v-if="activePanel === 'monitor'"
        :url="monitorPanelList[0].link" />
    </div>
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getMonitorUrls } from '@services/source/monitorGrafana';

  import { useGlobalBizs } from '@stores';

  import {
    ClusterTypes,
    DBTypes,
  } from '@common/const';

  import ClusterTopo from '@components/cluster-details/ClusterTopo.vue';
  import ClusterEventChange from '@components/cluster-event-change/EventChange.vue';
  import MonitorDashboard from '@components/cluster-monitor/MonitorDashboard.vue';

  import BaseInfo from './BaseInfo.vue';

  interface Props {
    singleClusterData: {
      clusterId: number
    }
  }

  interface PanelItem {
    label: string,
    name: string,
    link: string,
  }

  const props = defineProps<Props>();

  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();

  const monitorPanelList = ref<PanelItem[]>([]);
  const activePanel = ref('');

  const {
    loading: isLoading,
    run: runGetMonitorUrls,
  } = useRequest(getMonitorUrls, {
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

  watch(
    () => props.singleClusterData, () => {
      runGetMonitorUrls({
        bk_biz_id: currentBizId,
        cluster_type: ClusterTypes.SQLSERVER_SINGLE,
        cluster_id: props.singleClusterData.clusterId,
      });
    },
    { immediate: true },
  );
</script>

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
