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
      :placeholder="t('请输入或选择条件搜索')" />
    <DbOriginalTable
      class="mt-12"
      :columns="columns"
      :data="tableData"
      :max-height="530"
      :pagination="pagination.count < 10 ? false : pagination"
      :remote-pagination="false"
      :settings="tableSettings" />
  </div>
</template>
<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import type { ClusterInfo } from '@services/types';

  import DbStatus from '@components/db-status/index.vue';

  interface DataRow {
    data: ClusterInfo,
  }

  interface Props {
    lastValues: Record<string, ClusterInfo[]>;
    activePanelId: string;
  }

  interface Emits {
    (e: 'change', value: Props['lastValues']): void;
  }

  const props = defineProps<Props>();

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
  });

  const checkedMap = shallowRef({} as Record<string, ClusterInfo>);

  const tableData = shallowRef<ClusterInfo[]>([]);

  const isSelectedAll = computed(() => (tableData.value.length > 0
    // eslint-disable-next-line max-len
    && tableData.value.length === tableData.value.filter(item => checkedMap.value[item.immute_domain]).length
  ));

  const tableSettings = {
    fields: [
      {
        label: t('访问入口'),
        field: 'matser_domain',
      },
      {
        label: t('集群类型'),
        field: 'cluster_type',
      },
      {
        label: t('集群别名'),
        field: 'cluster_name',
      },
      {
        label: t('所属DB模块'),
        field: 'db_module_id',
      },
      {
        label: t('状态'),
        field: 'status',
      },
      {
        label: t('管控区域'),
        field: 'bk_cloud_id',
      },
    ],
    checked: ['matser_domain', 'cluster_type', 'cluster_name', 'db_module_id', 'status', 'bk_cloud_id'],
  };

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
      render: ({ data }: DataRow) => (
        <bk-checkbox
          style="vertical-align: middle;"
          label={true}
          model-value={Boolean(checkedMap.value[data.immute_domain])}
          onChange={(value: boolean) => handleTableSelectOne(value, data)}
        />
      ),
    },
    {
      label: t('访问入口'),
      field: 'master_domain',
      showOverflowTooltip: true,
    },
    {
      label: t('集群类型'),
      field: 'cluster_type',
      showOverflowTooltip: true,
      filter: {
        list: [
          {
            value: 'tendbha',
            text: t('主从'),
          },
          {
            value: 'tendbsingle',
            text: t('单节点'),
          },
        ],
      },
      render: ({ data }: DataRow) => {
        const clusterTypeMap: Record<string, string> = {
          tendbha: t('主从'),
          tendsingle: t('单节点'),
        };
        return <span>{clusterTypeMap[data.cluster_type] ?? '--'}</span>
      },
    },
    {
      label: t('集群别名'),
      field: 'cluster_name',
      showOverflowTooltip: true,
    },
    {
      label: t('所属DB模块'),
      field: 'db_module_id',
      showOverflowTooltip: true,
      render: ({ data }: DataRow) => <span>{data.db_module_name ?? '--'}</span>,
    },
    {
      label: t('状态'),
      field: 'status',
      filter: {
        list: [
          {
            value: 'normal',
            text: t('正常'),
          },
          {
            value: 'abnormal',
            text: t('异常'),
          },
        ],
      },
      render: ({ data }: DataRow) => {
        const statusMap: Record<string, { text: string; theme: string }> = {
          normal: {
            text: t('正常'),
            theme: 'success',
          },
          abnormal: {
            text: t('异常'),
            theme: 'danger',
          },
        };
        const info = statusMap[data.status]
        return info ? <DbStatus theme={info.theme}>{info.text}</DbStatus> : '--';
      },
    },
    {
      minWidth: 100,
      label: t('管控区域'),
      field: 'bk_cloud_id',
      showOverflowTooltip: true,
      render: ({ data }: DataRow) => <span>{data.bk_cloud_name ?? '--'}</span>,
    },
  ];

  watch(() => props.lastValues, () => {
    if (props.activePanelId && props.activePanelId !== 'manual') {
      checkedMap.value = {};
      const checkedList = props.lastValues[props.activePanelId];
      if (checkedList) {
        for (const item of checkedList) {
          checkedMap.value[item.immute_domain] = item;
        }
      }
    }
  }, { immediate: true, deep: true });

  const triggerChange = () => {
    const result = Object.values(checkedMap.value).reduce<ClusterInfo[]>((result, item) => {
      result.push({
        ...item,
      });
      return result;
    }, []);

    if (props.activePanelId) {
      emits('change', {
        ...props.lastValues,
        [props.activePanelId]: result,
      });
    }
  };

  const handleTableSelectOne = (checked: boolean, data: ClusterInfo) => {
    const lastCheckMap = { ...checkedMap.value };
    if (checked) {
      lastCheckMap[data.immute_domain] = data;
    } else {
      delete lastCheckMap[data.immute_domain];
    }
    checkedMap.value = lastCheckMap;
    triggerChange();
  };

  const handleSelectPageAll = (checked: boolean) => {
    const list = tableData.value;
    for (const item of list) {
      handleTableSelectOne(checked, item);
    }
  };
</script>

<style lang="less">
  .selector-render-topo-host {
    padding: 0 24px;

    .bk-table-body {
      tr {
        cursor: pointer;
      }
    }
  }
</style>
