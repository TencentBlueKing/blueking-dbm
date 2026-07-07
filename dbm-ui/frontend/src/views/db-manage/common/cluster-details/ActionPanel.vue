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
              v-if="visitedPanels.has('topo')"
              v-show="activePanel === 'topo'"
              :cluster-data="clusterData"
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
              v-if="visitedPanels.has('info') && clusterData"
              name="infoContent">
              <BaseInfo
                v-show="activePanel === 'info'"
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
              v-if="visitedPanels.has('instance')"
              name="instanceContent">
              <Instancelist
                v-show="activePanel === 'instance'"
                :key="clusterData.id"
                :cluster-id="clusterData.id"
                :cluster-role-node-group="clusterRoleNodeGroup"
                :cluster-type="clusterType" />
            </slot>
          </BkTabPanel>
        </slot>
        <slot
          v-if="!clusterType.includes('k8s')"
          name="host">
          <BkTabPanel
            :key="clusterData.id"
            :label="t('主机列表')"
            name="host">
            <slot
              v-if="visitedPanels.has('host')"
              :active-panel="activePanel"
              name="hostContent">
              <HostList
                v-show="activePanel === 'host'"
                :key="clusterData.id"
                :active-panel="activePanel"
                :cluster-id="clusterData.id"
                :cluster-type="hostListRelatedClusterTypes" />
            </slot>
          </BkTabPanel>
        </slot>
        <slot
          v-if="!clusterType.includes('k8s')"
          name="paramConfig">
          <BkTabPanel
            :key="clusterData.id"
            :label="t('参数配置')"
            name="paramConfig">
            <ParamConfig
              v-if="activePanel === 'paramConfig' && clusterData.id"
              :cluster="clusterData" />
          </BkTabPanel>
        </slot>
        <template v-if="monitorPanelList && monitorPanelList.urls.length > 0">
          <BkTabPanel
            v-for="monirotItem in monitorPanelList.urls"
            :key="monirotItem.id"
            :label="monirotItem.view"
            :name="monirotItem.id">
            <MonitorDashboard
              v-if="visitedPanels.has(monirotItem.id)"
              v-show="activePanel === monirotItem.id"
              :key="clusterData.id"
              :url="monirotItem.url" />
          </BkTabPanel>
        </template>
        <slot
          v-if="isAbleSubscribe"
          name="alarmSubscription">
          <BkTabPanel
            :key="clusterData.id"
            :label="t('告警订阅')"
            name="alarmSubscription">
            <AlarmSubscription
              v-show="activePanel === 'alarmSubscription'"
              :cluster-type="clusterData.cluster_type"
              :data="clusterData" />
          </BkTabPanel>
        </slot>
        <slot
          v-if="!clusterType.includes('k8s')"
          name="record">
          <BkTabPanel
            :key="clusterData.id"
            :label="t('单据记录')"
            name="record">
            <TicketRecord
              :id="clusterData.id"
              :key="clusterData.id" />
          </BkTabPanel>
        </slot>
        <slot
          v-if="clusterType.includes('k8s')"
          name="operation">
          <BkTabPanel
            :key="clusterData.id"
            :label="t('操作记录')"
            name="operation">
            <K8SOperationRecord
              v-if="visitedPanels.has('operation')"
              v-show="activePanel === 'operation'"
              :id="clusterData.id"
              :key="clusterData.id"
              :cluster-data="k8sOperationRecordRelatedClusterData"
              :cluster-type="clusterType" />
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
  import OracleHaModel from '@services/model/oracle/oracle-ha';
  import OracleSingleModel from '@services/model/oracle/oracle-single';
  import PulsarModel from '@services/model/pulsar/pulsar';
  import QdrantHaModel from '@services/model/qdrant/qdrant-ha';
  import RedisModel from '@services/model/redis/redis';
  import RiakModel from '@services/model/riak/riak';
  import SqlserverHaModel from '@services/model/sqlserver/sqlserver-ha';
  import SqlserverSingleModel from '@services/model/sqlserver/sqlserver-single';
  import SurrealdbHaModel from '@services/model/surrealdb/surrealdb-ha';
  import SurrealdbSingleModel from '@services/model/surrealdb/surrealdb-single';
  import TendbClusterModel from '@services/model/tendbcluster/tendbcluster';
  import { getMonitorUrls } from '@services/source/monitorGrafana';
  import type { ClusterListNode } from '@services/types';

  import { useAlarmSubscribe, useUrlSearch } from '@hooks';

  import { clusterTypeInfos, ClusterTypes } from '@common/const';

  import AlarmSubscription from './components/AlarmSubscription.vue';
  import BaseInfo from './components/BaseInfo.vue';
  import ClusterTopo from './components/cluster-topo/Index.vue';
  import HostList from './components/HostList.vue';
  import Instancelist from './components/InstanceList.vue';
  import K8SOperationRecord from './components/k8s-operation-record/Index.vue';
  import MonitorDashboard from './components/MonitorDashboard.vue';
  import ParamConfig from './components/ParamConfig.vue';
  import TicketRecord from './components/TicketRecord.vue';
  import {
    URL_CLUSTER_DETAIL_MEMO_KEY,
    URL_HOST_MEMO_KEY,
    URL_INSTANCE_MEMO_KEY,
    URL_K8S_OPERATION_MEMO_KEY,
    URL_PARAM_CONF_TAB_KEY,
    URL_RECORD_MEMO_KEY,
  } from './constants';

  export interface Props<C extends keyof ClusterTypeRelateClusterModel> {
    clusterData: ClusterTypeRelateClusterModel[C];
    clusterRoleNodeGroup: Record<string, ClusterListNode[]>;
    clusterType: C;
  }

  export interface Slots {
    alarmSubscription: () => VNode;
    host: () => VNode;
    hostContent: (params: { activePanel: string }) => VNode;
    info: () => VNode;
    infoContent: () => VNode;
    instance: () => VNode;
    instanceContent: () => VNode;
    operation: () => VNode;
    paramConfig: () => VNode;
    record: () => VNode;
    topo: () => VNode;
  }

  export interface ClusterTypeRelateClusterModel {
    [ClusterTypes.DORIS]: DorisModel;
    [ClusterTypes.ES]: EsModel;
    [ClusterTypes.HDFS]: HdfsModel;
    [ClusterTypes.K8S_QDRANT_HA]: QdrantHaModel;
    [ClusterTypes.K8S_SURREALDB_HA]: SurrealdbHaModel;
    [ClusterTypes.K8S_SURREALDB_SINGLE]: SurrealdbSingleModel;
    [ClusterTypes.KAFKA]: KafkaModel;
    [ClusterTypes.MONGO_REPLICA_SET]: MongodbModel;
    [ClusterTypes.MONGO_SHARED_CLUSTER]: MongodbModel;
    [ClusterTypes.ORACLE_PRIMARY_STANDBY]: OracleHaModel;
    [ClusterTypes.ORACLE_SINGLE_NONE]: OracleSingleModel;
    [ClusterTypes.PREDIXY_REDIS_CLUSTER]: RedisModel;
    [ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER]: RedisModel;
    [ClusterTypes.PREDIXY_TENDISPLUS_INSTANCE]: RedisModel;
    [ClusterTypes.PULSAR]: PulsarModel;
    // [ClusterTypes.REDIS_CLUSTER]: RedisModel;
    [ClusterTypes.REDIS_INSTANCE]: RedisModel;
    // [ClusterTypes.REDIS]: RedisModel;
    [ClusterTypes.RIAK]: RiakModel;
    [ClusterTypes.SQLSERVER_HA]: SqlserverHaModel;
    [ClusterTypes.SQLSERVER_SINGLE]: SqlserverSingleModel;
    [ClusterTypes.TENDBCLUSTER]: TendbClusterModel;
    [ClusterTypes.TENDBHA]: TendbhaModel;
    [ClusterTypes.TENDBSINGLE]: TendbsingleModel;
    [ClusterTypes.TWEMPROXY_REDIS_INSTANCE]: RedisModel;
    [ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE]: RedisModel;
  }

  const fixedTabList = ['topo', 'info', 'instance', 'host', 'paramConfig', 'record', 'alarmSubscription'];
</script>
<script setup lang="ts" generic="T extends keyof ClusterTypeRelateClusterModel">
  const props = defineProps<Props<T>>();
  defineSlots<Slots>();

  const { t } = useI18n();
  const route = useRoute();
  const router = useRouter();
  const { removeSearchParam } = useUrlSearch();
  const { metricsMap } = useAlarmSubscribe();

  const isFixedTab = ref(false);

  const rootRef = useTemplateRef('root');
  const activePanel = ref(String(route.query[URL_CLUSTER_DETAIL_MEMO_KEY]) || '');
  const visitedPanels = reactive(new Set<string>());
  const tabcontentheight = ref('0');

  const dbType = computed(() => clusterTypeInfos[props.clusterData.cluster_type].dbType);
  const isLoading = computed(() => !isFixedTab.value && isPanelLoading.value);
  const isAbleSubscribe = computed(() => metricsMap.value[props.clusterData.cluster_type]?.list?.length > 0);

  type ExludeClusterTypes =
    ClusterTypes.K8S_SURREALDB_HA | ClusterTypes.K8S_SURREALDB_SINGLE | ClusterTypes.K8S_QDRANT_HA;
  const hostListRelatedClusterTypes = computed(
    () => props.clusterType as Exclude<keyof ClusterTypeRelateClusterModel, ExludeClusterTypes>,
  );
  const k8sOperationRecordRelatedClusterData = computed(
    () => props.clusterData as ClusterTypeRelateClusterModel[ExludeClusterTypes],
  );

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
      // 部分仪表盘暂时没数据，若请求会报错
      if (
        props.clusterData &&
        ![
          ClusterTypes.K8S_QDRANT_HA,
          ClusterTypes.K8S_SURREALDB_HA,
          ClusterTypes.K8S_SURREALDB_SINGLE,
          ClusterTypes.ORACLE_PRIMARY_STANDBY,
          ClusterTypes.ORACLE_SINGLE_NONE,
        ].includes(props.clusterData.cluster_type)
      ) {
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
      if (activePanel.value) {
        visitedPanels.add(activePanel.value);
      }
    },
    {
      immediate: true,
    },
  );

  const handlePanelChange = (value: string) => {
    router.replace({
      query: {
        ...removeSearchParam(
          [
            URL_HOST_MEMO_KEY,
            URL_INSTANCE_MEMO_KEY,
            URL_PARAM_CONF_TAB_KEY,
            URL_RECORD_MEMO_KEY,
            URL_K8S_OPERATION_MEMO_KEY,
          ],
          false,
        ),
        [URL_CLUSTER_DETAIL_MEMO_KEY]: value,
      },
    });
    activePanel.value = value;
    visitedPanels.add(value);
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
      padding: 0 24px;
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
