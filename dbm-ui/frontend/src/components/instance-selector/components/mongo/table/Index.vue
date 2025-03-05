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
        :max-height="520"
        :pagination="pagination.count < 10 ? false : pagination"
        :settings="tableSetting"
        :show-overflow="false"
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
  import type { Ref } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { useLinkQueryColumnSerach } from '@hooks';

  import { ClusterTypes } from '@common/const';

  import DbStatus from '@components/db-status/index.vue';
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
    columnFilterChange,
    handleSearchValueChange,
    searchAttrs,
    searchValue,
    validateSearchValues,
  } = useLinkQueryColumnSerach({
    attrs: ['bk_cloud_id'],
    defaultSearchItem: {
      id: 'instance',
      name: t('IP 或 IP:Port'),
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

  const columns = [
    {
      fixed: 'left',
      label: () =>
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
      minWidth: 70,
      render: ({ data }: { data: DataRow }) => {
        if (props.disabledRowConfig && props.disabledRowConfig.handler(data)) {
          return (
            <bk-popover
              placement='top'
              popoverDelay={0}
              theme='dark'>
              {{
                content: () => <span>{props.disabledRowConfig?.tip}</span>,
                default: () => (
                  <bk-checkbox
                    style='vertical-align: middle;'
                    disabled
                  />
                ),
              }}
            </bk-popover>
          );
        }
        return props.multiple ? (
          <bk-checkbox
            label={true}
            model-value={Boolean(checkedMap.value[data[firstColumnFieldId.value]])}
            style='vertical-align: middle;'
            onChange={(value: boolean) => handleTableSelectOne(value, data)}
          />
        ) : (
          <bk-radio
            label={true}
            model-value={Boolean(checkedMap.value[data[firstColumnFieldId.value]])}
            style='vertical-align: middle;'
            onChange={(value: boolean) => handleTableSelectOne(value, data)}
          />
        );
      },
    },
    {
      field: props.firsrColumn?.field ? props.firsrColumn.field : 'instance_address',
      fixed: 'left',
      label: props.firsrColumn?.label ? props.firsrColumn.label : t('实例'),
      minWidth: 160,
    },
    {
      field: 'role',
      label: t('角色'),
      minWidth: 160,
      render: ({ row }: { row: DataRow }) => {
        if (row.cluster_type === ClusterTypes.MONGO_SHARED_CLUSTER && row.machine_type === 'mongodb') {
          return row.shard;
        }
        return row.machine_type;
      },
      rowspan: ({ row }: { row: DataRow }) => {
        if (row.machine_type === 'mongodb') {
          const rowSpan = tableData.value.filter(
            (item) =>
              item.master_domain === row.master_domain &&
              item.machine_type === row.machine_type &&
              item.shard === row.shard,
          ).length;
          return rowSpan > 1 ? rowSpan : 1;
        }
        const rowSpan = tableData.value.filter(
          (item) => item.master_domain === row.master_domain && item.machine_type === row.machine_type,
        ).length;
        return rowSpan > 1 ? rowSpan : 1;
      },
      showOverflow: true,
    },
    {
      field: 'status',
      filter: {
        checked: columnCheckedMap.value.status,
        list: [
          {
            text: t('正常'),
            value: 'running',
          },
          {
            text: t('异常'),
            value: 'unavailable',
          },
          {
            text: t('重建中'),
            value: 'loading',
          },
        ],
      },
      label: t('实例状态'),
      render: ({ data }: DataRow) => {
        const isNormal = props.statusFilter ? props.statusFilter(data) : data.status === 'running';
        const info = isNormal ? { text: t('正常'), theme: 'success' } : { text: t('异常'), theme: 'danger' };
        return <DbStatus theme={info.theme}>{info.text}</DbStatus>;
      },
    },
    {
      field: 'bk_sub_zone',
      label: t('园区'),
      minWidth: 120,
      render: ({ data }: DataRow) => data.bk_sub_zone || '--',
      showOverflow: true,
    },
    {
      field: 'bk_rack_id',
      label: t('机架ID'),
      minWidth: 80,
      render: ({ data }: DataRow) => data.bk_rack_id || '--',
      showOverflow: true,
    },
    {
      field: 'bk_svr_device_cls_name',
      label: t('机型'),
      minWidth: 120,
      render: ({ data }: DataRow) => data.bk_svr_device_cls_name || '--',
      showOverflow: true,
    },
    {
      field: 'bk_cloud_id',
      filter: {
        checked: columnCheckedMap.value.bk_cloud_id,
        list: columnAttrs.value.bk_cloud_id,
      },
      label: t('管控区域'),
      minWidth: 100,
      render: ({ data }: DataRow) => <span>{data.bk_cloud_name ?? '--'}</span>,
      showOverflow: true,
    },
    {
      field: 'alive',
      label: t('Agent状态'),
      minWidth: 100,
      render: ({ data }: DataRow) => {
        const info =
          data.host_info?.alive === 1 ? { text: t('正常'), theme: 'success' } : { text: t('异常'), theme: 'danger' };
        return <DbStatus theme={info.theme}>{info.text}</DbStatus>;
      },
    },
    {
      field: 'host_name',
      label: t('主机名称'),
      render: ({ data }: DataRow) => data.host_info?.host_name || '--',
      showOverflow: true,
    },
    {
      field: 'os_name',
      label: t('OS名称'),
      render: ({ data }: DataRow) => data.host_info?.os_name || '--',
      showOverflow: true,
    },
    {
      field: 'cloud_vendor',
      label: t('所属云厂商'),
      render: ({ data }: DataRow) => data.host_info?.cloud_vendor || '--',
      showOverflow: true,
    },
    {
      field: 'os_type',
      label: t('OS类型'),
      render: ({ data }: DataRow) => data.host_info.os_type || '--',
      showOverflow: true,
    },
    {
      field: 'host_id',
      label: t('主机ID'),
      render: ({ data }: DataRow) => data.host_info?.host_id || '--',
      showOverflow: true,
    },
    {
      field: 'agent_id',
      label: 'Agent ID',
      render: ({ data }: DataRow) => data.host_info?.agent_id || '--',
      showOverflow: true,
    },
  ];

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

  const handleRowClick = (key: number, data: DataRow) => {
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
  }
</style>
