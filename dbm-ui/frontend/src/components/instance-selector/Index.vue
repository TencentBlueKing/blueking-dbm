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
          :last-values="lastValues"
          :manual-config="activePanelObj?.manualConfig"
          :multiple="activePanelObj?.tableConfig?.multiple"
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
      <span class="mr24">
        <slot
          v-if="slots.submitTips"
          :host-list="lastHostList"
          name="submitTips" />
      </span>
      <span v-bk-tooltips="submitButtonDisabledInfo.tooltips">
        <BkButton
          class="w-88"
          :disabled="submitButtonDisabledInfo.disabled"
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
  import { type InjectionKey, type Ref, type VNode } from 'vue';

  import TendbclusterMachineModel from '@services/model/tendbcluster/tendbcluster-machine';
  import type { HostInfo, ListBase } from '@services/types';

  import { t } from '@locales/index';

  export interface IValue {
    [key: string]: any;
    bk_cloud_id: number;
    bk_cloud_name: string;
    bk_host_id: number;
    cluster_id: number;
    cluster_name?: string;
    cluster_type: string;
    create_at: string;
    db_module_id: number;
    db_module_name: string;
    host_info: HostInfo;
    id: number;
    instance_address: string;
    instance_role: string;
    ip: string;
    machine_type: string;
    master_domain: string;
    name: string;
    port: number;
    related_clusters: {
      cluster_type: string;
      db_module_id: number;
      id: number;
      immute_domain: string;
      master_domain: string;
      name: string;
      region: string;
    }[];
    related_instances: {
      admin_port: number;
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      bk_instance_id: number;
      cluster_id: number;
      instance: string;
      ip: string;
      name: string;
      phase: string;
      port: number;
      status: string;
    }[];
    role: string;
    shard: string;
    spec_config: TendbclusterMachineModel['spec_config'];
    spec_id: number;
    status: string;
    version: string;
  }

  export type InstanceSelectorValues<T> = Record<string, T[]>;

  export const activePanelInjectionKey: InjectionKey<Ref<string>> = Symbol('activePanel');

  const getSettings = (role?: string) => ({
    checked: ['instance_address', 'role', 'status', 'cloud_area', 'alive', 'host_name', 'os_name'],
    fields: [
      {
        disabled: true,
        field: 'instance_address',
        label: role ? role.charAt(0).toUpperCase() + role.slice(1) : t('实例'),
      },
      {
        field: 'role',
        label: t('角色'),
      },
      {
        field: 'status',
        label: t('实例状态'),
      },
      {
        field: 'bk_cloud_id',
        label: t('管控区域'),
      },
      {
        field: 'alive',
        label: t('Agent状态'),
      },
      {
        field: 'host_name',
        label: t('主机名称'),
      },
      {
        field: 'os_name',
        label: t('OS名称'),
      },
      {
        field: 'cloud_vendor',
        label: t('所属云厂商'),
      },
      {
        field: 'os_type',
        label: t('OS类型'),
      },
      {
        field: 'host_id',
        label: t('主机ID'),
      },
      {
        field: 'agent_id',
        label: 'Agent ID',
      },
    ],
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
  import {
    getTendbhaFlatList as getTendbhaList,
    getTendbhaInstanceList,
    getTendbhaMachineList,
  } from '@services/source/tendbha';
  import {
    getTendbsingleFlatList as getTendbsingleList,
    getTendbsingleInstanceList,
    getTendbSingleMachineList,
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
  import TendbHaHostContent from './components/tendb-ha-host/Index.vue';
  import TendbSingleHostContent from './components/tendb-single-host/Index.vue';

  export type TableSetting = ReturnType<typeof getSettings>;

  export type PanelListType = {
    content?: any;
    id: string;
    manualConfig?: {
      activePanelId?: string;
      checkInstances?: (params: any) => Promise<any[] | ListBase<any[]>>;
      checkKey: keyof IValue;
      checkType: 'ip' | 'instance';
      fieldFormat?: Record<string, Record<string, string>>;
    };
    name: string;
    previewConfig?: {
      displayKey?: keyof IValue;
      showTitle?: boolean;
      title?: string;
    };
    tableConfig?: {
      columnsChecked?: string[];
      disabledRowConfig?: {
        handler: (data: any) => boolean;
        tip?: string;
      };
      firsrColumn?: {
        field: string;
        label: string;
        role?: string; // 接口过滤
      };
      getTableList?: (params: any) => Promise<any>;
      multiple?: boolean;
      roleFilterList?: {
        list: { text: string; value: string }[];
      };
      statusFilter?: (data: any) => boolean;
    };
    topoConfig?: {
      countFunc?: (data: any) => number;
      filterClusterId?: number;
      getTopoList?: (params: any) => Promise<any[]>;
      topoAlertContent?: Element;
      totalCountFunc?: (data: any) => number;
    };
  }[];

  type PanelListItem = PanelListType[number];

  type RedisModel = ServiceReturnType<typeof getRedisClusterList>[number];
  type RedisHostModel = ServiceReturnType<typeof getRedisMachineList>['results'][number];

  type Props = {
    clusterTypes: (
      | ClusterTypes
      | 'TendbhaHost'
      | 'TendbClusterHost'
      | 'RedisHost'
      | 'mongoCluster'
      | 'TendbSingleHost'
    )[];
    disableDialogSubmitMethod?: (hostList: Array<string>) => string | boolean;
    hideManualInput?: boolean;
    onlyOneType?: boolean;
    selected?: InstanceSelectorValues<T>;
    tabListConfig?: Record<string, PanelListType>;
    unqiuePanelTips?: string;
    unqiuePanelValue?: boolean;
  };

  type Emits = {
    (e: 'change', value: NonNullable<Props['selected']>): void;
    (e: 'cancel'): void;
  };

  defineOptions({
    name: 'InstanceSelector',
  });

  const props = withDefaults(defineProps<Props>(), {
    disableDialogSubmitMethod: () => false,
    hideManualInput: false,
    onlyOneType: false,
    selected: undefined,
    tabListConfig: undefined,
    unqiuePanelTips: t('仅可选择一种实例类型'),
    unqiuePanelValue: false,
  });

  const emits = defineEmits<Emits>();

  const slots = defineSlots<{
    submitTips?: () => VNode;
  }>();

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const tabListMap: Record<string, PanelListType> = {
    [ClusterTypes.REDIS]: [
      {
        content: RedisContent,
        id: 'redis',
        name: t('Redis 主库主机'),
        previewConfig: {
          displayKey: 'ip',
          showTitle: false,
        },
        tableConfig: {
          columnsChecked: ['ip', 'role', 'cloud_area', 'status', 'host_name', 'os_name'],
          firsrColumn: {
            field: 'ip',
            label: 'master Ip',
            role: 'redis_master',
          },
          getTableList: getRedisMachineList,
          statusFilter: (data: RedisHostModel) => !data.isMasterFailover,
        },
        topoConfig: {
          countFunc: (item: RedisModel) => item.redisMasterCount,
          getTopoList: getRedisClusterList,
          totalCountFunc: (dataList: RedisModel[]) => {
            const ipSet = new Set<string>();
            dataList.forEach((dataItem) => dataItem.redis_master.forEach((masterItem) => ipSet.add(masterItem.ip)));
            return ipSet.size;
          },
        },
      },
      {
        content: ManualInputContent,
        id: 'manualInput',
        manualConfig: {
          activePanelId: 'redis',
          checkInstances: checkRedisInstances,
          checkKey: 'ip',
          checkType: 'ip',
          fieldFormat: {
            // column绑定的field
            role: {
              // 接口返回值->展示值
              master: 'redis_master',
              proxy: 'proxy',
              slave: 'redis_slave',
            },
          },
        },
        name: t('手动输入'),
        previewConfig: {
          displayKey: 'ip',
          showTitle: false,
        },
        tableConfig: {
          columnsChecked: ['ip', 'role', 'cloud_area', 'status', 'host_name', 'os_name'],
          firsrColumn: {
            field: 'ip',
            label: 'IP',
            role: 'redis_master',
          },
          getTableList: getRedisMachineList,
          statusFilter: (data: RedisHostModel) => !data.isMasterFailover,
        },
      },
    ],
    [ClusterTypes.SQLSERVER_HA]: [
      {
        content: SqlServerContent,
        id: ClusterTypes.SQLSERVER_HA,
        name: t('SqlServer 主从'),
        tableConfig: {
          getTableList: getSqlServerInstanceList,
          // firsrColumn: {
          //   label: 'backend_master',
          //   field: 'instance_address',
          //   role: 'backend_master',
          // },
        },
        topoConfig: {
          countFunc: (item: ServiceReturnType<typeof getSqlServerHaCluster>[number]) => item.masters.length,
          getTopoList: getSqlServerHaCluster,
        },
      },
      {
        content: ManualInputContent,
        id: 'manualInput',
        manualConfig: {
          activePanelId: ClusterTypes.SQLSERVER_HA,
          checkInstances: checkMysqlInstances,
          checkKey: 'instance_address',
          checkType: 'instance',
        },
        name: t('手动输入'),
        tableConfig: {
          firsrColumn: {
            field: 'instance_address',
            label: 'remote_master',
          },
          getTableList: getSqlServerInstanceList,
        },
      },
    ],
    [ClusterTypes.SQLSERVER_SINGLE]: [
      {
        content: SqlServerContent,
        id: ClusterTypes.SQLSERVER_SINGLE,
        name: t('SqlServer 单节点'),
        tableConfig: {
          getTableList: getSqlServerSingleInstanceList,
        },
        topoConfig: {
          countFunc: () => 1,
          getTopoList: (params: ServiceParameters<typeof getSingleClusterList>) =>
            getSingleClusterList(params).then((data) => data.results),
        },
      },
      {
        content: ManualInputContent,
        id: 'manualInput',
        manualConfig: {
          activePanelId: ClusterTypes.SQLSERVER_SINGLE,
          checkInstances: checkMysqlInstances,
          checkKey: 'instance_address',
          checkType: 'instance',
        },
        name: t('手动输入'),
        tableConfig: {
          firsrColumn: {
            field: 'instance_address',
            label: 'remote_master',
          },
          getTableList: getSqlServerSingleInstanceList,
        },
      },
    ],
    [ClusterTypes.TENDBCLUSTER]: [
      {
        content: TendbClusterContent,
        id: 'tendbcluster',
        name: 'Tendb Cluster',
        tableConfig: {
          firsrColumn: {
            field: 'instance_address',
            label: 'remote_master',
            role: 'remote_master',
          },
          getTableList: getTendbclusterInstanceList,
        },
        topoConfig: {
          getTopoList: getTendbClusterList,
        },
      },
      {
        content: ManualInputContent,
        id: 'manualInput',
        manualConfig: {
          activePanelId: 'tendbcluster',
          checkInstances: checkMysqlInstances,
          checkKey: 'instance_address',
          checkType: 'instance',
        },
        name: t('手动输入'),
        tableConfig: {
          firsrColumn: {
            field: 'instance_address',
            label: 'remote_master',
            role: 'remote_master',
          },
          getTableList: getTendbclusterInstanceList,
        },
      },
    ],
    [ClusterTypes.TENDBHA]: [
      {
        content: MysqlContent,
        id: 'tendbha',
        name: t('Mysql 主从'),
        tableConfig: {
          firsrColumn: {
            field: 'instance_address',
            label: 'master',
            role: 'master',
          },
          getTableList: getTendbhaInstanceList,
        },
        topoConfig: {
          getTopoList: getTendbhaList,
        },
      },
      {
        content: ManualInputContent,
        id: 'manualInput',
        manualConfig: {
          activePanelId: 'tendbha',
          checkInstances: checkMysqlInstances,
          checkKey: 'instance_address',
          checkType: 'instance',
        },
        name: t('手动输入'),
        tableConfig: {
          firsrColumn: {
            field: 'instance_address',
            label: 'master',
            role: 'master',
          },
          getTableList: getTendbhaInstanceList,
        },
      },
    ],
    [ClusterTypes.TENDBSINGLE]: [
      {
        content: MysqlContent,
        id: 'tendbsingle',
        name: t('Mysql 单节点'),
        tableConfig: {
          firsrColumn: {
            field: 'instance_address',
            label: '',
            role: '',
          },
          getTableList: getTendbsingleInstanceList,
        },
        topoConfig: {
          getTopoList: getTendbsingleList,
        },
      },
      {
        content: ManualInputContent,
        id: 'manualInput',
        manualConfig: {
          activePanelId: 'tendbsingle',
          checkInstances: checkMysqlInstances,
          checkKey: 'instance_address',
          checkType: 'instance',
        },
        name: t('手动输入'),
        tableConfig: {
          firsrColumn: {
            field: 'instance_address',
            label: '',
            role: '',
          },
          getTableList: getTendbsingleInstanceList,
        },
      },
    ],
    mongoCluster: [
      {
        content: MongoClusterContent,
        id: 'mongoCluster',
        name: t('Mongo 主库主机'),
        previewConfig: {
          displayKey: 'ip',
        },
        tableConfig: {
          firsrColumn: {
            field: 'ip',
            label: 'IP',
          },
          getTableList: getMongoInstancesList,
        },
        topoConfig: {
          countFunc: (item: MongodbModel) => item.instanceCount,
          getTopoList: getMongoTopoList,
        },
      },
      {
        content: ManualInputContent,
        id: 'manualInput',
        manualConfig: {
          activePanelId: 'mongocluster',
          checkInstances: checkMongoInstances,
          checkKey: 'instance_address',
          checkType: 'instance',
        },
        name: t('手动输入'),
        previewConfig: {
          displayKey: 'ip',
        },
        tableConfig: {
          firsrColumn: {
            field: 'ip',
            label: 'IP',
          },
          getTableList: getTendbclusterInstanceList,
        },
      },
    ],
    RedisHost: [
      {
        content: RenderRedisHost,
        id: 'RedisHost',
        name: t('Redis 主从'),
        previewConfig: {
          displayKey: 'ip',
        },
        tableConfig: {
          columnsChecked: ['ip', 'cloud_area', 'alive', 'host_name', 'os_name'],
          firsrColumn: {
            field: 'ip',
            label: t('主库主机'),
            role: 'redis_master',
          },
          getTableList: getRedisMachineList,
        },
        topoConfig: {
          countFunc: (clusterItem: { redis_master: { ip: string }[] }) => {
            const ipList = clusterItem.redis_master.map((hostItem) => hostItem.ip);
            return new Set(ipList).size;
          },
          getTopoList: getRedisClusterList,
        },
      },
      {
        content: ManualInputHostContent,
        id: 'manualInput',
        manualConfig: {
          activePanelId: 'RedisHost',
          checkInstances: getRedisMachineList,
          checkKey: 'ip',
          checkType: 'ip',
        },
        name: t('手动输入'),
        previewConfig: {
          displayKey: 'ip',
        },
        tableConfig: {
          columnsChecked: ['ip', 'cloud_area', 'alive', 'host_name', 'os_name'],
          firsrColumn: {
            field: 'ip',
            label: t('主库主机'),
            role: 'redis_master',
          },
          getTableList: getRedisMachineList,
        },
      },
    ],
    TendbClusterHost: [
      {
        content: TendbClusterHostContent,
        id: 'TendbClusterHost',
        name: 'TendbCluster',
        previewConfig: {
          displayKey: 'ip',
        },
        tableConfig: {
          columnsChecked: ['ip', 'related_instances', 'cloud_area', 'alive', 'host_name', 'os_name'],
          firsrColumn: {
            field: 'ip',
            label: t('主库主机'),
            role: 'remote_master',
          },
          getTableList: getTendbclusterMachineList,
        },
        topoConfig: {
          countFunc: (clusterItem: { remote_db: { ip: string }[] }) => {
            const ipList = clusterItem.remote_db.map((hostItem) => hostItem.ip);
            return new Set(ipList).size;
          },
          getTopoList: queryMysqlCluster,
        },
      },
      {
        content: ManualInputHostContent,
        id: 'manualInput',
        manualConfig: {
          activePanelId: 'TendbClusterHost',
          checkInstances: getTendbclusterMachineList,
          checkKey: 'ip',
          checkType: 'ip',
        },
        name: t('手动输入'),
        previewConfig: {
          displayKey: 'ip',
        },
        tableConfig: {
          columnsChecked: ['ip', 'related_instances', 'cloud_area', 'alive', 'host_name', 'os_name'],
          firsrColumn: {
            field: 'ip',
            label: 'remote_master',
            role: 'remote_master',
          },
          getTableList: getTendbclusterMachineList,
        },
      },
    ],
    TendbhaHost: [
      {
        content: TendbHaHostContent,
        id: 'TendbhaHost',
        name: t('主库主机'),
        previewConfig: {
          displayKey: 'ip',
        },
        tableConfig: {
          columnsChecked: ['ip', 'related_instances', 'cloud_area', 'alive', 'host_name', 'os_name'],
          firsrColumn: {
            field: 'ip',
            label: t('主库主机'),
            role: 'master',
          },
          getTableList: getTendbhaMachineList,
        },
        topoConfig: {
          getTopoList: queryMysqlCluster,
        },
      },
      {
        content: ManualInputHostContent,
        id: 'manualInput',
        manualConfig: {
          activePanelId: 'TendbhaHost',
          checkInstances: getTendbhaMachineList,
          checkKey: 'ip',
          checkType: 'ip',
        },
        name: t('手动输入'),
        previewConfig: {
          displayKey: 'ip',
        },
        tableConfig: {
          columnsChecked: ['ip', 'related_instances', 'cloud_area', 'alive', 'host_name', 'os_name'],
          firsrColumn: {
            field: 'ip',
            label: t('主库主机'),
            role: 'master',
          },
          getTableList: getTendbhaMachineList,
        },
      },
    ],
    TendbHaHost: [
      {
        content: TendbHaHostContent,
        id: 'TendbHaHost',
        name: t('MySQL 主从'),
        previewConfig: {
          displayKey: 'ip',
        },
        tableConfig: {
          columnsChecked: ['ip', 'cloud_area', 'alive', 'host_name', 'os_name'],
          firsrColumn: {
            field: 'ip',
            label: 'IP',
            role: '',
          },
          getTableList: getTendbhaMachineList,
        },
        topoConfig: {
          getTopoList: queryMysqlCluster,
        },
      },
      {
        content: ManualInputHostContent,
        id: 'manualInput',
        manualConfig: {
          activePanelId: 'TendbClusterHost',
          checkInstances: getTendbhaMachineList,
          checkKey: 'ip',
          checkType: 'ip',
        },
        name: t('手动输入'),
        previewConfig: {
          displayKey: 'ip',
        },
        tableConfig: {
          columnsChecked: ['ip', 'cloud_area', 'alive', 'host_name', 'os_name'],
          firsrColumn: {
            field: 'ip',
            label: 'IP',
            role: '',
          },
          getTableList: getTendbhaMachineList,
        },
      },
    ],
    TendbSingleHost: [
      {
        content: TendbSingleHostContent,
        id: 'TendbSingleHost',
        name: t('MySQL 单节点'),
        previewConfig: {
          displayKey: 'ip',
        },
        tableConfig: {
          columnsChecked: ['ip', 'related_instances', 'cloud_area', 'alive', 'host_name', 'os_name'],
          firsrColumn: {
            field: 'ip',
            label: 'IP',
            role: '',
          },
          getTableList: getTendbSingleMachineList,
        },
        topoConfig: {
          getTopoList: queryMysqlCluster,
        },
      },
      {
        content: ManualInputHostContent,
        id: 'manualInput',
        manualConfig: {
          activePanelId: 'TendbClusterHost',
          checkInstances: getTendbSingleMachineList,
          checkKey: 'ip',
          checkType: 'ip',
        },
        name: t('手动输入'),
        previewConfig: {
          displayKey: 'ip',
        },
        tableConfig: {
          columnsChecked: ['ip', 'related_instances', 'cloud_area', 'alive', 'host_name', 'os_name'],
          firsrColumn: {
            field: 'ip',
            label: 'IP',
            role: '',
          },
          getTableList: getTendbSingleMachineList,
        },
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

  const lastHostList = computed(() =>
    Object.values(lastValues).reduce<string[]>((prevList, hostListItem) => {
      const ipList = hostListItem.map((listItem) => listItem.ip);
      prevList.push(...ipList);
      return prevList;
    }, []),
  );

  const submitButtonDisabledInfo = computed(() => {
    const info = {
      disabled: false,
      tooltips: {
        content: '',
        disabled: true,
      },
    };

    if (isEmpty.value) {
      info.disabled = true;
      info.tooltips.disabled = false;
      info.tooltips.content =
        panelTabActive.value.includes('Host') ||
        tabListMap[props.clusterTypes[0]][0]?.tableConfig?.firsrColumn?.field === 'ip'
          ? t('请选择主机')
          : t('请选择实例');
      return info;
    }

    const hostList = Object.values(lastValues).reduce<string[]>((prevList, hostListItem) => {
      const ipList = hostListItem.map((listItem) => listItem.ip);
      prevList.push(...ipList);
      return prevList;
    }, []);

    const checkValue = props.disableDialogSubmitMethod(hostList);
    if (checkValue) {
      info.disabled = true;
      info.tooltips.disabled = false;
      info.tooltips.content = _.isString(checkValue) ? checkValue : t('无法保存');
    }
    return info;
  });

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

  watch(
    () => props.selected,
    () => {
      if (props.selected) {
        Object.assign(lastValues, props.selected);
      }
    },
  );

  const handleChangePanel = (obj: PanelListItem) => {
    activePanelObj.value = obj;
    if (props.onlyOneType) {
      const initValues = Object.keys(lastValues).reduce<Record<string, T[]>>(
        (results, id) =>
          Object.assign({}, results, {
            [id]: [],
          }),
        {},
      );
      Object.assign(lastValues, initValues);
    }
  };

  const handleChange = (values: Props['selected'] = {}) => {
    // 如果只允许选一种类型, 则清空非当前类型的选中列表
    // 如果是勾选的取消全选，则忽略
    const currentKey = panelTabActive.value;
    if (props.onlyOneType && values[currentKey].length > 0) {
      Object.keys(lastValues).forEach((key) => {
        if (key !== currentKey) {
          lastValues[key] = [];
        } else {
          lastValues[key] = values[key];
        }
      });
      return;
    }
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
