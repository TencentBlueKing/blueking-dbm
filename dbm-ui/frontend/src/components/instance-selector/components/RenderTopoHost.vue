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
      v-model="search"
      clearable
      :placeholder="$t('请输入实例')"
      @clear="handlePageValueChange(1)"
      @enter="handlePageValueChange(1)" />
    <BkLoading
      :loading="isTableDataLoading"
      :z-index="2">
      <DbOriginalTable
        :columns="columns"
        :data="tableData"
        :height="505"
        :is-anomalies="isAnomalies"
        :is-searching="!!search"
        :pagination="pagination"
        remote-pagination
        :settings="tableSettings"
        style="margin-top: 12px;"
        @clear-search="handleClearSearch"
        @page-limit-change="handlePageLimitChange"
        @page-value-change="handlePageValueChange"
        @refresh="fetchData"
        @row-click.stop="handleRowClick" />
    </BkLoading>
  </div>
</template>
<script setup lang="tsx">
  import {
    ref,
    watch,
  } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { getResourceInstances as getTendbhaResourceInstances } from '@services/source/resourceTendbha';
  import { getResourceInstances as getTendbsingleResourceInstances } from '@services/source/resourceTendbsingle';
  import type { InstanceInfos, ResourceInstance } from '@services/types/clusters';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes } from '@common/const';

  import DbStatus from '@components/db-status/index.vue';

  import getSettings from '../common/tableSettings';
  import type { IValue, MySQLClusterTypes } from '../common/types';
  import type { InstanceSelectorValues } from '../Index.vue';

  import { activePanelInjectionKey } from './PanelTab.vue';

  interface TableItem {
    data: InstanceInfos
  }

  interface Props {
    node?: {
      id: number,
      name: string
    },
    role?: string
    lastValues: InstanceSelectorValues
  }

  interface Emits {
    (e: 'change', value: InstanceSelectorValues): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const apiMap: Record<string, (params: any) => ReturnType<typeof getTendbsingleResourceInstances>> = {
    [ClusterTypes.TENDBSINGLE]: getTendbsingleResourceInstances,
    [ClusterTypes.TENDBHA]: getTendbhaResourceInstances,
  };

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
  const { currentBizId } = useGlobalBizs();
  const activePanel = inject(activePanelInjectionKey);

  const tableSettings = getSettings(props.role);

  const search = ref('');
  const isAnomalies = ref(false);

  const checkedMap = shallowRef({} as Record<string, IValue>);

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

  const pagination = reactive({
    count: 0,
    current: 1,
    limit: 10,
    limitList: [10, 20, 50, 100],
    align: 'right',
    layout: ['total', 'limit', 'list'],
  });
  const isTableDataLoading = ref(false);
  const tableData = shallowRef<ResourceInstance []>([]);
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
      render: ({ data }: TableItem) => data.host_info.cloud_area.name || '--',
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

  const fetchData = () => {
    isTableDataLoading.value = true;
    const params = {
      db_type: 'mysql',
      bk_biz_id: currentBizId,
      instance_address: search.value,
      limit: pagination.limit,
      offset: (pagination.current - 1) * pagination.limit,
      type: activePanel?.value === 'manualInput' ? undefined : activePanel?.value,
      role: props.role,
      extra: 1,
    };
    if (props.node && props.node.id !== currentBizId) {
      Object.assign(params, {
        cluster_id: props.node.id,
      });
    }
    apiMap[activePanel?.value || 'tendbsingle'](params)
      .then((data) => {
        tableData.value = data.results;
        pagination.count = data.count;
        isAnomalies.value = false;
      })
      .catch(() => {
        tableData.value = [];
        pagination.count = 0;
        isAnomalies.value = true;
      })
      .finally(() => {
        isTableDataLoading.value = false;
      });
  };

  watch(() => props.node, () => {
    if (props.node) {
      fetchData();
    }
  });

  const triggerChange = () => {
    const result = Object.values(checkedMap.value).reduce((result, item) => {
      result.push({
        ...item,
      });
      return result;
    }, [] as IValue[]);[];

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

  // 切换每页条数
  const handlePageLimitChange = (pageLimit: number) => {
    pagination.limit = pageLimit;
    fetchData();
  };
  // 切换页码
  const handlePageValueChange = (pageValue:number) => {
    pagination.current = pageValue;
    fetchData();
  };
  // 清空搜索
  const handleClearSearch = () => {
    search.value = '';
    handlePageValueChange(1);
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
