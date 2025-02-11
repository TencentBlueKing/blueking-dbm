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
      :placeholder="t('请输入或选择条件搜索')"
      :search-attrs="searchAttrs"
      :validate-search-values="validateSearchValues"
      @search-value-change="handleSearchValueChange" />
    <BkLoading
      :loading="isLoading"
      :z-index="2">
      <DbOriginalTable
        :columns="columns"
        :data="tableData"
        :max-height="530"
        :pagination="pagination.count < 10 ? false : pagination"
        :remote-pagination="isRemotePagination"
        :settings="tableSetting"
        style="margin-top: 12px"
        @clear-search="clearSearchValue"
        @column-filter="columnFilterChange"
        @page-limit-change="handeChangeLimit"
        @page-value-change="handleChangePage"
        @row-click.stop.prevent="handleRowClick" />
    </BkLoading>
  </div>
</template>
<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import { useLinkQueryColumnSerach } from '@hooks';

  import { ClusterTypes } from '@common/const';

  import DbStatus from '@components/db-status/index.vue';

  import {
    activePanelInjectionKey,
    type InstanceSelectorValues,
    type IValue,
    type PanelListType,
    type TableSetting,
  } from '../../../Index.vue';
  import SerachBar from '../../common/SearchBar.vue';

  import { useTableData } from './useTableData';

  type TableConfigType = Required<PanelListType[number]>['tableConfig'];

  interface DataRow {
    data: IValue,
  }

  interface Props {
    lastValues: InstanceSelectorValues<IValue>,
    tableSetting: TableSetting,
    clusterId?: number,
    isRemotePagination?: TableConfigType['isRemotePagination'],
    firsrColumn?: TableConfigType['firsrColumn'],
    roleFilterList?: TableConfigType['roleFilterList'],
    disabledRowConfig?: TableConfigType['disabledRowConfig'],
    getTableList: NonNullable<TableConfigType['getTableList']>,
    statusFilter?: TableConfigType['statusFilter'],
  }

  interface Emits {
    (e: 'change', value: Props['lastValues']): void;
  }

  const props = withDefaults(defineProps<Props>(), {
    clusterId: undefined,
    manualTableData: () => ([]),
    firsrColumn: undefined,
    statusFilter: undefined,
    isRemotePagination: true,
    activePanelId: 'tendbcluster',
    disabledRowConfig: undefined,
    roleFilterList: undefined,
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const {
    columnAttrs,
    searchAttrs,
    searchValue,
    columnCheckedMap,
    clearSearchValue,
    columnFilterChange,
    validateSearchValues,
    handleSearchValueChange,
  } = useLinkQueryColumnSerach({
    searchType: ClusterTypes.TENDBCLUSTER,
    attrs: [
      'bk_cloud_id'
    ],
    fetchDataFn: () => fetchResources(),
    defaultSearchItem: {
      name: t('IP 或 IP:Port'),
      id: 'instance',
    },
    isDiscardNondefault: true,
    initAutoFetch: false
  });

  const activePanel = inject(activePanelInjectionKey);

  const checkedMap = shallowRef({} as Record<string, IValue>);

  const initRole = computed(() => props.firsrColumn?.role);
  const selectClusterId = computed(() => props.clusterId);
  const firstColumnFieldId = computed(() => (props.firsrColumn?.field || 'instance_address') as keyof IValue);
  const mainSelectDisable = computed(() => (props.disabledRowConfig ? tableData.value
    .filter(data => props.disabledRowConfig?.handler(data)).length === tableData.value.length : false));

  const {
    isLoading,
    data: tableData,
    pagination,
    generateParams,
    fetchResources,
    handleChangePage,
    handeChangeLimit,
  } = useTableData<IValue>(searchValue, initRole, selectClusterId);

  const isSelectedAll = computed(() => (
    tableData.value.length > 0
    && tableData.value.length === tableData.value
      .filter(item => checkedMap.value[item[firstColumnFieldId.value]]).length
  ));

  const columns = computed(() => [
    {
      minWidth: 70,
      fixed: 'left',
      label: () => (
        <div style="display:flex;align-items:center">
          <bk-checkbox
            label={true}
            model-value={isSelectedAll.value}
            disabled={mainSelectDisable.value}
            onChange={handleSelectPageAll}
          />
          <bk-popover
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
          </bk-popover>
        </div>
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
      label: props.firsrColumn?.label ? props.firsrColumn.label : t('实例'),
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
      filter: {
        list: [
          {
            value: 'running',
            text: t('正常'),
          },
          {
            value: 'unavailable',
            text: t('异常'),
          },
          {
            value: 'loading',
            text: t('重建中'),
          },
        ],
        checked: columnCheckedMap.value.status,
      },
      render: ({ data }: DataRow) => {
        const isNormal = props.statusFilter ? props.statusFilter(data) : data.status === 'running';
        const info = isNormal ? { theme: 'success', text: t('正常') } : { theme: 'danger', text: t('异常') };
        return <DbStatus theme={info.theme}>{info.text}</DbStatus>;
      },
    },
    {
      minWidth: 100,
      label: t('管控区域'),
      field: 'bk_cloud_id',
      showOverflowTooltip: true,
      filter: {
        list: columnAttrs.value.bk_cloud_id,
        checked: columnCheckedMap.value.bk_cloud_id,
      },
      render: ({ data }:  DataRow) => <span>{data.bk_cloud_name}</span>,
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
  ]);

  watch(() => props.lastValues, () => {
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

    if (activePanel?.value) {
      emits('change', {
        ...props.lastValues,
        [activePanel.value]: Object.values(checkedMap.value).map(item => ({
          ...item,
          // 兼容历史遗留问题（对 bk_cloud_id, bk_cloud_name 的特殊处理）
          bk_cloud_id: item.host_info.cloud_id,
          bk_cloud_name: item.host_info.cloud_area.name,
        })),
      });
    }
  };

  // 跨页全选
  const handleWholeSelect = () => {
    isLoading.value = true;
    const params = generateParams();
    params.limit = -1;
    props.getTableList(params).then((data) => {
      data.results.forEach((dataItem: IValue) => {
        if (!props.disabledRowConfig?.handler(dataItem)) {
          handleTableSelectOne(true, dataItem);
        }
      });
    }).finally(() => isLoading.value = false);
  };

  const handleSelectPageAll = (checked: boolean) => {
    const list = tableData.value;
    if (props.disabledRowConfig) {
      for (const data of list) {
        if (!props.disabledRowConfig.handler(data)) {
          handleTableSelectOne(checked, data);
        }
      }
      return;
    }
    for (const item of list) {
      handleTableSelectOne(checked, item);
    }
  };

  const handleRowClick = (row: unknown, data: IValue) => {
    if (props.disabledRowConfig && props.disabledRowConfig.handler(data)) {
      return;
    }

    const isChecked = !!checkedMap.value[data[firstColumnFieldId.value]];
    handleTableSelectOne(!isChecked, data);
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
  }
</style>
