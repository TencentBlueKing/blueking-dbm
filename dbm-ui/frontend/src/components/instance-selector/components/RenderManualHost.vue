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
  <div class="instance-selector-render-manual-host">
    <BkInput
      v-model.trim="search"
      clearable
      :placeholder="$t('请输入实例')" />
    <DbOriginalTable
      :columns="columns"
      :data="renderData"
      :height="505"
      :is-searching="!!search"
      :settings="tableSettings"
      style="margin-top: 12px;"
      @clear-search="handleClearSearch"
      @row-click.stop="handleRowClick" />
  </div>
</template>

<script setup lang="tsx">
  import {
    ref,
  } from 'vue';
  import { useI18n } from 'vue-i18n';

  import type { InstanceInfos  } from '@services/types/clusters';

  import DbStatus from '@components/db-status/index.vue';

  import getSettings from '../common/tableSettings';
  import type { IValue, MySQLClusterTypes } from '../common/types';
  import type { InstanceSelectorValues } from '../Index.vue';

  import { ClusterTypes } from '@/common/const';

  interface TableItem {
    data: InstanceInfos
  }

  interface Props {
    role?: string,
    lastValues: InstanceSelectorValues,
    tableData: InstanceInfos[],
  }

  interface Emits {
    (e: 'change', value: InstanceSelectorValues): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const tableSettings = getSettings(props.role);

  const formatValue = (data: InstanceInfos) => ({
    bk_host_id: data.bk_host_id,
    instance_address: data.instance_address,
    cluster_id: data.cluster_id,
    cluster_type: data.cluster_type as MySQLClusterTypes,
    bk_cloud_id: data.host_info.cloud_id,
    port: data.port,
    ip: data.ip,
  });

  const search = ref('');

  const checkedMap = shallowRef({} as Record<string, IValue>);

  watch(() => props.lastValues, () => {
    checkedMap.value = {};
    for (const checkedList of Object.values(props.lastValues)) {
      for (const item of checkedList) {
        checkedMap.value[item.instance_address] = item;
      }
    }
  }, { immediate: true, deep: true });

  const renderData = computed(() => {
    if (search.value === '') return props.tableData;

    return props.tableData.filter(item => (
      item.instance_address.includes(search.value)
    ));
  });
  const isSelectedAll = computed(() => (
    renderData.value.length > 0
    && renderData.value.length === renderData.value.filter(item => checkedMap.value[item.instance_address]).length
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
      render: ({ data }: TableItem) => (
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

  const triggerChange = () => {
    const lastValues: InstanceSelectorValues = {
      [ClusterTypes.TENDBHA]: [],
      [ClusterTypes.TENDBSINGLE]: [],
    };
    for (const item of Object.values(checkedMap.value)) {
      lastValues[item.cluster_type].push(item);
    }

    emits('change', {
      ...props.lastValues,
      ...lastValues,
    });
  };

  const handleSelectPageAll = (checked: boolean) => {
    const lastCheckMap = { ...checkedMap.value };
    for (const item of renderData.value) {
      if (checked) {
        lastCheckMap[item.instance_address] = formatValue(item);
      } else {
        delete lastCheckMap[item.instance_address];
      }
    }
    checkedMap.value = lastCheckMap;
    triggerChange();
  };

  const handleTableSelectOne = (checked: boolean, data: InstanceInfos) => {
    const lastCheckMap = { ...checkedMap.value };
    if (checked) {
      lastCheckMap[data.instance_address] = formatValue(data);
    } else {
      delete lastCheckMap[data.instance_address];
    }
    checkedMap.value = lastCheckMap;
    triggerChange();
  };

  const handleRowClick = (e: Event, data: InstanceInfos) => {
    const checked = checkedMap.value[data.instance_address];
    handleTableSelectOne(!checked, data);
  };

  const handleClearSearch = () => {
    search.value = '';
  };
</script>

<style lang="less">
  .instance-selector-render-manual-host {
    padding: 0 24px;

    .bk-table-body {
      tr {
        cursor: pointer;
      }
    }
  }
</style>
