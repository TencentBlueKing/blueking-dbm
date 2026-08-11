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
    <SerachBar
      v-model="searchValue"
      is-host
      :placeholder="t('请输入或选择条件搜索')"
      :search-attrs="searchAttrs"
      :validate-search-values="validateSearchValues"
      @search-value-change="handleSearchValueChange" />
    <BkLoading
      :loading="isLoading"
      :z-index="2">
      <PrimaryTable
        :bk-ui-settings="tableSetting"
        :columns="columns"
        :data="tableData"
        :filter-value="columnCheckedMap"
        :max-height="520"
        :rowspan-and-colspan="rowspanAndColspan"
        style="margin-top: 12px"
        @filter-change="handleFilterChange"
        @row-click="handleRowClick">
        <template #empty>
          <EmptyStatus
            :is-anomalies="isAnomalies"
            :is-searching="searchValue.length > 0"
            @clear-search="clearSearchValue"
            @refresh="fetchResources" />
        </template>
      </PrimaryTable>
      <div
        v-if="pagination.count >= 10"
        class="table-footer">
        <BkPagination
          v-bind="pagination"
          :model-value="pagination.current"
          @change="handleChangePage"
          @limit-change="handeChangeLimit" />
      </div>
    </BkLoading>
  </div>
</template>
<script setup lang="tsx">
  import type { PrimaryTableCol, PrimaryTableProps } from 'tdesign-vue-next';
  import type { Ref } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { useLinkQueryColumnSerach } from '@hooks';

  import { ClusterTypes } from '@common/const';

  import DbStatus from '@components/db-status/index.vue';
  import EmptyStatus from '@components/empty-status/EmptyStatus.vue';
  import type {
    InstanceSelectorValues,
    IValue,
    PanelListType,
    TableSetting,
  } from '@components/instance-selector/Index.vue';
  import { activePanelInjectionKey } from '@components/instance-selector/Index.vue';

  import SerachBar from '../../common/SearchBar.vue';

  import { useTableData } from './useTableData';

  type TableConfigType = Required<PanelListType[number]>['tableConfig'];

  type DataRow = Record<string, any>;

  interface Props {
    activePanelId?: string;
    clusterId?: number;
    // roleFilterList?: TableConfigType['roleFilterList'],
    disabledRowConfig?: TableConfigType['disabledRowConfig'];
    firsrColumn?: TableConfigType['firsrColumn'];
    getTableList: NonNullable<TableConfigType['getTableList']>;
    isManul?: boolean;
    lastValues: InstanceSelectorValues<IValue>;
    multiple: boolean;
    statusFilter?: TableConfigType['statusFilter'];
    tableSetting: TableSetting;
  }

  type Emits = (e: 'change', value: InstanceSelectorValues<IValue>) => void;

  const props = withDefaults(defineProps<Props>(), {
    activePanelId: 'tendbcluster',
    clusterId: undefined,
    customColums: undefined,
    disabledRowConfig: undefined,
    firsrColumn: undefined,
    isManul: false,
    isRemotePagination: true,
    manualTableData: () => [],
    roleFilterList: undefined,
    statusFilter: undefined,
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const {
    clearSearchValue,
    columnAttrs,
    columnCheckedMap,
    handleSearchValueChange,
    searchAttrs,
    searchValue,
    tableColumnFilterChange,
    validateSearchValues,
  } = useLinkQueryColumnSerach({
    attrs: ['bk_cloud_id'],
    defaultSearchItem: {
      id: 'ip',
      name: 'IP',
    },
    fetchDataFn: () => fetchResources(),
    initAutoFetch: false,
    isDiscardNondefault: true,
    searchType: [ClusterTypes.MONGO_SHARED_CLUSTER, ClusterTypes.MONGO_REPLICA_SET].join(','),
  });

  const activePanel = inject(activePanelInjectionKey) as Ref<string> | undefined;

  const checkedMap = shallowRef({} as DataRow);

  const initRole = computed(() => props.firsrColumn?.role);
  const selectClusterId = computed(() => props.clusterId);
  const firstColumnFieldId = computed(() => (props.firsrColumn?.field || 'instance_address') as keyof IValue);
  const mainSelectDisable = computed(() =>
    props.disabledRowConfig
      ? tableData.value.filter((data) => props.disabledRowConfig?.handler(data)).length === tableData.value.length
      : false,
  );

  const {
    data: tableData,
    fetchResources,
    generateParams,
    handeChangeLimit,
    handleChangePage,
    isAnomalies,
    isLoading,
    pagination,
  } = useTableData<DataRow>(searchValue, selectClusterId, initRole);

  const isSelectedAll = computed(
    () =>
      tableData.value.length > 0 &&
      tableData.value.length ===
        tableData.value.filter((item) => checkedMap.value[item[firstColumnFieldId.value]]).length,
  );

  let isSelectedAllReal = false;

  const statusFilterList = computed(() => [
    {
      label: t('正常'),
      value: 'running',
    },
    {
      label: t('异常'),
      value: 'unavailable',
    },
    {
      label: t('重建中'),
      value: 'loading',
    },
  ]);

  const columns = computed<PrimaryTableCol[]>(() => [
    {
      cell: (_, { row }) => {
        if (props.disabledRowConfig && props.disabledRowConfig.handler(row)) {
          return (
            <bk-popover
              placement='top'
              popoverDelay={0}
              theme='dark'>
              {{
                content: () => <span>{props.disabledRowConfig?.tip}</span>,
                default: () => (
                  <bk-checkbox
                    disabled
                    style='vertical-align: middle;'
                  />
                ),
              }}
            </bk-popover>
          );
        }
        return props.multiple ? (
          <bk-checkbox
            label={true}
            model-value={Boolean(checkedMap.value[row[firstColumnFieldId.value]])}
            style='vertical-align: middle;'
            onChange={(value: boolean) => handleTableSelectOne(value, row)}
          />
        ) : (
          <bk-radio
            label={true}
            model-value={Boolean(checkedMap.value[row[firstColumnFieldId.value]])}
            style='vertical-align: middle;'
            onChange={(value: boolean) => handleTableSelectOne(value, row)}
          />
        );
      },
      colKey: 'row-select',
      fixed: 'left',
      minWidth: 70,
      title: () =>
        props.multiple && (
          <div style='display:flex;align-items:center'>
            <bk-checkbox
              disabled={mainSelectDisable.value}
              label={true}
              model-value={isSelectedAll.value}
              onChange={handleSelectPageAll}
            />
            <bk-popover
              v-slots={{
                content: () => (
                  <div class='db-table-select-plan'>
                    <div
                      class='item'
                      onClick={handleWholeSelect}>
                      {t('跨页全选')}
                    </div>
                  </div>
                ),
                default: () => (
                  <db-icon
                    class='select-menu-flag'
                    type='down-big'
                  />
                ),
              }}
              arrow={false}
              placement='bottom-start'
              theme='light db-table-select-menu'
              trigger='hover'></bk-popover>
          </div>
        ),
    },
    {
      colKey: props.firsrColumn?.field ? props.firsrColumn.field : 'instance_address',
      ellipsis: true,
      fixed: 'left',
      minWidth: 160,
      title: props.firsrColumn?.label ? props.firsrColumn.label : t('实例'),
    },
    {
      cell: (_, { row }) => {
        if (row.cluster_type === ClusterTypes.MONGO_SHARED_CLUSTER && row.machine_type === 'mongodb') {
          return row.shard;
        }
        return row.machine_type;
      },
      colKey: 'role',
      ellipsis: true,
      minWidth: 160,
      title: t('角色'),
    },
    {
      cell: (_, { row }) => {
        const isNormal = props.statusFilter ? props.statusFilter(row) : row.status === 'running';
        const info = isNormal ? { text: t('正常'), theme: 'success' } : { text: t('异常'), theme: 'danger' };
        return <DbStatus theme={info.theme}>{info.text}</DbStatus>;
      },
      colKey: 'status',
      filter: {
        list: statusFilterList.value,
        showConfirmAndReset: true,
        type: 'multiple',
      },
      title: t('状态'),
    },
    {
      cell: (_, { row }) => row.bk_sub_zone || '--',
      colKey: 'bk_sub_zone',
      ellipsis: true,
      minWidth: 120,
      title: t('园区'),
    },
    {
      cell: (_, { row }) => row.bk_rack_id || '--',
      colKey: 'bk_rack_id',
      ellipsis: true,
      minWidth: 80,
      title: t('机架ID'),
    },
    {
      cell: (_, { row }) => row.bk_svr_device_cls_name || '--',
      colKey: 'bk_svr_device_cls_name',
      ellipsis: true,
      minWidth: 120,
      title: t('机型'),
    },
    {
      cell: (_, { row }) => <span>{row.bk_cloud_name ?? '--'}</span>,
      colKey: 'bk_cloud_id',
      ellipsis: true,
      filter: {
        list: (columnAttrs.value.bk_cloud_id || []).map((item) => ({
          label: item.text,
          value: item.value,
        })),
        showConfirmAndReset: true,
        type: 'multiple',
      },
      minWidth: 100,
      title: t('管控区域'),
    },
    {
      cell: (_, { row }) => {
        const info =
          row.host_info?.alive === 1 ? { text: t('正常'), theme: 'success' } : { text: t('异常'), theme: 'danger' };
        return <DbStatus theme={info.theme}>{info.text}</DbStatus>;
      },
      colKey: 'alive',
      minWidth: 100,
      title: t('Agent状态'),
    },
    {
      cell: (_, { row }) => row.host_info?.host_name || '--',
      colKey: 'host_name',
      ellipsis: true,
      title: t('主机名称'),
    },
    {
      cell: (_, { row }) => row.host_info?.os_name || '--',
      colKey: 'os_name',
      ellipsis: true,
      title: t('OS名称'),
    },
    {
      cell: (_, { row }) => row.host_info?.cloud_vendor || '--',
      colKey: 'cloud_vendor',
      ellipsis: true,
      title: t('所属云厂商'),
    },
    {
      cell: (_, { row }) => row.host_info.os_type || '--',
      colKey: 'os_type',
      ellipsis: true,
      title: t('OS类型'),
    },
    {
      cell: (_, { row }) => row.host_info?.host_id || '--',
      colKey: 'host_id',
      ellipsis: true,
      title: t('主机ID'),
    },
    {
      cell: (_, { row }) => row.host_info?.agent_id || '--',
      colKey: 'agent_id',
      ellipsis: true,
      title: 'Agent ID',
    },
  ]);

  const getRoleRowspan = (row: DataRow, rowIndex: number) => {
    const isSameGroup = (item: DataRow) =>
      row.machine_type === 'mongodb'
        ? item.master_domain === row.master_domain && item.machine_type === row.machine_type && item.shard === row.shard
        : item.master_domain === row.master_domain && item.machine_type === row.machine_type;
    // 同组首行合并，其余行隐藏
    if (tableData.value.findIndex(isSameGroup) !== rowIndex) {
      return 0;
    }
    return tableData.value.filter(isSameGroup).length;
  };

  const rowspanAndColspan: PrimaryTableProps['rowspanAndColspan'] = ({ col, row, rowIndex }) => {
    if (col.colKey !== 'role') {
      return {};
    }
    return { rowspan: getRoleRowspan(row as DataRow, rowIndex) };
  };

  const handleFilterChange = (filterValue: Record<string, string[]>) => {
    tableColumnFilterChange(filterValue, {
      bk_cloud_id: {
        list: (columnAttrs.value.bk_cloud_id || []).map((item) => ({
          label: item.text,
          value: item.value,
        })),
        name: t('管控区域'),
      },
      status: {
        list: statusFilterList.value,
        name: t('状态'),
      },
    });
  };

  watch(
    () => props.lastValues,
    () => {
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
    },
    { deep: true, immediate: true },
  );

  watch(
    () => props.clusterId,
    () => {
      if (props.clusterId) {
        fetchResources();
      }
    },
    {
      immediate: true,
    },
  );

  watch(searchValue, () => {
    checkedMap.value = {};
    triggerChange();
  });

  const triggerChange = () => {
    if (props.isManul) {
      const lastValues: InstanceSelectorValues<IValue> = {
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
    }, [] as IValue[]);

    if (activePanel?.value) {
      emits('change', {
        ...props.lastValues,
        [activePanel.value]: result,
      });
    }
  };

  // 跨页全选
  const handleWholeSelect = () => {
    isLoading.value = true;
    const params = generateParams();
    params.limit = -1;
    props
      .getTableList(params)
      .then((data) => {
        data.results.forEach((dataItem: IValue) => {
          if (!props.disabledRowConfig?.handler(dataItem)) {
            handleTableSelectOne(true, dataItem);
          }
        });
      })
      .finally(() => (isLoading.value = false));
  };

  const handleSelectPageAll = (checked: boolean) => {
    const list = tableData.value;
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

  const handleTableSelectOne = (checked: boolean, data: DataRow) => {
    const lastCheckMap = props.multiple ? { ...checkedMap.value } : {};
    if (checked) {
      lastCheckMap[data[firstColumnFieldId.value]] = data;
    } else {
      delete lastCheckMap[data[firstColumnFieldId.value]];
    }
    checkedMap.value = lastCheckMap;
    triggerChange();
  };

  const handleRowClick = ({ row }: { row: DataRow }) => {
    if (props.disabledRowConfig && props.disabledRowConfig.handler(row)) {
      return;
    }
    const checked = checkedMap.value[row[firstColumnFieldId.value]];
    handleTableSelectOne(!checked, row);
  };
</script>

<style lang="less">
  .instance-selector-render-topo-host {
    padding: 0 24px;

    .table-footer {
      display: flex;
      justify-content: flex-end;
      margin-top: 12px;
    }
  }
</style>
