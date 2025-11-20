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
    <DbOriginalTable
      class="mt-12"
      :columns="columns"
      :data="renderManualData"
      :max-height="530"
      :pagination="pagination.count < 10 ? false : pagination" />
  </div>
</template>
<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import DbStatus from '@components/db-status/index.vue';

  import { type InstanceSelectorValues, type IValue, type PanelListType } from '../../../../Index.vue';

  type TableConfigType = Required<PanelListType[number]>['tableConfig'];
  type ManualConfigType = Required<PanelListType[number]>['manualConfig'];

  interface DataRow {
    data: IValue;
  }

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
  const pagination = ref({
    align: 'right',
    count: 0,
    current: 1,
    layout: ['total', 'limit', 'list'],
    limit: 10,
    limitList: [10, 20, 50, 100],
    remote: false,
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

  const columns = [
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
      field: props.firsrColumn?.field ? props.firsrColumn.field : 'instance_address',
      fixed: 'left',
      label: props.firsrColumn?.label ? props.firsrColumn.label : t('实例'),
      minWidth: 160,
    },
    {
      field: 'role',
      filter: props.roleFilterList,
      label: t('角色'),
      render: ({ data }: DataRow) => (
        <span>{props.fieldFormat?.role ? props.fieldFormat.role[data.role] : data.role}</span>
      ),
      showOverflow: true,
    },
    {
      field: 'status',
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

  watch(
    () => props.manualTableData,
    () => {
      pagination.value.count = props.manualTableData.length;
    },
    {
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
  }
</style>
