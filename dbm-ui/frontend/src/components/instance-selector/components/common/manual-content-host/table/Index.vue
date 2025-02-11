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
      <DbOriginalTable
        :columns="columns"
        :data="isManul ? renderManualData : tableData"
        :max-height="530"
        :pagination="pagination.count < 10 ? false : pagination"
        :remote-pagination="isRemotePagination"
        :settings="tableSettings"
        style="margin-top: 12px"
        @page-limit-change="handeChangeLimit"
        @page-value-change="handleChangePage"
        @refresh="fetchResources" />
    </BkLoading>
  </div>
</template>
<script setup lang="tsx">
  import type { Column } from 'bkui-vue/lib/table/props';
  import type { Ref } from 'vue';
  import { useI18n } from 'vue-i18n';

  import DbStatus from '@components/db-status/index.vue';

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
    lastValues: InstanceSelectorValues<IValue>,
    activePanelId?: string,
    clusterId?: number,
    isManul?: boolean,
    manualTableData?: DataRow[];
    isRemotePagination?: TableConfigType['isRemotePagination'],
    firsrColumn?: TableConfigType['firsrColumn'],
    // eslint-disable-next-line vue/no-unused-properties
    roleFilterList?: TableConfigType['roleFilterList'],
    disabledRowConfig?: TableConfigType['disabledRowConfig'],
    // eslint-disable-next-line vue/no-unused-properties
    getTableList?: TableConfigType['getTableList'],
    // eslint-disable-next-line vue/no-unused-properties
    statusFilter?: TableConfigType['statusFilter'],
  }

  interface Emits {
    (e: 'change', value: InstanceSelectorValues<IValue>): void;
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

  const { t } = useI18n();

  const activePanel = inject(activePanelInjectionKey) as Ref<string> | undefined;

  const checkedMap = shallowRef({} as DataRow);

  const initRole = computed(() => props.firsrColumn?.role);
  const firstColumnFieldId = computed(() => (props.firsrColumn?.field || 'ip'));
  const mainSelectDisable = computed(() => (props.disabledRowConfig
    ? tableData.value.filter(data => props.disabledRowConfig?.handler(data)).length === tableData.value.length
    : false)
  );

  const {
    isLoading,
    data: tableData,
    pagination,
    searchValue,
    fetchResources,
    handleChangePage,
    handeChangeLimit,
  } = useTableData<IValue>(initRole);

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
    && tableData.value.length === tableData.value.filter(item => checkedMap.value[item[firstColumnFieldId.value]]).length
  ));

  let isSelectedAllReal = false;

  const firstColumnField = props.firsrColumn?.field ? props.firsrColumn.field : 'instance_address'

  const columns = computed(() => {
    const baseColumns: Column[] = [
      {
        width: 60,
        fixed: 'left',
        label: () => (
        <bk-checkbox
          label={true}
          model-value={isSelectedAll.value}
          disabled={mainSelectDisable.value}
          onClick={(e: Event) => e.stopPropagation()}
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
            onClick={(e: Event) => e.stopPropagation()}
            onChange={(value: boolean) => handleTableSelectOne(value, data)}
          />
          );
        },
      },
      {
        fixed: 'left',
        minWidth: 160,
        label: props.firsrColumn?.label ? props.firsrColumn.label : t('实例'),
        field: firstColumnField,
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

    if (props.activePanelId === 'TendbClusterHost') {
      baseColumns.splice(2, 0, {
        label: t('关联的从库实例'),
        field: 'related_instances',
        showOverflowTooltip: true,
        width: 200,
        render: ({ data }: DataRow) => <RenderInstance data={data.related_instances}></RenderInstance>,
      })
    }

    return baseColumns
  })

  const tableSettings = computed(() => ({
    fields: columns.value.filter(item => item.field).map(item => ({
      label: item.label,
      field: item.field,
      disabled: [firstColumnField, 'related_instances'].includes(item.field as string),
    })),
    checked: [firstColumnField, 'related_instances', 'role', 'status', 'cloud_area', 'alive', 'host_name', 'os_name'],
  }))

  watch(() => props.lastValues, () => {
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
        [activePanel.value]: Object.values(checkedMap.value).map(item => ({
          ...item,
          port: 0,
          instance_address: '',
          cluster_id: item.related_clusters[0].id,
          cluster_type: '',
          master_domain: item.related_clusters[0].immute_domain,
        })),
      });
    }
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
