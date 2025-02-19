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
      <DbOriginalTable
        :columns="columns"
        :data="tableData"
        :max-height="530"
        :pagination="pagination.count < 10 ? false : pagination"
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

  import {
    activePanelInjectionKey,
    type InstanceSelectorValues,
    type IValue,
    type PanelListType,
  } from '../../../Index.vue';
  import RenderInstance from '../../common/render-instance/Index.vue';
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
    columnFilterChange,
    handleSearchValueChange,
    searchAttrs,
    searchValue,
    validateSearchValues,
  } = useLinkQueryColumnSerach({
    attrs: ['bk_cloud_id'],
    defaultSearchItem: {
      id: 'ip',
      name: 'IP',
    },
    fetchDataFn: () => fetchResources(),
    isDiscardNondefault: true,
    searchType: ClusterTypes.REDIS,
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

  const columns = computed(() => [
    {
      fixed: 'left',
      label: () => (
        <div style='display:flex;align-items:center'>
          <bk-checkbox
            disabled={mainSelectDisable.value}
            label={true}
            model-value={isSelectedAll.value}
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
      minWidth: 70,
      render: ({ data }: DataRow) => {
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
        return (
          <bk-checkbox
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
      field: 'related_instances',
      label: t('关联实例'),
      render: ({ data }: DataRow) => <RenderInstance data={data.related_instances || []}></RenderInstance>,
      showOverflow: true,
      width: 200,
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
      label: t('云区域'),
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
  ]);

  // const tableSettings = computed(() => ({
  //   fields: columns.value.filter(item => item.field).map(item => ({
  //     label: item.label,
  //     field: item.field,
  //     disabled: firstColumnFieldId.value === item.field,
  //   })),
  //   checked: [firstColumnFieldId.value, 'related_instances', 'bk_cloud_id', 'role', 'status', 'cloud_area', 'alive', 'host_name', 'os_name'],
  // }))

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
          bk_cloud_id: item.bk_cloud_id,
          bk_host_id: item.bk_host_id,
          cluster_id: item.related_clusters[0].id,
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
