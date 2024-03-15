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
      :placeholder="t('请输入实例')" />
    <BkLoading
      :loading="isLoading"
      :z-index="2">
      <DbOriginalTable
        :columns="columns"
        :data="isManul? renderManualData : tableData"
        :max-height="530"
        :pagination="pagination.count < 10 ? false : pagination"
        :remote-pagination="isRemotePagination"
        :settings="tableSetting"
        style="margin-top: 12px;"
        @page-limit-change="handeChangeLimit"
        @page-value-change="handleChangePage"
        @refresh="fetchResources"
        @row-click.stop.prevent="handleRowClick" />
    </BkLoading>
  </div>
</template>
<script setup lang="tsx" generic="T extends IValue">
  import type { Ref } from 'vue';
  import { useI18n } from 'vue-i18n';

  import DbStatus from '@components/db-status/index.vue';

  import { firstLetterToUpper } from '@utils';

  import {
    activePanelInjectionKey,
    type InstanceSelectorValues,
    type IValue,
    type PanelListType,
    type TableSetting,
  } from '../../../Index.vue';

  import { useTableData } from './useTableData';

  type TableConfigType = Required<PanelListType[number]>['tableConfig'];

  interface DataRow {
    data: T,
  }

  interface Props {
    lastValues: InstanceSelectorValues<T>,
    tableSetting: TableSetting,
    activePanelId?: string,
    clusterId?: number,
    isManul?: boolean,
    manualTableData?: T[];
    isRemotePagination?: TableConfigType['isRemotePagination'],
    firsrColumn?: TableConfigType['firsrColumn'],
    roleFilterList?: TableConfigType['roleFilterList'],
    disabledRowConfig?: TableConfigType['disabledRowConfig'],
    // eslint-disable-next-line vue/no-unused-properties
    getTableList?: TableConfigType['getTableList'],
    statusFilter?: TableConfigType['statusFilter'],
  }

  interface Emits {
    (e: 'change', value: InstanceSelectorValues<T>): void;
  }

  const props = withDefaults(defineProps<Props>(), {
    clusterId: undefined,
    isManul: false,
    manualTableData: () => ([]),
    firsrColumn: undefined,
    statusFilter: undefined,
    isRemotePagination: true,
    activePanelId: 'tendbcluster',
    disabledRowConfig: undefined,
    roleFilterList: undefined,
    getTableList: undefined,
  });

  const emits = defineEmits<Emits>();

  const formatValue = (data: T) => ({
    bk_host_id: data.bk_host_id,
    instance_address: data.instance_address || '',
    cluster_id: data.cluster_id,
    bk_cloud_id: data?.host_info?.cloud_id || 0,
    ip: data.ip || '',
    port: data.port,
    cluster_type: data.cluster_type,
  });

  const { t } = useI18n();

  const activePanel = inject(activePanelInjectionKey) as Ref<string> | undefined;

  const checkedMap = shallowRef({} as Record<string, T>);

  const initRole = computed(() => props.firsrColumn?.role);
  const selectClusterId = computed(() => props.clusterId);
  const firstColumnFieldId = computed(() => (props.firsrColumn?.field || 'instance_address') as keyof IValue);
  const mainSelectDisable = computed(() => (props.disabledRowConfig
    // eslint-disable-next-line max-len
    ? tableData.value.filter(data => props.disabledRowConfig?.handler(data)).length === tableData.value.length : false));

  const {
    isLoading,
    data: tableData,
    pagination,
    searchValue,
    fetchResources,
    handleChangePage,
    handeChangeLimit,
  } = useTableData<T>(initRole, selectClusterId);

  const renderManualData = computed(() => {
    if (searchValue.value === '') {
      return props.manualTableData;
    }
    return props.manualTableData.filter(item => (
      (item[firstColumnFieldId.value] as string).includes(searchValue.value)
    ));
  });

  const isSelectedAll = computed(() => (
    tableData.value.length > 0
    // eslint-disable-next-line max-len
    && tableData.value.length === tableData.value.filter(item => checkedMap.value[item[firstColumnFieldId.value]]).length
  ));

  let isSelectedAllReal = false;

  const columns = [
    {
      width: 60,
      fixed: 'left',
      label: () => (
        <bk-checkbox
          label={true}
          model-value={isSelectedAll.value}
          disabled={mainSelectDisable.value}
          onChange={handleSelectPageAll}
        />
      ),
      render: ({ data }: DataRow) => {
        if (props.disabledRowConfig && props.disabledRowConfig.handler(data)) {
          return (
            <bk-popover theme="dark" placement="top" popoverDelay={0}>
              {{
                default: () => <bk-checkbox style="vertical-align: middle;" disabled />,
                content: () => <span>{props.disabledRowConfig?.tip}</span>,
              }}
            </bk-popover>
          );
        }
        return (
          <bk-checkbox
            style="vertical-align: middle;"
            label={true}
            model-value={Boolean(checkedMap.value[data[firstColumnFieldId.value]])}
            onChange={(value: boolean) => handleTableSelectOne(value, data)}
          />
        );
      },
    },
    {
      fixed: 'left',
      minWidth: 160,
      label: props.firsrColumn?.label ? firstLetterToUpper(props.firsrColumn.label) : t('实例'),
      field: props.firsrColumn?.field ? props.firsrColumn.field : 'instance_address',
    },
    {
      label: t('角色'),
      field: 'role',
      showOverflowTooltip: true,
      filter: props.roleFilterList,
    },
    {
      label: t('实例状态'),
      field: 'status',
      render: ({ data }: DataRow) => {
        const isNormal = props.statusFilter ? props.statusFilter(data) : data.status === 'running';
        const info = isNormal ? { theme: 'success', text: t('正常') } : { theme: 'danger', text: t('异常') };
        return <DbStatus theme={info.theme}>{info.text}</DbStatus>;
      },
    },
    {
      minWidth: 100,
      label: t('管控区域'),
      field: 'cloud_area',
      showOverflowTooltip: true,
      render: ({ data }: DataRow) => data.host_info?.cloud_area?.name || '--',
    },
    {
      minWidth: 100,
      label: t('Agent状态'),
      field: 'alive',
      render: ({ data }: DataRow) => {
        const info = data.host_info?.alive === 1 ? { theme: 'success', text: t('正常') } : { theme: 'danger', text: t('异常') };
        return <DbStatus theme={info.theme}>{info.text}</DbStatus>;
      },
    },
    {
      label: t('主机名称'),
      field: 'host_name',
      showOverflowTooltip: true,
      render: ({ data }: DataRow) => data.host_info?.host_name || '--',
    },
    {
      label: t('OS名称'),
      field: 'os_name',
      showOverflowTooltip: true,
      render: ({ data }: DataRow) => data.host_info?.os_name || '--',
    },
    {
      label: t('所属云厂商'),
      field: 'cloud_vendor',
      showOverflowTooltip: true,
      render: ({ data }: DataRow) => data.host_info?.cloud_vendor || '--',
    },
    {
      label: t('OS类型'),
      field: 'os_type',
      showOverflowTooltip: true,
      render: ({ data }: DataRow) => data.host_info.os_type || '--',
    },
    {
      label: t('主机ID'),
      field: 'host_id',
      showOverflowTooltip: true,
      render: ({ data }: DataRow) => data.host_info?.host_id || '--',
    },
    {
      label: 'Agent ID',
      field: 'agent_id',
      showOverflowTooltip: true,
      render: ({ data }: DataRow) => data.host_info?.agent_id || '--',
    },
  ];

  watch(() => props.lastValues, () => {
    if (props.isManul) {
      checkedMap.value = {};
      for (const checkedList of Object.values(props.lastValues)) {
        for (const item of checkedList) {
          checkedMap.value[item[firstColumnFieldId.value]] = item;
        }
      }
      return;
    }
    // 切换 tab 回显选中状态 \ 预览结果操作选中状态
    if (activePanel?.value && activePanel.value !== 'manualInput') {
      checkedMap.value = {};
      const checkedList = props.lastValues[activePanel.value];
      if (checkedList) {
        for (const item of checkedList) {
          checkedMap.value[item[firstColumnFieldId.value]] = item;
        }
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
    if (props.isManul) {
      const lastValues: InstanceSelectorValues<T> = {
        [props.activePanelId]: [],
      };
      for (const item of Object.values(checkedMap.value)) {
        lastValues[props.activePanelId].push(item);
      }

      emits('change', {
        ...props.lastValues,
        ...lastValues,
      });
      return;
    }
    const result = Object.values(checkedMap.value).reduce((result, item) => {
      result.push({
        ...item,
      });
      return result;
    }, [] as T[]);

    if (activePanel?.value) {
      emits('change', {
        ...props.lastValues,
        [activePanel.value]: result,
      });
    }
  };

  const handleSelectPageAll = (checked: boolean) => {
    const list = props.isManul ? renderManualData.value : tableData.value;
    if (props.disabledRowConfig) {
      isSelectedAllReal = !isSelectedAllReal;
      for (const data of list) {
        if (!props.disabledRowConfig.handler(data)) {
          handleTableSelectOne(isSelectedAllReal, data);
        }
      }
      return;
    }
    for (const item of list) {
      handleTableSelectOne(checked, item);
    }
  };

  const handleTableSelectOne = (checked: boolean, data: T) => {
    const lastCheckMap = { ...checkedMap.value };
    if (checked) {
      lastCheckMap[data[firstColumnFieldId.value]] = formatValue(data) as T;
    } else {
      delete lastCheckMap[data[firstColumnFieldId.value]];
    }
    checkedMap.value = lastCheckMap;
    triggerChange();
  };

  const handleRowClick = (e: PointerEvent, data: T) => {
    if (props.disabledRowConfig && props.disabledRowConfig.handler(data)) {
      return;
    }
    const checked = checkedMap.value[data[firstColumnFieldId.value]];
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
