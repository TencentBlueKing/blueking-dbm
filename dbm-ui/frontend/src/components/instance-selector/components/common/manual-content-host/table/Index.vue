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
      :placeholder="t('请输入主机')" />
    <BkLoading
      :loading="isLoading"
      :z-index="2">
      <PrimaryTable
        :columns="columns"
        :data="isManul ? renderManualData : tableData"
        :max-height="530"
        style="margin-top: 12px">
        <template #empty>
          <EmptyStatus
            :is-anomalies="isAnomalies"
            :is-searching="searchValue.length > 0"
            @clear-search="handleClearSearch"
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

  import DbStatus from '@components/db-status/index.vue';
  import EmptyStatus from '@components/empty-status/EmptyStatus.vue';

  import {
    activePanelInjectionKey,
    type InstanceSelectorValues,
    type IValue,
    type PanelListType,
  } from '../../../../Index.vue';
  import RenderInstance from '../../render-instance/Index.vue';

  import { useTableData } from './useTableData';

  type TableConfigType = Required<PanelListType[number]>['tableConfig'];
  type DataRow = Record<string, any>;

  interface Props {
    activePanelId?: string;
    clusterId?: number;
    disabledRowConfig?: TableConfigType['disabledRowConfig'];
    firsrColumn?: TableConfigType['firsrColumn'];
    // eslint-disable-next-line vue/no-unused-properties
    getTableList?: TableConfigType['getTableList'];
    isManul?: boolean;
    lastValues: InstanceSelectorValues<IValue>;
    manualTableData?: DataRow[];
    // eslint-disable-next-line vue/no-unused-properties
    roleFilterList?: TableConfigType['roleFilterList'];
    // eslint-disable-next-line vue/no-unused-properties
    statusFilter?: TableConfigType['statusFilter'];
  }

  type Emits = (e: 'change', value: InstanceSelectorValues<IValue>) => void;

  const props = withDefaults(defineProps<Props>(), {
    activePanelId: 'tendbcluster',
    clusterId: undefined,
    disabledRowConfig: undefined,
    firsrColumn: undefined,
    getTableList: undefined,
    isManul: false,
    isRemotePagination: true,
    manualTableData: () => [],
    roleFilterList: undefined,
    statusFilter: undefined,
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const activePanel = inject(activePanelInjectionKey) as Ref<string> | undefined;

  const checkedMap = shallowRef({} as DataRow);

  const initRole = computed(() => props.firsrColumn?.role);
  const firstColumnFieldId = computed(() => props.firsrColumn?.field || 'ip');
  const mainSelectDisable = computed(() =>
    props.disabledRowConfig
      ? tableData.value.filter((data) => props.disabledRowConfig?.handler(data)).length === tableData.value.length
      : false,
  );

  const {
    data: tableData,
    fetchResources,
    handeChangeLimit,
    handleChangePage,
    isAnomalies,
    isLoading,
    pagination,
    searchValue,
  } = useTableData<IValue>(initRole);

  const renderManualData = computed(() => {
    if (searchValue.value === '') {
      return props.manualTableData;
    }
    return props.manualTableData.filter((item) =>
      (item[firstColumnFieldId.value] as string).includes(searchValue.value),
    );
  });

  const isSelectedAll = computed(
    () =>
      renderManualData.value.length > 0 &&
      renderManualData.value.length ===
        renderManualData.value.filter((item) => checkedMap.value[item[firstColumnFieldId.value]]).length,
  );

  let isSelectedAllReal = false;

  const firstColumnField = props.firsrColumn?.field ? props.firsrColumn.field : 'instance_address';

  const columns = computed<PrimaryTableCol[]>(() => {
    const baseColumns: PrimaryTableCol[] = [
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
            <Checkbox
              checked={Boolean(checkedMap.value[row[firstColumnFieldId.value]])}
              style='vertical-align: middle;'
              onChange={(value: boolean) => handleTableSelectOne(value, row as IValue)}
            />
          );
        },
        colKey: 'row-select',
        fixed: 'left',
        title: () => (
          <Checkbox
            checked={isSelectedAll.value}
            disabled={mainSelectDisable.value}
            onChange={handleSelectPageAll}
          />
        ),
        width: 60,
      },
      {
        colKey: firstColumnField,
        fixed: 'left',
        minWidth: 160,
        title: props.firsrColumn?.label ? props.firsrColumn.label : t('实例'),
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
        cell: (_, { row }) => row.host_info?.cloud_area?.name || '--',
        colKey: 'cloud_area',
        ellipsis: true,
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
    ];

    if (props.activePanelId === 'TendbClusterHost') {
      baseColumns.splice(2, 0, {
        cell: (_, { row }) => <RenderInstance data={row.related_instances}></RenderInstance>,
        colKey: 'related_instances',
        ellipsis: true,
        minWidth: 200,
        title: t('关联的从库实例'),
      });
    }

    return baseColumns;
  });

  watch(
    () => props.lastValues,
    () => {
      if (props.isManul) {
        checkedMap.value = {};
        if (props.lastValues[props.activePanelId]) {
          for (const item of Object.values(props.lastValues[props.activePanelId])) {
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

  const handleClearSearch = () => {
    searchValue.value = '';
  };

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

    if (activePanel?.value) {
      emits('change', {
        ...props.lastValues,
        [activePanel.value]: Object.values(checkedMap.value).map((item) => ({
          ...item,
          cluster_id: item.related_clusters[0].id,
          cluster_type: '',
          instance_address: '',
          master_domain: item.related_clusters[0].immute_domain,
          port: 0,
        })),
      });
    }
  };

  const handleSelectPageAll = (checked: boolean) => {
    if (checked) {
      const list = renderManualData.value;
      if (props.disabledRowConfig) {
        isSelectedAllReal = !isSelectedAllReal;
        for (const data of list) {
          if (!props.disabledRowConfig.handler(data)) {
            handleTableSelectOne(isSelectedAllReal, data as IValue);
          }
        }
        return;
      }
      for (const item of list) {
        handleTableSelectOne(checked, item as IValue);
      }
    } else {
      checkedMap.value = {};
      triggerChange();
    }
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
