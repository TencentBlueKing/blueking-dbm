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
        :columns="columns"
        :data="tableData"
        :filter-value="columnCheckedMap"
        :max-height="520"
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
  import { Checkbox, type PrimaryTableCol } from 'tdesign-vue-next';
  import type { Ref } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { useLinkQueryColumnSerach } from '@hooks';

  import { ClusterTypes } from '@common/const';

  import DbStatus from '@components/db-status/index.vue';
  import EmptyStatus from '@components/empty-status/EmptyStatus.vue';

  import {
    activePanelInjectionKey,
    type InstanceSelectorValues,
    type IValue,
    type PanelListType,
  } from '../../../Index.vue';
  import SerachBar from '../../common/SearchBar.vue';

  import { useTableData } from './useTableData';

  type TableConfigType = Required<PanelListType[number]>['tableConfig'];
  type DataRow = Record<string, any>;

  interface Props {
    clusterId?: number;
    disabledRowConfig?: TableConfigType['disabledRowConfig'];
    firsrColumn?: TableConfigType['firsrColumn'];
    getTableList: NonNullable<TableConfigType['getTableList']>;
    lastValues: InstanceSelectorValues<IValue>;
  }

  type Emits = (e: 'change', value: InstanceSelectorValues<IValue>) => void;

  const props = withDefaults(defineProps<Props>(), {
    clusterId: undefined,
    disabledRowConfig: undefined,
    firsrColumn: undefined,
    isRemotePagination: true,
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
    isDiscardNondefault: true,
    searchType: ClusterTypes.TENDBSINGLE,
  });

  const activePanel = inject(activePanelInjectionKey) as Ref<string> | undefined;

  const checkedMap = shallowRef({} as DataRow);

  const initRole = computed(() => props.firsrColumn?.role);
  const selectClusterId = computed(() => props.clusterId);
  const firstColumnFieldId = computed(() => props.firsrColumn?.field || 'ip');
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
  } = useTableData<IValue>(searchValue, initRole, selectClusterId);

  const isSelectedAll = computed(
    () =>
      tableData.value.length > 0 &&
      tableData.value.length ===
        tableData.value.filter((item) => checkedMap.value[item[firstColumnFieldId.value]]).length,
  );

  // const isSelectedAllReal = false;

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
                  <Checkbox
                    disabled
                    style='vertical-align: middle;'
                  />
                ),
              }}
            </bk-popover>
          );
        }
        return (
          <span onClick={(e: Event) => e.stopPropagation()}>
            <Checkbox
              checked={Boolean(checkedMap.value[row[firstColumnFieldId.value]])}
              style='vertical-align: middle;'
              onChange={(value: boolean) => handleTableSelectOne(value, row as IValue)}
            />
          </span>
        );
      },
      colKey: 'row-select',
      fixed: 'left',
      minWidth: 70,
      title: () => (
        <div style='display:flex;align-items:center'>
          <Checkbox
            checked={isSelectedAll.value}
            disabled={mainSelectDisable.value}
            onChange={handleWholeSelect}
          />
          {/* <bk-popover
            placement="bottom-start"
            theme="light db-table-select-menu"
            arrow={ false }
            trigger='hover'
            v-slots={{
              default: () => <db-icon class="select-menu-flag" type="down-big" />,
              content: () => (
                <div class="db-table-select-plan">
                  <div
                    class="item"
                    onClick={handleWholeSelect}>{t('跨页全选')}</div>
                </div>
              ),
            }}>
          </bk-popover> */}
        </div>
      ),
    },
    {
      colKey: props.firsrColumn?.field ? props.firsrColumn.field : 'instance_address',
      fixed: 'left',
      minWidth: 160,
      title: props.firsrColumn?.label ? props.firsrColumn.label : t('实例'),
    },
    {
      cell: (_, { row }) => {
        const info =
          row.host_info?.alive === 1 ? { text: t('正常'), theme: 'success' } : { text: t('异常'), theme: 'danger' };
        return <DbStatus theme={info.theme}>{info.text}</DbStatus>;
      },
      colKey: 'alive',
      ellipsis: true,
      minWidth: 100,
      title: t('Agent状态'),
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

  const handleFilterChange = (filterValue: Record<string, string[]>) => {
    tableColumnFilterChange(filterValue, {
      bk_cloud_id: {
        list: (columnAttrs.value.bk_cloud_id || []).map((item) => ({
          label: item.text,
          value: item.value,
        })),
        name: t('管控区域'),
      },
    });
  };

  watch(
    () => props.lastValues,
    () => {
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
    if (activePanel?.value) {
      emits('change', {
        ...props.lastValues,
        [activePanel.value]: Object.values(checkedMap.value).map((item) => ({
          ...item,
          // 兼容历史遗留问题（对 cluster_id, master_domain 的特殊处理）
          cluster_id: item.related_clusters[0].id,
          cluster_type: '',
          instance_address: '',
          master_domain: item.related_clusters[0].immute_domain,
          port: 0,
        })),
      });
    }
  };

  // 跨页全选
  const handleWholeSelect = (value: boolean) => {
    if (value) {
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
    } else {
      checkedMap.value = {};
      triggerChange();
    }
  };

  // const handleSelectPageAll = (checked: boolean) => {
  //   const list = tableData.value;
  //   if (props.disabledRowConfig) {
  //     isSelectedAllReal = !isSelectedAllReal;
  //     for (const data of list) {
  //       if (!props.disabledRowConfig.handler(data)) {
  //         handleTableSelectOne(isSelectedAllReal, data);
  //       }
  //     }
  //     return;
  //   }
  //   for (const item of list) {
  //     handleTableSelectOne(checked, item);
  //   }
  // };

  const handleRowClick = ({ row }: { row: DataRow }) => {
    if (props.disabledRowConfig && props.disabledRowConfig.handler(row)) {
      return;
    }

    const isChecked = !!checkedMap.value[row[firstColumnFieldId.value]];
    handleTableSelectOne(!isChecked, row as IValue);
  };

  const handleTableSelectOne = (checked: boolean, data: IValue) => {
    const lastCheckMap = { ...checkedMap.value };
    if (checked) {
      lastCheckMap[data[firstColumnFieldId.value]] = data;
    } else {
      delete lastCheckMap[data[firstColumnFieldId.value]];
    }
    checkedMap.value = lastCheckMap;
    triggerChange();
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
