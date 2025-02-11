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

  import {
    type InstanceSelectorValues,
    type IValue,
    type PanelListType,
  } from '../../../../Index.vue';

  type TableConfigType = Required<PanelListType[number]>['tableConfig'];
  type ManualConfigType = Required<PanelListType[number]>['manualConfig'];

  interface DataRow {
    data: IValue,
  }

  interface Props {
    lastValues: InstanceSelectorValues<IValue>,
    activePanelId?: string,
    manualTableData?: IValue[];
    firsrColumn?: TableConfigType['firsrColumn'],
    roleFilterList?: TableConfigType['roleFilterList'],
    disabledRowConfig?: TableConfigType['disabledRowConfig'],
    fieldFormat?: ManualConfigType['fieldFormat'];
    statusFilter?: TableConfigType['statusFilter'],
  }

  interface Emits {
    (e: 'change', value: Props['lastValues']): void;
  }

  const props = withDefaults(defineProps<Props>(), {
    manualTableData: () => ([]),
    firsrColumn: undefined,
    statusFilter: undefined,
    activePanelId: 'tendbcluster',
    disabledRowConfig: undefined,
    fieldFormat: undefined,
    roleFilterList: undefined,
    getTableList: undefined,
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const searchValue = ref('');
  const pagination = ref({
    count: 0,
    current: 1,
    limit: 10,
    limitList: [10, 20, 50, 100],
    align: 'right',
    layout: ['total', 'limit', 'list'],
    remote: false,
  });

  const checkedMap = shallowRef({} as Record<string, IValue>);

  const firstColumnFieldId = computed(() => (props.firsrColumn?.field || 'instance_address') as keyof IValue);
  const renderManualData = computed(() => {
    if (searchValue.value === '') {
      return props.manualTableData;
    }
    return props.manualTableData.filter(item => (
      (item[firstColumnFieldId.value] as string).includes(searchValue.value)
    ));
  });
  const mainSelectDisable = computed(() => (props.disabledRowConfig
    // eslint-disable-next-line max-len
    ? renderManualData.value.filter(data => props.disabledRowConfig?.handler(data)).length === renderManualData.value.length : false));

  const isSelectedAll = computed(() => (renderManualData.value.length > 0
    // eslint-disable-next-line max-len
    && renderManualData.value.length === renderManualData.value.filter(item => checkedMap.value[item[firstColumnFieldId.value]]).length
  ));

  let isSelectedAllReal = false;

  const columns = [
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
      field: props.firsrColumn?.field ? props.firsrColumn.field : 'instance_address',
    },
    {
      label: t('角色'),
      field: 'role',
      showOverflow: true,
      filter: props.roleFilterList,
      render: ({ data }: DataRow) => <span>{props.fieldFormat?.role ? props.fieldFormat.role[data.role] : data.role}</span>
    },
    {
      label: t('实例状态'),
      field: 'status',
      render: ({ data }: DataRow) => {
        const isNormal = props.statusFilter ? props.statusFilter(data) : data.status === 'running';
        const info = isNormal ? { theme: 'success', text: t('正常') } : { theme: 'danger', text: t('异常') };
        return <DbStatus theme={info.theme}>{info.text}</DbStatus>;
      },
    },
    {
      label: t('园区'),
      field: 'bk_sub_zone',
      minWidth: 120,
      showOverflow: true,
      render: ({ data }: DataRow) => data.bk_sub_zone || '--',
    },
    {
      label: t('机架ID'),
      field: 'bk_rack_id',
      minWidth: 80,
      showOverflow: true,
      render: ({ data }: DataRow) => data.bk_rack_id || '--',
    },
    {
      label: t('机型'),
      field: 'bk_svr_device_cls_name',
      minWidth: 120,
      showOverflow: true,
      render: ({ data }: DataRow) => data.bk_svr_device_cls_name || '--',
    },
    {
      minWidth: 100,
      label: t('管控区域'),
      field: 'cloud_area',
      showOverflow: true,
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
      showOverflow: true,
      render: ({ data }: DataRow) => data.host_info?.host_name || '--',
    },
    {
      label: t('OS名称'),
      field: 'os_name',
      showOverflow: true,
      render: ({ data }: DataRow) => data.host_info?.os_name || '--',
    },
    {
      label: t('所属云厂商'),
      field: 'cloud_vendor',
      showOverflow: true,
      render: ({ data }: DataRow) => data.host_info?.cloud_vendor || '--',
    },
    {
      label: t('OS类型'),
      field: 'os_type',
      showOverflow: true,
      render: ({ data }: DataRow) => data.host_info.os_type || '--',
    },
    {
      label: t('主机ID'),
      field: 'host_id',
      showOverflow: true,
      render: ({ data }: DataRow) => data.host_info?.host_id || '--',
    },
    {
      label: 'Agent ID',
      field: 'agent_id',
      showOverflow: true,
      render: ({ data }: DataRow) => data.host_info?.agent_id || '--',
    },
  ];

  watch(() => props.lastValues, () => {
    checkedMap.value = {};
    if (props.lastValues[props.activePanelId]) {
      for (const item of Object.values(props.lastValues[props.activePanelId])) {
        checkedMap.value[item[firstColumnFieldId.value]] = item;
      }
    }
  }, {
    immediate: true,
    deep: true,
  });

  watch(() => props.manualTableData, () => {
    pagination.value.count = props.manualTableData.length;
  }, {
    immediate: true,
  });

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
    checkedMap.value = {}
    triggerChange()
  })

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
        bk_cloud_id: data.host_info.cloud_id,
        bk_cloud_name: data.host_info.cloud_area.name,
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
