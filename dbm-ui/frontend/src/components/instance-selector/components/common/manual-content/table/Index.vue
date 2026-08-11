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
    <PrimaryTable
      class="mt-12"
      :columns="columns"
      :data="pageData"
      :max-height="530">
      <template #empty>
        <EmptyStatus
          :is-anomalies="false"
          :is-searching="searchValue.length > 0"
          @clear-search="handleClearSearch" />
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
  </div>
</template>
<script setup lang="tsx">
  import type { PrimaryTableCol } from 'tdesign-vue-next';
  import { useI18n } from 'vue-i18n';

  import DbStatus from '@components/db-status/index.vue';
  import EmptyStatus from '@components/empty-status/EmptyStatus.vue';

  import { type InstanceSelectorValues, type IValue, type PanelListType } from '../../../../Index.vue';

  type TableConfigType = Required<PanelListType[number]>['tableConfig'];
  type ManualConfigType = Required<PanelListType[number]>['manualConfig'];

  interface Props {
    activePanelId?: string;
    disabledRowConfig?: TableConfigType['disabledRowConfig'];
    fieldFormat?: ManualConfigType['fieldFormat'];
    firsrColumn?: TableConfigType['firsrColumn'];
    lastValues: InstanceSelectorValues<IValue>;
    manualTableData?: IValue[];
    roleFilterList?: TableConfigType['roleFilterList'];
    statusFilter?: TableConfigType['statusFilter'];
  }

  type Emits = (e: 'change', value: Props['lastValues']) => void;

  const props = withDefaults(defineProps<Props>(), {
    activePanelId: 'tendbcluster',
    disabledRowConfig: undefined,
    fieldFormat: undefined,
    firsrColumn: undefined,
    getTableList: undefined,
    manualTableData: () => [],
    roleFilterList: undefined,
    statusFilter: undefined,
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const searchValue = ref('');
  const pagination = reactive({
    align: 'right',
    count: 0,
    current: 1,
    layout: ['total', 'limit', 'list'],
    limit: 10,
    limitList: [10, 20, 50, 100],
  });

  const checkedMap = shallowRef({} as Record<string, IValue>);

  const firstColumnFieldId = computed(() => (props.firsrColumn?.field || 'instance_address') as keyof IValue);
  const renderManualData = computed(() => {
    if (searchValue.value === '') {
      return props.manualTableData;
    }
    return props.manualTableData.filter((item) =>
      (item[firstColumnFieldId.value] as string).includes(searchValue.value),
    );
  });
  // 全量数据在本地分页展示，选中逻辑仍基于全量过滤结果
  const pageData = computed(() => {
    const startIndex = (pagination.current - 1) * pagination.limit;
    return renderManualData.value.slice(startIndex, startIndex + pagination.limit);
  });
  const mainSelectDisable = computed(() =>
    props.disabledRowConfig
      ? renderManualData.value.filter((data) => props.disabledRowConfig?.handler(data)).length ===
        renderManualData.value.length
      : false,
  );

  const isSelectedAll = computed(
    () =>
      renderManualData.value.length > 0 &&
      renderManualData.value.length ===
        renderManualData.value.filter((item) => checkedMap.value[item[firstColumnFieldId.value]]).length,
  );

  let isSelectedAllReal = false;

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
        return (
          <bk-checkbox
            label={true}
            model-value={Boolean(checkedMap.value[row[firstColumnFieldId.value]])}
            style='vertical-align: middle;'
            onChange={(value: boolean) => handleTableSelectOne(value, row as IValue)}
            onClick={(e: Event) => e.stopPropagation()}
          />
        );
      },
      colKey: 'row-select',
      fixed: 'left',
      title: () => (
        <bk-checkbox
          disabled={mainSelectDisable.value}
          label={true}
          model-value={isSelectedAll.value}
          onChange={handleSelectPageAll}
          onClick={(e: Event) => e.stopPropagation()}
        />
      ),
      width: 60,
    },
    {
      colKey: props.firsrColumn?.field ? props.firsrColumn.field : 'instance_address',
      fixed: 'left',
      minWidth: 160,
      title: props.firsrColumn?.label ? props.firsrColumn.label : t('实例'),
    },
    {
      cell: (_, { row }) => <span>{props.fieldFormat?.role ? props.fieldFormat.role[row.role] : row.role}</span>,
      colKey: 'role',
      ellipsis: true,
      filter: props.roleFilterList
        ? {
            list: props.roleFilterList.list.map((item) => ({
              label: item.text,
              value: item.value,
            })),
            showConfirmAndReset: true,
            type: 'multiple',
          }
        : undefined,
      title: t('角色'),
    },
    {
      cell: (_, { row }) => {
        const isNormal = props.statusFilter ? props.statusFilter(row) : row.status === 'running';
        const info = isNormal ? { text: t('正常'), theme: 'success' } : { text: t('异常'), theme: 'danger' };
        return <DbStatus theme={info.theme}>{info.text}</DbStatus>;
      },
      colKey: 'status',
      title: t('实例状态'),
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
  ]);

  watch(
    renderManualData,
    () => {
      pagination.count = renderManualData.value.length;
      pagination.current = 1;
    },
    {
      immediate: true,
    },
  );

  watch(
    () => props.lastValues,
    () => {
      checkedMap.value = {};
      if (props.lastValues[props.activePanelId]) {
        for (const item of Object.values(props.lastValues[props.activePanelId])) {
          checkedMap.value[item[firstColumnFieldId.value]] = item;
        }
      }
    },
    {
      deep: true,
      immediate: true,
    },
  );

  const triggerChange = () => {
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
  };

  watch(searchValue, () => {
    checkedMap.value = {};
    triggerChange();
  });

  const handleClearSearch = () => {
    searchValue.value = '';
  };

  const handleChangePage = (value: number) => {
    pagination.current = value;
  };

  const handeChangeLimit = (value: number) => {
    pagination.limit = value;
    pagination.current = 1;
  };

  const handleSelectPageAll = (checked: boolean) => {
    if (checked) {
      const list = renderManualData.value;
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
    } else {
      checkedMap.value = {};
      triggerChange();
    }
  };

  const handleTableSelectOne = (checked: boolean, data: IValue) => {
    const lastCheckMap = { ...checkedMap.value };
    if (checked) {
      lastCheckMap[data[firstColumnFieldId.value]] = {
        ...data,
      };
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
