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
        style="margin-top: 12px"
        @page-limit-change="handeChangeLimit"
        @page-value-change="handleChangePage"
        @refresh="fetchResources" />
    </BkLoading>
  </div>
</template>
<script setup lang="tsx">
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

  const columns = computed(() => {
    const baseColumns = [
      {
        fixed: 'left',
        label: () => (
          <bk-checkbox
            disabled={mainSelectDisable.value}
            label={true}
            model-value={isSelectedAll.value}
            onChange={handleSelectPageAll}
            onClick={(e: Event) => e.stopPropagation()}
          />
        ),
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
              onClick={(e: Event) => e.stopPropagation()}
            />
          );
        },
        width: 60,
      },
      {
        field: firstColumnField,
        fixed: 'left',
        label: props.firsrColumn?.label ? props.firsrColumn.label : t('实例'),
        minWidth: 160,
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
        field: 'cloud_area',
        label: t('管控区域'),
        minWidth: 100,
        render: ({ data }: DataRow) => data.host_info?.cloud_area?.name || '--',
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

    if (props.activePanelId === 'TendbClusterHost') {
      baseColumns.splice(2, 0, {
        field: 'related_instances',
        label: t('关联的从库实例'),
        minWidth: 200,
        render: ({ data }: DataRow) => <RenderInstance data={data.related_instances}></RenderInstance>,
        showOverflow: true,
      });
    }

    return baseColumns;
  });

  // const tableSettings = computed(() => ({
  //   fields: columns.value.filter(item => item.field).map(item => ({
  //     label: item.label,
  //     field: item.field,
  //     disabled: [firstColumnField, 'related_instances'].includes(item.field as string),
  //   })),
  //   checked: [firstColumnField, 'related_instances', 'role', 'status', 'cloud_area', 'alive', 'host_name', 'os_name'],
  // }))

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
