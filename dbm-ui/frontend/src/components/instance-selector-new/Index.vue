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
    class="spider-instance-selector"
    :close-icon="false"
    :draggable="false"
    :esc-close="false"
    :is-show="isShow"
    :quick-close="false"
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
          @change="handleChange" />
      </template>
      <template #aside>
        <PreviewResult
          :active-panel-id="panelTabActive"
          :display-key="activePanelObj?.previewConfig?.displayKey"
          :get-table-list="activePanelObj?.tableConfig?.getTableList"
          :last-values="lastValues"
          :show-title="activePanelObj?.previewConfig?.showTitle"
          :title="activePanelObj?.previewConfig?.title"
          @change="handleChange" />
      </template>
    </BkResizeLayout>
    <template #footer>
      <span
        v-bk-tooltips="{
          content: t('请选择实例'),
          disabled: !isEmpty
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
        @click="handleClose">
        {{ t('取消') }}
      </BkButton>
    </template>
  </BkDialog>
</template>
<script lang="ts">
  import { t } from '@locales/index';
  export default { name: 'InstanceSelector' };

  export interface IValue {
    bk_host_id: number,
    bk_cloud_id: number,
    ip: string,
    port: number,
    instance_address: string,
    cluster_id: number,
    cluster_type: string,
  }

  export type InstanceSelectorValues<T = IValue> = Record<string, T[]>

  export const activePanelInjectionKey = Symbol('activePanel');

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
        field: 'cloud_area',
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

<script setup lang="ts">
  import _ from 'lodash';

  import {
    listClusterHostsMasterFailoverProxy,
    listClustersMasterFailoverProxy,
  } from '@services/redis/toolbox';
  import {
    checkMysqlInstances,
    checkRedisInstances,
  } from '@services/source/instances';
  import { queryClusters } from '@services/source/mysqlCluster';
  import { getSpiderInstanceList } from '@services/source/spider';

  import { ClusterTypes } from '@common/const';

  import ManualInputContent from './components/common/manual-content/Index.vue';
  import PanelTab  from './components/common/PanelTab.vue';
  import PreviewResult from './components/common/preview-result/Index.vue';
  import RedisContent from './components/redis/Index.vue';
  import TendbClusterContent from './components/tendb-cluster/Index.vue';

  export type TableSetting = ReturnType<typeof getSettings>;

  export type PanelListType = {
    name: string,
    id: string,
    topoConfig?: {
      topoAlertContent?: Element,
      filterClusterId?: number,
      getTopoList?: (params: any) => Promise<any[]>,
      countFunc?: (data: any) => number,
    }
    tableConfig?: {
      isRemotePagination?: boolean,
      columnsChecked?: string[],
      firsrColumn?: {
        label: string,
        field: string,
        role: string, // 接口过滤
      },
      roleFilterList?: {
        list: { text: string, value: string }[],
      }
      disabledRowConfig?: {
        handler: (data: any) => boolean,
        tip?: string,
      },
      getTableList?: (params: any) => Promise<any>,
      statusFilter?: (data: any) => boolean,
    },
    manualConfig?: {
      checkType: 'ip' | 'instance',
      checkKey: keyof IValue,
      activePanelId?: string
      checkInstances?: (params: any) => Promise<any[]>,
    },
    previewConfig?: {
      displayKey?: keyof IValue,
      showTitle?: boolean,
      title?: string,
    },
    content?: any,
  }[]

  type PanelListItem = PanelListType[number];

  type RedisModel = ServiceReturnType<typeof listClustersMasterFailoverProxy>[number]
  type RedisHostModel = ServiceReturnType<typeof listClusterHostsMasterFailoverProxy>['results'][number]

  interface Props {
    clusterTypes: ClusterTypes[],
    tabListConfig?: Record<string, PanelListType>,
    selected?: InstanceSelectorValues,
  }

  interface Emits {
    (e: 'change', value: InstanceSelectorValues): void
  }

  const props = withDefaults(defineProps<Props>(), {
    tabListConfig: undefined,
    selected: undefined,
  });

  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const tabListMap: Record<string, PanelListType> = {
    [ClusterTypes.REDIS]: [
      {
        id: 'redis',
        name: t('主库主机'),
        topoConfig: {
          getTopoList: listClustersMasterFailoverProxy,
          countFunc: (item: RedisModel) => item.redisMasterCount,
        },
        tableConfig: {
          getTableList: listClusterHostsMasterFailoverProxy,
          firsrColumn: {
            label: 'master Ip',
            role: 'redis_master',
            field: 'ip',
          },
          columnsChecked: ['ip', 'cloud_area', 'status', 'host_name', 'os_name'],
          statusFilter: (data: RedisHostModel) => !data.isMasterFailover,
          isRemotePagination: false,
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
          getTableList: listClusterHostsMasterFailoverProxy,
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
          getTopoList: queryClusters,
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
  };

  const diffComposeObjs = (objA: Record<string, any>, objB: Record<string, any>) => {
    const obj: Record<string, any> = {};
    Object.keys(objA).forEach((key) => {
      if (Object.prototype.toString.call(objB[key]) === '[object Object]') {
        obj[key] = diffComposeObjs(_.cloneDeep(objA[key]), _.cloneDeep(objB[key]));
        return;
      }
      if (objB[key] !== undefined) {
        obj[key] = objB[key];
        // eslint-disable-next-line no-param-reassign
        delete objB[key];
      } else {
        obj[key] = objA[key];
      }
    });
    if (Object.keys(objB).length > 0) {
      Object.keys(objB).forEach((key) => {
        if (obj[key] === undefined) {
          obj[key] = objB[key];
        }
      });
    }
    return obj;
  };

  const panelTabActive = ref<string>();
  const activePanelObj = ref<PanelListItem>();

  const lastValues = reactive<InstanceSelectorValues>({});

  provide(activePanelInjectionKey, panelTabActive);

  const clusterTabListMap = computed<Record<string, PanelListType>>(() => {
    if (props.tabListConfig) {
      Object.keys(props.tabListConfig).forEach((type) => {
        const configArr = props.tabListConfig?.[type];
        if (configArr) {
          configArr.forEach((config, index) => {
            let objItem = {};
            const baseObj = tabListMap[type][index] as Record<string, any>;
            if (baseObj) {
              objItem = {
                ...diffComposeObjs(_.cloneDeep(baseObj), _.cloneDeep(config)),
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

  const panelList = computed<PanelListType>(() => _.flatMap(props.clusterTypes.map(type => tabListMap[type])));

  const tableSettings = computed(() => {
    const setting = getSettings(activePanelObj.value?.tableConfig?.firsrColumn?.label);
    const checked = activePanelObj?.value?.tableConfig?.columnsChecked;
    if (checked) {
      // 自定义列项
      setting.checked = checked;
    }
    return setting;
  });

  const isEmpty = computed(() => !Object.values(lastValues).some(values => values.length > 0));
  const renderCom = computed(() => activePanelObj.value?.content);

  watch(() => props.clusterTypes, (types) => {
    if (types) {
      const activeObj = clusterTabListMap.value[types[0]];
      [activePanelObj.value] = activeObj;
      panelTabActive.value = activeObj[0].id;
    }
  }, {
    immediate: true,
    deep: true,
  });

  watch(() => isShow, (show) => {
    if (show && props.selected) {
      Object.assign(lastValues, props.selected);
    }
  });

  const handleChangePanel = (obj: PanelListItem) => {
    activePanelObj.value = obj;
  };

  const handleChange = (values: InstanceSelectorValues) => {
    Object.assign(lastValues, values);
  };

  const handleSubmit = () => {
    emits('change', lastValues);
    handleClose();
  };

  const handleClose = () => {
    isShow.value = false;
  };
</script>
<style lang="less">
  .spider-instance-selector {
    display: block;
    width: 80%;
    max-width: 1600px;
    min-width: 1200px;

    .bk-modal-header {
      display: none;
    }

    .bk-modal-content {
      padding: 0 !important;
      overflow-y: hidden !important;
    }
  }
</style>
