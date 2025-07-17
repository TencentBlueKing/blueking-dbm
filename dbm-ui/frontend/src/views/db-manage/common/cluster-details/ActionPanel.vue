<template>
  <BkLoading :loading="isLoading">
    <div
      ref="root"
      class="cluster-detail-action-panel-box">
      <BkTab
        v-if="!isLoading"
        :active="activePanel"
        class="content-tabs"
        type="card-tab"
        @change="handlePanelChange">
        <slot name="topo">
          <BkTabPanel
            :key="clusterData.id"
            :label="t('集群拓扑')"
            name="topo">
            <ClusterTopo
              v-if="activePanel === 'topo'"
              :cluster-id="clusterData.id"
              :cluster-role-node-group="clusterRoleNodeGroup"
              :cluster-type="clusterType"
              :db-type="dbType" />
          </BkTabPanel>
        </slot>
        <slot name="info">
          <BkTabPanel
            :key="clusterData.id"
            :label="t('基本信息')"
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
        <slot name="instance">
          <BkTabPanel
            :key="clusterData.id"
            :label="t('实例列表')"
            name="instance">
            <slot
              v-if="activePanel === 'instance'"
              name="instanceContent">
              <Instancelist
                :key="clusterData.id"
                :cluster-id="clusterData.id"
                :cluster-role-node-group="clusterRoleNodeGroup"
                :cluster-type="clusterType" />
            </slot>
          </BkTabPanel>
        </slot>
        <slot name="host">
          <BkTabPanel
            :key="clusterData.id"
            :label="t('主机列表')"
            name="host">
            <slot
              v-if="activePanel === 'host'"
              name="hostContent">
              <HostList
                :key="clusterData.id"
                :cluster-id="clusterData.id"
                :cluster-type="clusterType" />
            </slot>
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
            :key="clusterData.id"
            :label="t('单据记录')"
            name="record">
            <OperationRecord
              v-if="activePanel === 'record'"
              :id="clusterData.id"
              :key="clusterData.id" />
          </BkTabPanel>
        </slot>
      </BkTab>
    </div>
  </BkLoading>
</template>
<script lang="ts">
  import _ from 'lodash';
  import type { VNode } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';
  import { useRoute, useRouter } from 'vue-router';

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
  import { getMonitorUrls } from '@services/source/monitorGrafana';
  import type { ClusterListNode } from '@services/types';

  import { useUrlSearch } from '@hooks';

  import { clusterTypeInfos, ClusterTypes } from '@common/const';

  import BaseInfo from './components/BaseInfo.vue';
  import ClusterTopo from './components/cluster-topo/Index.vue';
  import HostList from './components/HostList.vue';
  import Instancelist from './components/InstanceList.vue';
  import MonitorDashboard from './components/MonitorDashboard.vue';
  import OperationRecord from './components/OperationRecord.vue';
  import {
    URL_CLUSTER_DETAIL_MEMO_KEY,
    URL_HOST_MEMO_KEY,
    URL_INSTANCE_MEMO_KEY,
    URL_RECORD_MEMO_KEY,
  } from './constants';

  export interface Props<C extends keyof ClusterTypeRelateClusterModel> {
    clusterData: ClusterTypeRelateClusterModel[C];
    clusterRoleNodeGroup: Record<string, ClusterListNode[]>;
    clusterType: C;
  }

  export interface Slots {
    host: () => VNode;
    hostContent: () => VNode;
    info: () => VNode;
    infoContent: () => VNode;
    instance: () => VNode;
    instanceContent: () => VNode;
    record: () => VNode;
    topo: () => VNode;
  }

  export interface ClusterTypeRelateClusterModel {
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

  const fixedTabList = ['topo', 'info', 'instance', 'host', 'record'];
</script>
<script setup lang="ts" generic="T extends keyof ClusterTypeRelateClusterModel">
  const props = defineProps<Props<T>>();
  defineSlots<Slots>();

  const { t } = useI18n();
  const route = useRoute();
  const router = useRouter();
  const { removeSearchParam } = useUrlSearch();

  const isFixedTab = ref(false);

  const rootRef = useTemplateRef('root');
  const activePanel = ref(String(route.query[URL_CLUSTER_DETAIL_MEMO_KEY]) || '');
  const tabcontentheight = ref('0');

  const dbType = computed(() => clusterTypeInfos[props.clusterData.cluster_type].dbType);
  const isLoading = computed(() => !isFixedTab.value && isPanelLoading.value);

  const calcTabContentHeight = _.throttle(() => {
    if (rootRef.value) {
      tabcontentheight.value = `${window.innerHeight - rootRef.value.getBoundingClientRect().top - 42}px`;
    }
  }, 60);

  const {
    data: monitorPanelList,
    loading: isPanelLoading,
    run: fetchMonitorUrls,
  } = useRequest(getMonitorUrls, {
    manual: true,
  });

  watch(
    () => props.clusterData,
    () => {
      if (props.clusterData) {
        fetchMonitorUrls({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          cluster_id: props.clusterData.id,
          cluster_type: props.clusterData.cluster_type,
        });
      }
    },
    {
      immediate: true,
    },
  );

  watch(
    route,
    () => {
      activePanel.value = String(route.query[URL_CLUSTER_DETAIL_MEMO_KEY] || '');
      isFixedTab.value = fixedTabList.includes(activePanel.value);
    },
    {
      immediate: true,
    },
  );

  const handlePanelChange = (value: string) => {
    router.replace({
      query: {
        ...removeSearchParam([URL_HOST_MEMO_KEY, URL_INSTANCE_MEMO_KEY, URL_RECORD_MEMO_KEY], false),
        [URL_CLUSTER_DETAIL_MEMO_KEY]: value,
      },
    });
    activePanel.value = value;
  };

  onMounted(() => {
    calcTabContentHeight();
    window.addEventListener('resize', calcTabContentHeight);
  });

  onBeforeUnmount(() => {
    window.removeEventListener('resize', calcTabContentHeight);
    // 延后执行
    setTimeout(() => {
      router.replace({
        query: {
          ...removeSearchParam([URL_HOST_MEMO_KEY, URL_INSTANCE_MEMO_KEY], false),
          [URL_CLUSTER_DETAIL_MEMO_KEY]: '',
        },
      });
    });
  });
</script>
<style lang="less">
  .cluster-detail-action-panel-box {
    min-height: 350px;

    .bk-tab-panel {
      padding: 0 20px;
    }

    .bk-tab-content {
      height: v-bind(tabcontentheight);
      padding: 0;
      flex: initial;
    }

    .content-wrapper {
      height: calc(100vh - 168px);
      padding: 0 24px;
      overflow: auto;
    }

    .cluster-specific-flag {
      color: #531dab !important;
      background: #f9f0ff !important;
    }
  }
</style>
