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
    <BkLoading
      :loading="isLoading"
      :z-index="2">
      <DbOriginalTable
        :columns="generatedColumns"
        :data="tableData"
        :max-height="520"
        :pagination="pagination.count < 10 ? false : pagination"
        :settings="tableSetting"
        :show-overflow="false"
        style="margin-top: 12px"
        @page-limit-change="handeChangeLimit"
        @page-value-change="handleChangePage"
        @row-click.stop.prevent="handleRowClick" />
    </BkLoading>
  </div>
</template>
<script setup lang="tsx">
  import type { Ref } from 'vue';
  import { useI18n } from 'vue-i18n';

  import RenderInstance from '@components/instance-selector/components/common/render-instance/Index.vue';
  import type {
    InstanceSelectorValues,
    IValue,
    PanelListType,
    TableSetting,
  } from '@components/instance-selector/Index.vue';
  import { activePanelInjectionKey } from '@components/instance-selector/Index.vue';

  import { useTableData } from './useTableData';

  type TableConfigType = Required<PanelListType[number]>['tableConfig'];

  type DataRow = Record<string, any>;

  interface Props {
    activePanelId?: string;
    clusterId?: number;
    customColums?: TableConfigType['customColums'];
    // roleFilterList?: TableConfigType['roleFilterList'],
    disabledRowConfig?: TableConfigType['disabledRowConfig'];
    firsrColumn?: TableConfigType['firsrColumn'];
    getTableList: NonNullable<TableConfigType['getTableList']>;
    isManul?: boolean;
    lastValues: InstanceSelectorValues<IValue>;
    multiple: boolean;
    // statusFilter?: TableConfigType['statusFilter'];
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

  const activePanel = inject(activePanelInjectionKey) as Ref<string> | undefined;

  const checkedMap = shallowRef({} as DataRow);

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
  } = useTableData<DataRow>(selectClusterId);

  const isSelectedAll = computed(
    () =>
      tableData.value.length > 0 &&
      tableData.value.length ===
        tableData.value.filter((item) => checkedMap.value[item[firstColumnFieldId.value]]).length,
  );

  let isSelectedAllReal = false;

  const columns = computed(() => [
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
      render: ({ data }: { data: DataRow }) => {
        if (props.disabledRowConfig && props.disabledRowConfig.handler(data, props.lastValues)) {
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
      width: 70,
    },
    {
      field: props.firsrColumn?.field ? props.firsrColumn.field : 'shard_name',
      fixed: 'left',
      label: props.firsrColumn?.label ? props.firsrColumn.label : t('分片'),
      minWidth: 160,
    },
    {
      field: 'related_instance',
      label: t('关联实例'),
      render: ({ data }: { data: DataRow }) => <RenderInstance data={data.related_instance || []}></RenderInstance>,
      // showOverflow: true,
      // width: 200,
    },
  ]);

  const generatedColumns = computed(() => {
    if (props.customColums) {
      return [columns.value[0], ...props.customColums];
    }
    return columns.value;
  });

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
          if (!props.disabledRowConfig?.handler(dataItem, props.lastValues)) {
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
        if (!props.disabledRowConfig.handler(data, props.lastValues)) {
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
    if (props.disabledRowConfig && props.disabledRowConfig.handler(data, props.lastValues)) {
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
