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
  <BkDialog
    class="dbm-instance-selector"
    :close-icon="false"
    :draggable="false"
    :esc-close="false"
    :is-show="isShow"
    :quick-close="false"
    width="80%"
    @closed="handleClose">
    <BkResizeLayout
      :border="false"
      collapsible
      initial-divide="320px"
      :max="360"
      :min="320"
      placement="right">
      <template #main>
        <PanelTab
          v-model="panelTabActive"
          :disabled="!isEmpty && unqiuePanelValue"
          :hide-manual-input="hideManualInput"
          :panel-list="panelList"
          :unqiue-panel-tips="unqiuePanelTips"
          @change="handleChangePanel" />
        <Component
          :is="renderCom"
          :key="panelTabActive"
          :active-panel-id="panelTabActive"
          :check-instances="activePanelObj?.manualConfig?.checkInstances"
          :count-func="activePanelObj?.topoConfig?.countFunc"
          :disabled-row-config="activePanelObj?.tableConfig?.disabledRowConfig"
          :filter-cluster-id="activePanelObj?.topoConfig?.filterClusterId"
          :firsr-column="activePanelObj?.tableConfig?.firsrColumn"
          :get-table-list="activePanelObj?.tableConfig?.getTableList"
          :get-topo-list="activePanelObj?.topoConfig?.getTopoList"
          :is-remote-pagination="activePanelObj?.tableConfig?.isRemotePagination"
          :last-values="lastValues"
          :manual-config="activePanelObj?.manualConfig"
          :role-filter-list="activePanelObj?.tableConfig?.roleFilterList"
          :status-filter="activePanelObj?.tableConfig?.statusFilter"
          :table-setting="tableSettings"
          :topo-alert-content="activePanelObj?.topoConfig?.topoAlertContent"
          :total-count-func="activePanelObj?.topoConfig?.totalCountFunc"
          @change="handleChange" />
      </template>
      <template #aside>
        <PreviewResult
          :active-panel-id="panelTabActive"
          :display-key="activePanelObj?.previewConfig?.displayKey"
          :get-table-list="activePanelObj?.tableConfig?.getTableList"
          :last-values="lastValues"
          :show-title="activePanelObj?.previewConfig?.showTitle"
          :title-map="previewTitleMap"
          @change="handleChange" />
      </template>
    </BkResizeLayout>
    <template #footer>
      <span
        v-bk-tooltips="{
          content: t('请选择实例'),
          disabled: !isEmpty,
        }"
        class="inline-block">
        <BkButton
          class="w-88"
          :disabled="isEmpty"
          theme="primary"
          @click="handleSubmit">
          {{ t('确定') }}
        </BkButton>
      </span>
      <BkButton
        class="ml8 w-88"
        @click="handleCancel">
        {{ t('取消') }}
      </BkButton>
    </template>
  </BkDialog>
</template>

<script lang="ts">
  import type { InjectionKey, Ref } from 'vue';

  import TendbclusterMachineModel from '@services/model/tendbcluster/tendbcluster-machine';
  import type { ListBase } from '@services/types';

  import { t } from '@locales/index';

  export interface IValue {
    [key: string]: any;
    bk_cloud_id: number;
    bk_cloud_name: string;
    bk_host_id: number;
    cluster_id: number;
    cluster_name: string;
    cluster_type: string;
    db_module_id: number;
    db_module_name: string;
    id: number;
    ip: string;
    port: number;
    instance_address: string;
    status?: string;
    host_info?: any;
    master_domain: string;
    related_instances?: {
      instance: string;
      status: string;
    }[];
    spec_config?: TendbclusterMachineModel['spec_config'];
    role: string;
  }

  export type InstanceSelectorValues<T> = Record<string, T[]>;

  export const activePanelInjectionKey: InjectionKey<Ref<string>> = Symbol('activePanel');

  const getSettings = (role?: string) => ({
    fields: [
      {
        label: role ? role.charAt(0).toUpperCase() + role.slice(1) : t('实例'),
        field: 'instance_address',
        disabled: true,
      },
      {
        label: t('角色'),
        field: 'role',
      },
      {
        label: t('实例状态'),
        field: 'status',
      },
      {
        label: t('管控区域'),
        field: 'bk_cloud_id',
      },
      {
        label: t('Agent状态'),
        field: 'alive',
      },
      {
        label: t('主机名称'),
        field: 'host_name',
      },
      {
        label: t('OS名称'),
        field: 'os_name',
      },
      {
        label: t('所属云厂商'),
        field: 'cloud_vendor',
      },
      {
        label: t('OS类型'),
        field: 'os_type',
      },
      {
        label: t('主机ID'),
        field: 'host_id',
      },
      {
        label: 'Agent ID',
        field: 'agent_id',
      },
    ],
    checked: ['instance_address', 'role', 'status', 'cloud_area', 'alive', 'host_name', 'os_name'],
  });
</script>

<script setup lang="ts" generic="T extends IValue">
  import _ from 'lodash';

  import MongodbModel from '@services/model/mongodb/mongodb';
  import { checkMongoInstances, checkMysqlInstances, checkRedisInstances } from '@services/source/instances';
  import { getMongoInstancesList, getMongoTopoList } from '@services/source/mongodb';
  import { queryClusters as queryMysqlCluster } from '@services/source/mysqlCluster';
  import { getRedisClusterList, getRedisMachineList } from '@services/source/redis';
  import {
    getHaClusterWholeList as getSqlServerHaCluster,
    getSqlServerInstanceList,
  } from '@services/source/sqlserveHaCluster';
  import {
    getSingleClusterList,
    getSqlServerInstanceList as getSqlServerSingleInstanceList,
  } from '@services/source/sqlserverSingleCluster';
  import {
    getTendbClusterFlatList as getTendbClusterList,
    getTendbclusterInstanceList,
    getTendbclusterMachineList,
  } from '@services/source/tendbcluster';
  import { getTendbhaFlatList as getTendbhaList, getTendbhaInstanceList } from '@services/source/tendbha';
  import {
    getTendbsingleFlatList as getTendbsingleList,
    getTendbsingleInstanceList,
  } from '@services/source/tendbsingle';

  import { ClusterTypes } from '@common/const';

  import ManualInputContent from './components/common/manual-content/Index.vue';
  import ManualInputHostContent from './components/common/manual-content-host/Index.vue';
  import PanelTab from './components/common/PanelTab.vue';
  import PreviewResult from './components/common/preview-result/Index.vue';
  import MongoClusterContent from './components/mongo/Index.vue';
  import MysqlContent from './components/mysql/Index.vue';
  import RedisContent from './components/redis/Index.vue';
  import RenderRedisHost from './components/redis-host/Index.vue';
  import SqlServerContent from './components/sqlserver/Index.vue';
  import TendbClusterContent from './components/tendb-cluster/Index.vue';
  import TendbClusterHostContent from './components/tendb-cluster-host/Index.vue';

  export type TableSetting = ReturnType<typeof getSettings>;

  export type PanelListType = {
    name: string;
    id: string;
    topoConfig?: {
      topoAlertContent?: Element;
      filterClusterId?: number;
      getTopoList?: (params: any) => Promise<any[]>;
      totalCountFunc?: (data: any) => number;
      countFunc?: (data: any) => number;
    };
    tableConfig?: {
      isRemotePagination?: boolean;
      columnsChecked?: string[];
      firsrColumn?: {
        label: string;
        field: string;
        role?: string; // 接口过滤
      };
      roleFilterList?: {
        list: { text: string; value: string }[];
      };
      disabledRowConfig?: {
        handler: (data: any) => boolean;
        tip?: string;
      };
      multiple?: boolean;
      getTableList?: (params: any) => Promise<any>;
      statusFilter?: (data: any) => boolean;
    };
    manualConfig?: {
      checkType: 'ip' | 'instance';
      checkKey: keyof IValue;
      activePanelId?: string;
      checkInstances?: (params: any) => Promise<any[] | ListBase<any[]>>;
    };
    previewConfig?: {
      displayKey?: keyof IValue;
      showTitle?: boolean;
      title?: string;
    };
    content?: any;
  }[];

  type PanelListItem = PanelListType[number];

  type RedisModel = ServiceReturnType<typeof getRedisClusterList>[number];
  type RedisHostModel = ServiceReturnType<typeof getRedisMachineList>['results'][number];

  interface Props {
    clusterTypes: (ClusterTypes | 'TendbClusterHost' | 'RedisHost' | 'mongoCluster')[];
    tabListConfig?: Record<string, PanelListType>;
    selected?: InstanceSelectorValues<T>;
    unqiuePanelValue?: boolean;
    unqiuePanelTips?: string;
    hideManualInput?: boolean;
  }

  interface Emits {
    (e: 'change', value: NonNullable<Props['selected']>): void;
    (e: 'cancel'): void;
  }

  const props = withDefaults(defineProps<Props>(), {
    tabListConfig: undefined,
    selected: undefined,
    unqiuePanelValue: false,
    unqiuePanelTips: t('仅可选择一种实例类型'),
    hideManualInput: false,
  });

  const emits = defineEmits<Emits>();

  defineOptions({
    name: 'InstanceSelector',
  });

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const tabListMap: Record<string, PanelListType> = {
    [ClusterTypes.REDIS]: [
      {
        id: 'redis',
        name: t('Redis 主库主机'),
        topoConfig: {
          getTopoList: getRedisClusterList,
          countFunc: (item: RedisModel) => item.redisMasterCount,
          totalCountFunc: (dataList: RedisModel[]) => {
            const ipSet = new Set<string>();
            dataList.forEach((dataItem) => dataItem.redis_master.forEach((masterItem) => ipSet.add(masterItem.ip)));
            return ipSet.size;
          },
        },
        tableConfig: {
          getTableList: getRedisMachineList,
          firsrColumn: {
            label: 'master Ip',
            role: 'redis_master',
            field: 'ip',
          },
          columnsChecked: ['ip', 'cloud_area', 'status', 'host_name', 'os_name'],
          statusFilter: (data: RedisHostModel) => !data.isMasterFailover,
          isRemotePagination: true,
        },
        previewConfig: {
          displayKey: 'ip',
          showTitle: false,
        },
        content: RedisContent,
      },
      {
        id: 'manualInput',
        name: t('手动输入'),
        tableConfig: {
          getTableList: getRedisMachineList,
          firsrColumn: {
            label: 'master Ip',
            role: 'redis_master',
            field: 'ip',
          },
          columnsChecked: ['ip', 'cloud_area', 'status', 'host_name', 'os_name'],
          statusFilter: (data: RedisHostModel) => !data.isMasterFailover,
          isRemotePagination: false,
        },
        manualConfig: {
          checkInstances: checkRedisInstances,
          checkType: 'ip',
          checkKey: 'ip',
          activePanelId: 'redis',
        },
        previewConfig: {
          displayKey: 'ip',
          showTitle: false,
        },
        content: ManualInputContent,
      },
    ],
    [ClusterTypes.TENDBCLUSTER]: [
      {
        id: 'tendbcluster',
        name: 'Tendb Cluster',
        topoConfig: {
          getTopoList: getTendbClusterList,
        },
        tableConfig: {
          getTableList: getTendbclusterInstanceList,
          firsrColumn: {
            label: 'remote_master',
            field: 'instance_address',
            role: 'remote_master',
          },
        },
        content: TendbClusterContent,
      },
      {
        id: 'manualInput',
        name: t('手动输入'),
        tableConfig: {
          getTableList: getTendbclusterInstanceList,
          firsrColumn: {
            label: 'remote_master',
            field: 'instance_address',
            role: 'remote_master',
          },
        },
        manualConfig: {
          checkInstances: checkMysqlInstances,
          checkType: 'instance',
          checkKey: 'instance_address',
          activePanelId: 'tendbcluster',
        },
        content: ManualInputContent,
      },
    ],
    [ClusterTypes.TENDBSINGLE]: [
      {
        id: 'tendbsingle',
        name: t('Mysql 单节点'),
        topoConfig: {
          getTopoList: getTendbsingleList,
        },
        tableConfig: {
          getTableList: getTendbsingleInstanceList,
          firsrColumn: {
            label: '',
            field: 'instance_address',
            role: '',
          },
        },
        content: MysqlContent,
      },
      {
        id: 'manualInput',
        name: t('手动输入'),
        tableConfig: {
          getTableList: getTendbsingleInstanceList,
          firsrColumn: {
            label: '',
            field: 'instance_address',
            role: '',
          },
        },
        manualConfig: {
          checkInstances: checkMysqlInstances,
          checkType: 'instance',
          checkKey: 'instance_address',
          activePanelId: 'tendbsingle',
        },
        content: ManualInputContent,
      },
    ],
    [ClusterTypes.TENDBHA]: [
      {
        id: 'tendbha',
        name: t('Mysql 主从'),
        topoConfig: {
          getTopoList: getTendbhaList,
        },
        tableConfig: {
          getTableList: getTendbhaInstanceList,
          firsrColumn: {
            label: 'master',
            field: 'instance_address',
            role: 'master',
          },
        },
        content: MysqlContent,
      },
      {
        id: 'manualInput',
        name: t('手动输入'),
        tableConfig: {
          getTableList: getTendbhaInstanceList,
          firsrColumn: {
            label: 'master',
            field: 'instance_address',
            role: 'master',
          },
        },
        manualConfig: {
          checkInstances: checkMysqlInstances,
          checkType: 'instance',
          checkKey: 'instance_address',
          activePanelId: 'tendbha',
        },
        content: ManualInputContent,
      },
    ],
    mongoCluster: [
      {
        id: 'mongoCluster',
        name: t('Mongo 主库主机'),
        topoConfig: {
          getTopoList: getMongoTopoList,
          countFunc: (item: MongodbModel) => item.instanceCount,
        },
        tableConfig: {
          getTableList: getMongoInstancesList,
          firsrColumn: {
            label: 'IP',
            field: 'ip',
          },
        },
        previewConfig: {
          displayKey: 'ip',
        },
        content: MongoClusterContent,
      },
      {
        id: 'manualInput',
        name: t('手动输入'),
        tableConfig: {
          getTableList: getTendbclusterInstanceList,
          firsrColumn: {
            label: 'IP',
            field: 'ip',
          },
        },
        manualConfig: {
          checkInstances: checkMongoInstances,
          checkType: 'instance',
          checkKey: 'instance_address',
          activePanelId: 'mongocluster',
        },
        previewConfig: {
          displayKey: 'ip',
        },
        content: ManualInputContent,
      },
    ],
    TendbClusterHost: [
      {
        id: 'TendbClusterHost',
        name: 'TendbCluster',
        topoConfig: {
          getTopoList: queryMysqlCluster,
          countFunc: (clusterItem: { remote_db: { ip: string }[] }) => {
            const ipList = clusterItem.remote_db.map((hostItem) => hostItem.ip);
            return new Set(ipList).size;
          },
        },
        tableConfig: {
          getTableList: getTendbclusterMachineList,
          firsrColumn: {
            label: t('主库主机'),
            field: 'ip',
            role: 'remote_master',
          },
          columnsChecked: ['ip', 'related_instances', 'cloud_area', 'alive', 'host_name', 'os_name'],
        },
        previewConfig: {
          displayKey: 'ip',
        },
        content: TendbClusterHostContent,
      },
      {
        id: 'manualInput',
        name: t('手动输入'),
        tableConfig: {
          getTableList: getTendbclusterMachineList,
          firsrColumn: {
            label: 'remote_master',
            field: 'ip',
            role: 'remote_master',
          },
          columnsChecked: ['ip', 'related_instances', 'cloud_area', 'alive', 'host_name', 'os_name'],
        },
        manualConfig: {
          checkInstances: getTendbclusterMachineList,
          checkType: 'ip',
          checkKey: 'ip',
          activePanelId: 'TendbClusterHost',
        },
        previewConfig: {
          displayKey: 'ip',
        },
        content: ManualInputHostContent,
      },
    ],
    RedisHost: [
      {
        id: 'RedisHost',
        name: t('Redis 主从'),
        topoConfig: {
          getTopoList: getRedisClusterList,
          countFunc: (clusterItem: { redis_master: { ip: string }[] }) => {
            const ipList = clusterItem.redis_master.map((hostItem) => hostItem.ip);
            return new Set(ipList).size;
          },
        },
        tableConfig: {
          getTableList: getRedisMachineList,
          firsrColumn: {
            label: t('主库主机'),
            field: 'ip',
            role: 'redis_master',
          },
          columnsChecked: ['ip', 'cloud_area', 'alive', 'host_name', 'os_name'],
        },
        previewConfig: {
          displayKey: 'ip',
        },
        content: RenderRedisHost,
      },
      {
        id: 'manualInput',
        name: t('手动输入'),
        tableConfig: {
          getTableList: getRedisMachineList,
          firsrColumn: {
            label: t('主库主机'),
            field: 'ip',
            role: 'redis_master',
          },
          columnsChecked: ['ip', 'cloud_area', 'alive', 'host_name', 'os_name'],
        },
        manualConfig: {
          checkInstances: getRedisMachineList,
          checkType: 'ip',
          checkKey: 'ip',
          activePanelId: 'RedisHost',
        },
        previewConfig: {
          displayKey: 'ip',
        },
        content: ManualInputHostContent,
      },
    ],
    [ClusterTypes.SQLSERVER_HA]: [
      {
        id: ClusterTypes.SQLSERVER_HA,
        name: t('SqlServer 主从'),
        topoConfig: {
          getTopoList: getSqlServerHaCluster,
          countFunc: (item: ServiceReturnType<typeof getSqlServerHaCluster>[number]) => item.masters.length,
        },
        tableConfig: {
          getTableList: getSqlServerInstanceList,
          // firsrColumn: {
          //   label: 'backend_master',
          //   field: 'instance_address',
          //   role: 'backend_master',
          // },
        },
        content: SqlServerContent,
      },
      {
        id: 'manualInput',
        name: t('手动输入'),
        tableConfig: {
          getTableList: getSqlServerInstanceList,
          firsrColumn: {
            label: 'remote_master',
            field: 'instance_address',
          },
        },
        manualConfig: {
          checkInstances: checkMysqlInstances,
          checkType: 'instance',
          checkKey: 'instance_address',
          activePanelId: ClusterTypes.SQLSERVER_HA,
        },
        content: ManualInputContent,
      },
    ],
    [ClusterTypes.SQLSERVER_SINGLE]: [
      {
        id: ClusterTypes.SQLSERVER_SINGLE,
        name: t('SqlServer 单节点'),
        topoConfig: {
          getTopoList: (params: ServiceParameters<typeof getSingleClusterList>) =>
            getSingleClusterList(params).then((data) => data.results),
          countFunc: () => 1,
        },
        tableConfig: {
          getTableList: getSqlServerSingleInstanceList,
        },
        content: SqlServerContent,
      },
      {
        id: 'manualInput',
        name: t('手动输入'),
        tableConfig: {
          getTableList: getSqlServerSingleInstanceList,
          firsrColumn: {
            label: 'remote_master',
            field: 'instance_address',
          },
        },
        manualConfig: {
          checkInstances: checkMysqlInstances,
          checkType: 'instance',
          checkKey: 'instance_address',
          activePanelId: ClusterTypes.SQLSERVER_SINGLE,
        },
        content: ManualInputContent,
      },
    ],
  };

  const panelTabActive = ref<string>('');
  const activePanelObj = shallowRef<PanelListItem>();

  const lastValues = reactive<NonNullable<Props['selected']>>({});

  provide(activePanelInjectionKey, panelTabActive);

  const clusterTabListMap = computed<Record<string, PanelListType>>(() => {
    if (props.tabListConfig) {
      Object.keys(props.tabListConfig).forEach((type) => {
        const configArr = props.tabListConfig?.[type];
        if (configArr) {
          configArr.forEach((config, index) => {
            let objItem = {};
            const baseObj = tabListMap[type][index];
            if (baseObj) {
              objItem = {
                ..._.merge(baseObj, config),
              };
            } else {
              objItem = baseObj;
            }
            tabListMap[type][index] = objItem as PanelListItem;
          });
        }
      });
    }
    return tabListMap;
  });

  const previewTitleMap = computed(() => {
    const titleMap = Object.keys(clusterTabListMap.value).reduce(
      (results, key) => {
        Object.assign(results, {
          [key]: clusterTabListMap.value[key][0].previewConfig?.title ?? '',
        });
        return results;
      },
      {} as Record<string, string>,
    );
    titleMap.manualInput = t('手动输入');
    return titleMap;
  });

  const panelList = computed<PanelListType>(() => {
    const pageList = _.flatMap(props.clusterTypes.map((type) => tabListMap[type]));
    if (pageList.length < 3) {
      return pageList;
    }
    // 两个及以上的tabPanel，手动输入tab取最后一个tab
    const newPageList: PanelListType = [];
    pageList.forEach((item, index) => {
      if (index % 2 === 0 || index === pageList.length - 1) {
        newPageList.push(item);
      }
    });
    return newPageList;
  });

  const tableSettings = computed(() => {
    const setting = getSettings(activePanelObj.value?.tableConfig?.firsrColumn?.label);
    const checked = activePanelObj?.value?.tableConfig?.columnsChecked;
    if (checked) {
      // 自定义列项
      setting.checked = checked;
    }
    return setting;
  });

  const isEmpty = computed(() => Object.values(lastValues).every((values) => values.length < 1));
  const renderCom = computed(() => (activePanelObj.value ? activePanelObj.value.content : 'div'));

  let isInnerChange = false;

  watch(
    () => isShow,
    (show) => {
      if (!show) {
        return;
      }
      if (isInnerChange) {
        isInnerChange = false;
        return;
      }
      if (props.selected) {
        Object.assign(lastValues, props.selected);
      }
      if (
        props.clusterTypes.length > 0 &&
        (!panelTabActive.value || !props.clusterTypes.includes(panelTabActive.value as Props['clusterTypes'][number]))
      ) {
        [panelTabActive.value] = props.clusterTypes as string[];
        [activePanelObj.value] = clusterTabListMap.value[panelTabActive.value];
      }
    },
    {
      immediate: true,
    },
  );

  const handleChangePanel = (obj: PanelListItem) => {
    activePanelObj.value = obj;
  };

  const handleChange = (values: Props['selected']) => {
    Object.assign(lastValues, values);
  };

  const handleSubmit = () => {
    emits('change', lastValues);
    handleClose();
  };

  const handleCancel = () => {
    emits('cancel');
    handleClose();
  };

  const handleClose = () => {
    isShow.value = false;
  };
</script>
<style lang="less">
  .dbm-instance-selector {
    display: block;
    width: 80%;
    max-width: 1600px;
    min-width: 1200px;

    .bk-modal-header {
      display: none;
    }

    .bk-dialog-content {
      padding: 0;
      margin: 0;
    }
  }
</style>
