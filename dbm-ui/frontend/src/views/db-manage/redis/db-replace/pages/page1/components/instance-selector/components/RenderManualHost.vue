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
      style="margin-top: 12px"
      @clear-search="handleClearSearch"
      @row-click.stop="handleRowClick" />
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import DbStatus from '@components/db-status/index.vue';

  import type { InstanceSelectorValues } from '../Index.vue';

  import type { InstanceItem } from './RenderManualInput.vue';
  import type { ChoosedItem } from './RenderRedisHost.vue';

  interface TableItem {
    data: InstanceItem;
  }

  interface Props {
    lastValues: InstanceSelectorValues;
    role?: string;
    tableData: InstanceItem[];
  }

  type Emits = (e: 'change', value: InstanceSelectorValues) => void;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const search = ref('');

  const checkedMap = shallowRef({} as Record<string, ChoosedItem>);

  watch(
    () => props.lastValues,
    () => {
      checkedMap.value = {};
      for (const checkedList of Object.values(props.lastValues)) {
        for (const item of checkedList) {
          checkedMap.value[item.ip] = item as ChoosedItem;
        }
      }
    },
    { deep: true, immediate: true },
  );

  const renderData = computed(() => {
    if (search.value === '') return props.tableData;

    return props.tableData.filter((item) => item.ip.includes(search.value));
  });
  const isSelectedAll = computed(
    () =>
      renderData.value.length > 0 &&
      renderData.value.length === renderData.value.filter((item) => checkedMap.value[item.ip]).length,
  );

  const columns = [
    {
      fixed: 'left',
      label: () => (
        <bk-checkbox
          label={true}
          model-value={isSelectedAll.value}
          onChange={handleSelectPageAll}
          onClick={(e: Event) => e.stopPropagation()}
        />
      ),
      render: ({ data }: TableItem) => (
        <bk-checkbox
          label={true}
          model-value={Boolean(checkedMap.value[data.ip])}
          style='vertical-align: middle;'
          onChange={(value: boolean) => handleTableSelectOne(value, data)}
          onClick={(e: Event) => e.stopPropagation()}
        />
      ),
      width: 60,
    },
    {
      field: 'ip',
      fixed: 'left',
      label: props.role ? props.role.charAt(0).toUpperCase() + props.role.slice(1) : t('实例'),
      minWidth: 160,
    },
    {
      field: 'role',
      label: t('角色'),
      // filter: {
      //   list: [{ text: 'master', value: 'master' }, { text: 'slave', value: 'slave' }, { text: 'proxy', value: 'proxy' }],
      // },
      render: ({ data }: TableItem) => <span>{data.role}</span>,
      showOverflowTooltip: true,
    },
    {
      field: 'status',
      label: t('实例状态'),
      render: ({ data }: TableItem) => {
        const info =
          data.host_info.alive === 1 ? { text: t('正常'), theme: 'success' } : { text: t('异常'), theme: 'danger' };
        return <DbStatus theme={info.theme}>{info.text}</DbStatus>;
      },
    },
    {
      field: 'cloud_area',
      label: t('管控区域'),
      minWidth: 100,
      render: ({ data }: TableItem) => data.host_info?.cloud_area.name || '--',
    },
    {
      field: 'alive',
      label: t('Agent状态'),
      minWidth: 100,
      render: ({ data }: TableItem) => {
        const info =
          data.host_info?.alive === 1 ? { text: t('正常'), theme: 'success' } : { text: t('异常'), theme: 'danger' };
        return <DbStatus theme={info.theme}>{info.text}</DbStatus>;
      },
      sort: true,
    },
    {
      field: 'host_name',
      label: t('主机名称'),
      render: ({ data }: TableItem) => data.host_info?.host_name || '--',
      showOverflowTooltip: true,
    },
    {
      field: 'os_name',
      label: t('OS名称'),
      render: ({ data }: TableItem) => data.host_info?.os_name || '--',
      showOverflowTooltip: true,
    },
    {
      field: 'cloud_vendor',
      label: t('所属云厂商'),
      render: ({ data }: TableItem) => data.host_info?.cloud_vendor || '--',
      showOverflowTooltip: true,
    },
    {
      field: 'os_type',
      label: t('OS类型'),
      render: ({ data }: TableItem) => data.host_info?.os_type || '--',
      showOverflowTooltip: true,
    },
    {
      field: 'host_id',
      label: t('主机ID'),
      render: ({ data }: TableItem) => data.host_info?.host_id || '--',
      showOverflowTooltip: true,
    },
    {
      field: 'agent_id',
      label: 'Agent ID',
      render: ({ data }: TableItem) => data.host_info?.agent_id || '--',
      showOverflowTooltip: true,
    },
  ];

  const triggerChange = () => {
    const lastValues: InstanceSelectorValues = {
      idleHosts: [],
    };
    lastValues.idleHosts = Object.values(checkedMap.value);

    emits('change', {
      ...props.lastValues,
      ...lastValues,
    });
  };

  const formatValue = (data: InstanceItem) => ({
    bk_cloud_id: data.host_info?.cloud_id || 0,
    bk_host_id: data.bk_host_id,
    cluster_domain: data.master_domain,
    cluster_id: data.cluster_id,
    ip: data.ip || '',
    role: data.role,
    spec_config: data.spec_config,
  });

  const handleSelectPageAll = (checked: boolean) => {
    const lastCheckMap = { ...checkedMap.value };
    for (const item of renderData.value) {
      if (checked) {
        lastCheckMap[item.ip] = formatValue(item);
      } else {
        delete lastCheckMap[item.ip];
      }
    }
    checkedMap.value = lastCheckMap;
    triggerChange();
  };

  const handleTableSelectOne = (checked: boolean, data: InstanceItem) => {
    const lastCheckMap = { ...checkedMap.value };
    if (checked) {
      lastCheckMap[data.ip] = formatValue(data);
    } else {
      delete lastCheckMap[data.ip];
    }
    checkedMap.value = lastCheckMap;
    triggerChange();
  };

  const handleRowClick = (key: number, data: InstanceItem) => {
    const checked = checkedMap.value[data.ip];
    handleTableSelectOne(!checked, data);
  };

  const handleClearSearch = () => {
    search.value = '';
  };
</script>

<style lang="less">
  .instance-selector-render-manual-host {
    padding: 0 24px;
  }
</style>
