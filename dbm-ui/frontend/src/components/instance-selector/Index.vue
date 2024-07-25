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
          :panel-list="panelList"
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

  import SpiderMachineModel from '@services/model/spider/spiderMachine';
  import type { ListBase } from '@services/types';

  import { t } from '@locales/index';

  export interface IValue {
    [key: string]: any;
    bk_cloud_id: number;
    bk_cloud_name: string;
    bk_host_id: number;
    cluster_id?: number;
    cluster_name?: string;
    cluster_type: string;
    create_at: string;
    db_module_id: number;
    db_module_name: string;
    host_info: any;
    id: number;
    instance_address: string;
    instance_role: string;
    ip: string;
    port: number;
    status?: string;
    machine_type: string;
    master_domain: string;
    related_clusters?: SpiderMachineModel['related_clusters'];
    related_instances?: SpiderMachineModel['related_instances'];
    spec_config?: SpiderMachineModel['spec_config'];
    spec_id?: number;
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
  import {
    queryClusters as getMysqlClusterList,
    queryClusters as queryMysqlCluster,
  } from '@services/source/mysqlCluster';
  import { getRedisClusterList, getRedisMachineList } from '@services/source/redis';
  import { getSpiderInstanceList, getSpiderMachineList } from '@services/source/spider';
  import {
    getHaClusterWholeList as getSqlServerHaCluster,
    getSqlServerInstanceList,
  } from '@services/source/sqlserveHaCluster';
  import { getTendbhaInstanceList, getTendbhaMachineList } from '@services/source/tendbha';
  import { getTendbsingleInstanceList } from '@services/source/tendbsingle';

  import { ClusterTypes } from '@common/const';

  import ManualInputContent from './components/common/manual-content/Index.vue';
  import ManualInputHostContent from './components/common/manual-content-host/Index.vue';
  import PanelTab from './components/common/PanelTab.vue';
  import PreviewResult from './components/common/preview-result/Index.vue';
  import MongoClusterContent from './components/mongo/Index.vue';
  import MysqlContent from './components/mysql/Index.vue';
  import RedisContent from './components/redis/Index.vue';
  import RenderRedisHost from './components/redis-host/Index.vue';
  import SqlServerContent from './components/sql-server/Index.vue';
  import TendbClusterContent from './components/tendb-cluster/Index.vue';
  import TendbClusterHostContent from './components/tendb-cluster-host/Index.vue';
  import TendbhaHostContent from './components/tendb-ha-host/Index.vue';

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
    clusterTypes: (ClusterTypes | 'TendbhaHost' | 'TendbClusterHost')[];
    tabListConfig?: Record<string, PanelListType>;
    selected?: InstanceSelectorValues<T>;
  }

  interface Emits {
    (e: 'change', value: NonNullable<Props['selected']>): void;
    (e: 'cancel'): void;
  }

  const props = withDefaults(defineProps<Props>(), {
    tabListConfig: undefined,
    selected: undefined,
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
        name: t('主库主机'),
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
        name: t('主库主机'),
        topoConfig: {
          getTopoList: getMysqlClusterList,
        },
        tableConfig: {
          getTableList: getSpiderInstanceList,
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
          getTableList: getSpiderInstanceList,
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
        name: t('单节点'),
        topoConfig: {
          getTopoList: getMysqlClusterList,
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
        name: t('主从'),
        topoConfig: {
          getTopoList: getMysqlClusterList,
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
    [ClusterTypes.MONGOCLUSTER]: [
      {
        id: 'mongocluster',
        name: t('主库主机'),
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
          getTableList: getSpiderInstanceList,
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
    TendbhaHost: [
      {
        id: 'TendbhaHost',
        name: t('主库主机'),
        topoConfig: {
          getTopoList: getMysqlClusterList,
        },
        tableConfig: {
          getTableList: getTendbhaMachineList,
          firsrColumn: {
            label: t('主库主机'),
            field: 'ip',
            role: 'master',
          },
          columnsChecked: ['ip', 'related_instances', 'cloud_area', 'alive', 'host_name', 'os_name'],
        },
        previewConfig: {
          displayKey: 'ip',
        },
        content: TendbhaHostContent,
      },
      {
        id: 'manualInput',
        name: t('手动输入'),
        tableConfig: {
          getTableList: getTendbhaMachineList,
          firsrColumn: {
            label: t('主库主机'),
            field: 'ip',
            role: 'master',
          },
          columnsChecked: ['ip', 'related_instances', 'cloud_area', 'alive', 'host_name', 'os_name'],
        },
        manualConfig: {
          checkInstances: getTendbhaMachineList,
          checkType: 'ip',
          checkKey: 'ip',
          activePanelId: 'TendbhaHost',
        },
        previewConfig: {
          displayKey: 'ip',
        },
        content: ManualInputHostContent,
      },
    ],
    TendbClusterHost: [
      {
        id: 'TendbClusterHost',
        name: t('主库主机'),
        topoConfig: {
          getTopoList: queryMysqlCluster,
          countFunc: (clusterItem: { remote_db: { ip: string }[] }) => {
            const ipList = clusterItem.remote_db.map((hostItem) => hostItem.ip);
            return new Set(ipList).size;
          },
        },
        tableConfig: {
          getTableList: getSpiderMachineList,
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
          getTableList: getSpiderMachineList,
          firsrColumn: {
            label: t('主库主机'),
            field: 'ip',
            role: 'remote_master',
          },
          columnsChecked: ['ip', 'related_instances', 'cloud_area', 'alive', 'host_name', 'os_name'],
        },
        manualConfig: {
          checkInstances: getSpiderMachineList,
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
        name: t('主库主机'),
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
        name: t('主库主机'),
        topoConfig: {
          getTopoList: getSqlServerHaCluster,
          countFunc: (item: ServiceReturnType<typeof getSqlServerHaCluster>[number]) => item.masters.length,
        },
        tableConfig: {
          getTableList: getSqlServerInstanceList,
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
  const renderCom = computed(() => activePanelObj.value?.content);

  watch(
    () => props.clusterTypes,
    (types) => {
      if (types) {
        const activeObj = clusterTabListMap.value[types[0]];
        [activePanelObj.value] = activeObj;
        panelTabActive.value = activeObj[0].id;
      }
    },
    {
      immediate: true,
      deep: true,
    },
  );

  watch(isShow, (show) => {
    if (show && props.selected) {
      Object.assign(lastValues, props.selected);
    }
  });

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
