<template>
  <div class="cluster-detail-action-panel-box">
    <BkTab
      v-model:active="activePanel"
      class="content-tabs"
      type="card-tab">
      <slot name="topo">
        <BkTabPanel
          :label="t('集群拓扑')"
          name="topo">
          <ClusterTopo
            v-if="activePanel === 'topo'"
            :key="clusterData.id"
            :cluster-id="clusterData.id"
            :cluster-role-node-group="clusterRoleNodeGroup"
            :cluster-type="clusterType"
            :db-type="dbType" />
        </BkTabPanel>
      </slot>
      <slot name="info">
        <BkTabPanel
          :label="t('集群详情')"
          name="info">
          <slot
            v-if="activePanel === 'info' && clusterData"
            name="infoContent">
            <BaseInfo
              :key="clusterData.id"
              :data="clusterData" />
          </slot>
        </BkTabPanel>
      </slot>
      <slot name="host">
        <BkTabPanel
          :label="t('主机信息')"
          name="host">
          <HostList
            v-if="activePanel === 'host'"
            :key="clusterData.id"
            :cluster-id="clusterData.id"
            :cluster-type="clusterType" />
        </BkTabPanel>
      </slot>
      <slot name="instance">
        <BkTabPanel
          :label="t('集群实例')"
          name="instance">
          <Instancelist
            v-if="activePanel === 'instance'"
            :key="clusterData.id"
            :cluster-id="clusterData.id"
            :cluster-type="clusterType" />
        </BkTabPanel>
      </slot>
      <template v-if="monitorPanelList && monitorPanelList.urls.length > 0">
        <BkTabPanel
          v-for="monirotItem in monitorPanelList.urls"
          :key="monirotItem.view"
          :label="monirotItem.view"
          :name="monirotItem.view">
          <MonitorDashboard
            v-if="activePanel === monirotItem.view"
            :key="clusterData.id"
            :url="monirotItem.url" />
        </BkTabPanel>
      </template>
      <slot name="record">
        <BkTabPanel
          :label="t('变更记录')"
          name="record">
          <EventChange
            v-if="activePanel === 'record'"
            :id="clusterData.id"
            :key="clusterData.id" />
        </BkTabPanel>
      </slot>
    </BkTab>
  </div>
</template>
<script lang="ts">
  import DorisModel from '@services/model/doris/doris';
  import EsModel from '@services/model/es/es';
  import HdfsModel from '@services/model/hdfs/hdfs';
  import KafkaModel from '@services/model/kafka/kafka';
  import MongodbModel from '@services/model/mongodb/mongodb';
  import TendbhaModel from '@services/model/mysql/tendbha';
  import TendbsingleModel from '@services/model/mysql/tendbsingle';
  import PulsarModel from '@services/model/pulsar/pulsar';
  import RedisModel from '@services/model/redis/redis';
  import RiakModel from '@services/model/riak/riak';
  import SqlserverHaModel from '@services/model/sqlserver/sqlserver-ha';
  import SqlserverSingleModel from '@services/model/sqlserver/sqlserver-single';
  import TendbClusterModel from '@services/model/tendbcluster/tendbcluster';

  interface ClusterTypeRelateClusterModel {
    [ClusterTypes.DORIS]: DorisModel;
    [ClusterTypes.ES]: EsModel;
    [ClusterTypes.HDFS]: HdfsModel;
    [ClusterTypes.KAFKA]: KafkaModel;
    [ClusterTypes.MONGO_REPLICA_SET]: MongodbModel;
    [ClusterTypes.MONGO_SHARED_CLUSTER]: MongodbModel;
    [ClusterTypes.PULSAR]: PulsarModel;
    [ClusterTypes.REDIS_CLUSTER]: RedisModel;
    [ClusterTypes.REDIS_INSTANCE]: RedisModel;
    [ClusterTypes.REDIS]: RedisModel;
    [ClusterTypes.RIAK]: RiakModel;
    [ClusterTypes.SQLSERVER_HA]: SqlserverHaModel;
    [ClusterTypes.SQLSERVER_SINGLE]: SqlserverSingleModel;
    [ClusterTypes.TENDBCLUSTER]: TendbClusterModel;
    [ClusterTypes.TENDBHA]: TendbhaModel;
    [ClusterTypes.TENDBSINGLE]: TendbsingleModel;
  }
</script>
<script setup lang="ts" generic="T extends keyof ClusterTypeRelateClusterModel">
  import type { VNode } from 'vue';
  // import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';
  import { useRoute } from 'vue-router';

  import { getMonitorUrls } from '@services/source/monitorGrafana';
  import type { ClusterListNode } from '@services/types';

  import { useUrlSearch } from '@hooks';

  import { clusterTypeInfos, ClusterTypes } from '@common/const';

  import BaseInfo from './components/BaseInfo.vue';
  import ClusterTopo from './components/cluster-topo/Index.vue';
  import EventChange from './components/EventChange.vue';
  import HostList from './components/HostList.vue';
  import Instancelist from './components/InstanceList.vue';
  import MonitorDashboard from './components/MonitorDashboard.vue';

  export interface Props<C extends keyof ClusterTypeRelateClusterModel> {
    clusterData: ClusterTypeRelateClusterModel[C];
    clusterRoleNodeGroup: Record<string, ClusterListNode[]>;

    clusterType: C;
  }

  export interface Slots {
    host: () => VNode;
    info: () => VNode;
    infoContent: () => VNode;
    instance: () => VNode;
    record: () => VNode;
    topo: () => VNode;
  }

  // type ISupportClusterType = ComponentProps<typeof ClusterTopo>['clusterType'];

  const props = defineProps<Props<T>>();
  defineSlots<Slots>();

  const URL_MEMO_KEY = '__detail_panel__';

  const { t } = useI18n();
  const route = useRoute();
  const { appendSearchParams } = useUrlSearch();

  const activePanel = ref('');

  const dbType = computed(() => clusterTypeInfos[props.clusterData.cluster_type].dbType);

  watch(
    () => props.clusterData,
    () => {
      activePanel.value = String(route.query[URL_MEMO_KEY] || '');
    },
    {
      immediate: true,
    },
  );

  watch(activePanel, () => {
    appendSearchParams({
      [URL_MEMO_KEY]: activePanel.value,
    });
  });

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
