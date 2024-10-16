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
  <div class="selector-render-topo-host">
    <BkInput
      v-model="searchValue"
      clearable
      :placeholder="t('请输入IP')" />
    <BkLoading
      :loading="isLoading"
      :z-index="2">
      <DbOriginalTable
        :columns="columns"
        :data="tableData"
        :max-height="530"
        :pagination="pagination.count < 10 ? false : pagination"
        :settings="settings"
        style="margin-top: 12px"
        @page-limit-change="handeChangeLimit"
        @page-value-change="handleChangePage"
        @refresh="fetchResources"
        @setting-change="updateTableSettings" />
    </BkLoading>
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import DbResourceModel from '@services/model/db-resource/DbResource';

  import { useTableSettings } from '@hooks'

  import { UserPersonalSettings } from '@common/const';

  import DiskPopInfo from '@components/disk-pop-info/DiskPopInfo.vue';
  import HostAgentStatus from '@components/host-agent-status/Index.vue';

  import { useTableData } from './useTableData';

  interface DataRow {
    data: DbResourceModel,
  }

  interface Props {
    lastValues: DbResourceModel[],
    disableHostMethod?: (data: DbResourceModel, list: DbResourceModel[]) => boolean | string
  }

  interface Emits {
    (e: 'change', value: Props['lastValues']): void;
  }

  const props = withDefaults(defineProps<Props>(), {
    disableHostMethod: () => false
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const checkedMap = shallowRef({} as Record<string, DbResourceModel>);

  const {
    isLoading,
    data: tableData,
    pagination,
    searchValue,
    fetchResources,
    handleChangePage,
    handeChangeLimit,
  } = useTableData();

  const isSelectedAll = computed(() => (
    tableData.value.length > 0
    && tableData.value.filter(tableItem => !disableHostMethodHandler(tableItem)).length === Object.values(checkedMap.value).length
  ));

  const columns = [
    {
      width: 60,
      fixed: 'left',
      label: () => (
        <bk-checkbox
          label={true}
          model-value={isSelectedAll.value}
          onChange={handleSelectPageAll}
        />
      ),
      render: ({ data }: DataRow) => {
        const tip = disableHostMethodHandler(data)
        const disableCheck = tip !== false
        return (
          <bk-popover
            theme="dark"
            placement="top"
            popoverDelay={0}
            disabled={!disableCheck}>
            {{
              default: () => (
                <bk-checkbox
                  label={true}
                  model-value={Boolean(checkedMap.value[data.bk_host_id])}
                  onChange={(value: boolean) => handleTableSelectOne(value, data)}
                  style="vertical-align: middle;"
                  disabled={disableCheck} />
              ),
              content: () => <span>{tip}</span>,
            }}
          </bk-popover>
        );
      }
    },
    {
      label: 'IP',
      field: 'ip',
      fixed: 'left',
      with: 120,
    },
    {
      label: t('管控区域'),
      field: 'bk_cloud_name',
      with: 120,
    },
    {
      label: t('Agent 状态'),
      field: 'agent_status',
      with: 100,
      render: ({ data }: {data: DbResourceModel}) => <HostAgentStatus data={data.agent_status} />,
    },
    {
      label: t('所属业务'),
      field: 'for_biz',
      width: 170,
      render: ({ data }: {data: DbResourceModel}) => data.for_biz.bk_biz_name || t('无限制'),
    },
    {
      label: t('所属DB类型'),
      field: 'resource_type',
      width: 150,
      render: ({ data }: {data: DbResourceModel}) => data.resource_type || t('无限制'),
    },
    {
      label: t('机型'),
      field: 'device_class',
      render: ({ data }: {data: DbResourceModel}) => data.device_class || '--',
    },
    {
      label: t('操作系统类型'),
      field: 'os_type',
      render: ({ data }: {data: DbResourceModel}) => data.os_type || '--',
    },
    {
      label: t('地域'),
      field: 'city',
      render: ({ data }: {data: DbResourceModel}) => data.city || '--',
    },
    {
      label: t('园区'),
      field: 'sub_zone',
      render: ({ data }: {data: DbResourceModel}) => data.sub_zone || '--',
    },
    {
      label: t('CPU(核)'),
      field: 'bk_cpu',
    },
    {
      label: t('内存'),
      field: 'bkMemText',
      render: ({ data }: {data: DbResourceModel}) => data.bkMemText || '0 M',
    },
    {
      label: t('磁盘容量(G)'),
      field: 'bk_disk',
      minWidth: 120,
      render: ({ data }: {data: DbResourceModel}) => (
        <DiskPopInfo data={data.storage_device}>
          <span style="line-height: 40px; color: #3a84ff;">
            {data.bk_disk}
          </span>
        </DiskPopInfo>
      ),
    },
  ];

  const defaultSettings = {
    fields: columns.filter(item => item.field).map(item => ({
      label: item.label,
      field: item.field,
      disabled: ['ip', 'for_biz', 'resource_type'].includes(item.field as string),
    })),
    checked: [
      'ip',
      'bk_cloud_name',
      'agent_status',
      'for_biz',
      'resource_type',
    ],
    size: 'small',
  };

  const {
    settings,
    updateTableSettings,
  } = useTableSettings(UserPersonalSettings.RESOURCE_POOL_SELECTOR_SETTINGS, defaultSettings);

  watch(searchValue, () => {
    checkedMap.value = {};
    emits('change', []);
  })

  watch(() => props.lastValues, () => {
    // 切换 tab 回显选中状态 \ 预览结果操作选中状态
    checkedMap.value = props.lastValues.reduce((prevCheckedMap, item) => Object.assign(prevCheckedMap, {
      [item.bk_host_id]: item
    }), {} as Record<string, DbResourceModel>)
  }, { immediate: true, deep: true });

  const disableHostMethodHandler = (data: DbResourceModel) => {
    if (data.isAbnormal) {
      return t('Agent异常无法使用');
    }
    return props.disableHostMethod(data, Object.values(checkedMap.value));
  };

  const handleSelectPageAll = (checked: boolean) => {
    const list = tableData.value;
    for (const data of list) {
      if (disableHostMethodHandler(data)) {
        return;
      }
      handleTableSelectOne(checked, data);
    }
  };

  const handleTableSelectOne = (checked: boolean, data: DbResourceModel) => {
    const lastCheckMap = { ...checkedMap.value };
    if (checked) {
      lastCheckMap[data.bk_host_id] = data;
    } else {
      delete lastCheckMap[data.bk_host_id];
    }
    checkedMap.value = lastCheckMap;
    emits('change', Object.values(checkedMap.value));
  };

  onMounted(() => {
    fetchResources()
  })
</script>

<style lang="less">
  .selector-render-topo-host {
    padding: 0 26px 0 16px;

    .bk-table-body {
      tr {
        cursor: pointer;
      }
    }
  }
</style>
