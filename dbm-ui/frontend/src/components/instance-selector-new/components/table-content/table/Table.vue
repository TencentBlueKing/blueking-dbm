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
  <div class="instance-selector-render-topo-host">
    <BkInput
      v-model="searchValue"
      clearable
      :placeholder="$t('请输入实例')"
      @clear="handleChangePage(1)"
      @enter="handleChangePage(1)" />
    <BkLoading
      :loading="isLoading"
      :z-index="2">
      <DbOriginalTable
        :columns="columns"
        :data="tableData"
        :is-anomalies="isAnomalies"
        :is-searching="!!searchValue"
        :max-height="530"
        :pagination="pagination.count < 10 ? false : pagination"
        remote-pagination
        :settings="tableSetting"
        style="margin-top: 12px;"
        @clear-search="handleClearSearch"
        @page-limit-change="handeChangeLimit"
        @page-value-change="handleChangePage"
        @refresh="fetchResources"
        @row-click.stop="handleRowClick" />
    </BkLoading>
  </div>
</template>
<script setup lang="tsx" generic="T extends ResourceInstance">
  import { useI18n } from 'vue-i18n';

  import type { InstanceInfos, ResourceInstance } from '@services/types/clusters';
  import type { ListBase } from '@services/types/common';

  import DbStatus from '@components/db-status/index.vue';
  import type { IValue, MySQLClusterTypes } from '@components/instance-selector-new/common/types';
  import { activePanelInjectionKey } from '@components/instance-selector-new/components/PanelTab.vue';
  import type { InstanceSelectorValues, TableSetting } from '@components/instance-selector-new/Index.vue';

  import { useTableData } from './useTableData';

  interface TableItem {
    data: InstanceInfos
  }

  interface Props {
    lastValues: InstanceSelectorValues,
    clusterId?: number,
    role?: string,
    // eslint-disable-next-line vue/no-unused-properties
    getTableList: (params: Record<string, any>) => ListBase<T[]>,
    tableSetting: TableSetting
  }

  interface Emits {
    (e: 'change', value: InstanceSelectorValues): void;
  }

  const props = withDefaults(defineProps<Props>(), {
    clusterId: undefined,
    role: '',
  });

  const emits = defineEmits<Emits>();
  console.log('tableSettings>>', props.tableSetting);
  const formatValue = (data: ResourceInstance) => ({
    bk_host_id: data.bk_host_id,
    instance_address: data.instance_address,
    cluster_id: data.cluster_id,
    bk_cloud_id: data?.host_info?.cloud_id || 0,
    ip: data.ip || '',
    port: data.port,
    cluster_type: data.cluster_type as MySQLClusterTypes,
  });

  const { t } = useI18n();

  const activePanel = inject(activePanelInjectionKey);

  const checkedMap = shallowRef({} as Record<string, IValue>);

  const initRole = computed(() => props.role);
  const selectClusterId = computed(() => props.clusterId);

  const {
    isLoading,
    data: tableData,
    pagination,
    isAnomalies,
    searchValue,
    fetchResources,
    handleChangePage,
    handeChangeLimit,
    handleClearSearch,
  } = useTableData<ResourceInstance>(activePanel, initRole, selectClusterId);

  const isSelectedAll = computed(() => (
    tableData.value.length > 0
    && tableData.value.length === tableData.value.filter(item => checkedMap.value[item.instance_address]).length
  ));

  const columns = [
    {
      width: 60,
      fixed: 'left',
      label: () => (
        <bk-checkbox
          label={true}
          model-value={isSelectedAll.value}
          onClick={(e: Event) => e.stopPropagation()}
          onChange={handleSelectPageAll}
        />
      ),
      render: ({ data }: {data: ResourceInstance}) => (
        <bk-checkbox
          style="vertical-align: middle;"
          label={true}
          model-value={Boolean(checkedMap.value[data.instance_address])}
          onClick={(e: Event) => e.stopPropagation()}
          onChange={(value: boolean) => handleTableSelectOne(value, data)}
        />
      ),
    },
    {
      fixed: 'left',
      minWidth: 160,
      label: props.role ? props.role.charAt(0).toUpperCase() + props.role.slice(1) : t('实例'),
      field: 'instance_address',
    },
    {
      label: t('角色'),
      field: 'role',
      showOverflowTooltip: true,
    },
    {
      label: t('实例状态'),
      field: 'status',
      render: ({ data }: TableItem) => {
        const info = data.status === 'running' ? { theme: 'success', text: t('正常') } : { theme: 'danger', text: t('异常') };
        return <DbStatus theme={info.theme}>{info.text}</DbStatus>;
      },
    },
    {
      minWidth: 100,
      label: t('管控区域'),
      field: 'cloud_area',
      render: ({ data }: TableItem) => data.host_info?.cloud_area?.name || '--',
    },
    {
      minWidth: 100,
      label: t('Agent状态'),
      field: 'alive',
      render: ({ data }: TableItem) => {
        const info = data.host_info.alive === 1 ? { theme: 'success', text: t('正常') } : { theme: 'danger', text: t('异常') };
        return <DbStatus theme={info.theme}>{info.text}</DbStatus>;
      },
    },
    {
      label: t('主机名称'),
      field: 'host_name',
      showOverflowTooltip: true,
      render: ({ data }: TableItem) => data.host_info.host_name || '--',
    },
    {
      label: t('OS名称'),
      field: 'os_name',
      showOverflowTooltip: true,
      render: ({ data }: TableItem) => data.host_info.os_name || '--',
    },
    {
      label: t('所属云厂商'),
      field: 'cloud_vendor',
      showOverflowTooltip: true,
      render: ({ data }: TableItem) => data.host_info.cloud_vendor || '--',
    },
    {
      label: t('OS类型'),
      field: 'os_type',
      showOverflowTooltip: true,
      render: ({ data }: TableItem) => data.host_info.os_type || '--',
    },
    {
      label: t('主机ID'),
      field: 'host_id',
      showOverflowTooltip: true,
      render: ({ data }: TableItem) => data.host_info.host_id || '--',
    },
    {
      label: 'Agent ID',
      field: 'agent_id',
      showOverflowTooltip: true,
      render: ({ data }: TableItem) => data.host_info.agent_id || '--',
    },
  ];

  watch(() => props.lastValues, () => {
    // 切换 tab 回显选中状态 \ 预览结果操作选中状态
    if (activePanel?.value && activePanel.value !== 'manualInput') {
      checkedMap.value = {};
      const checkedList = props.lastValues[activePanel.value];
      for (const item of checkedList) {
        checkedMap.value[item.instance_address] = item;
      }
    }
  }, { immediate: true, deep: true });

  watch(() => props.clusterId, () => {
    if (props.clusterId) {
      fetchResources();
    }
  }, {
    immediate: true,
  });

  const triggerChange = () => {
    const result = Object.values(checkedMap.value).reduce((result, item) => {
      result.push({
        ...item,
      });
      return result;
    }, [] as IValue[]);

    if (activePanel?.value) {
      emits('change', {
        ...props.lastValues,
        [activePanel.value]: result,
      });
    }
  };

  const handleSelectPageAll = (checked: boolean) => {
    const lastCheckMap = { ...checkedMap.value };
    for (const item of tableData.value) {
      if (checked) {
        lastCheckMap[item.instance_address] = formatValue(item);
      } else {
        delete lastCheckMap[item.instance_address];
      }
    }
    checkedMap.value = lastCheckMap;
    triggerChange();
  };

  const handleTableSelectOne = (checked: boolean, data: ResourceInstance) => {
    const lastCheckMap = { ...checkedMap.value };
    if (checked) {
      lastCheckMap[data.instance_address] = formatValue(data);
    } else {
      delete lastCheckMap[data.instance_address];
    }
    checkedMap.value = lastCheckMap;
    triggerChange();
  };

  const handleRowClick = (key: number, data: ResourceInstance) => {
    const checked = checkedMap.value[data.instance_address];
    handleTableSelectOne(!checked, data);
  };

</script>

<style lang="less">
  .instance-selector-render-topo-host {
    padding: 0 24px;

    .bk-table-body {
      tr {
        cursor: pointer;
      }
    }
  }
</style>
