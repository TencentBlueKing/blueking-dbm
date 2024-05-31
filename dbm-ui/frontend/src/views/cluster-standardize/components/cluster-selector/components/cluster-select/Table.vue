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
    <SerachBar
      v-model="searchValue"
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
        :settings="tableSettings"
        style="margin-top: 12px"
        @clear-search="clearSearchValue"
        @column-filter="columnFilterChange"
        @page-limit-change="handeChangeLimit"
        @page-value-change="handleChangePage" />
    </BkLoading>
  </div>
</template>
<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import type BizModuleTopoTree from '@services/model/config/biz-module-topo-tree';
  import TendbhaModel from '@services/model/mysql/tendbha';

  import { useLinkQueryColumnSerach } from '@hooks';

  import { ClusterTypes } from '@common/const';

  import DbStatus from '@components/db-status/index.vue';

  import SerachBar from '@views/cluster-standardize/components/cluster-selector/components/common/SearchBar.vue';

  import { useTableData } from './hooks/useTableData';

  interface DataRow {
    data: TendbhaModel,
  }

  interface Props {
    checked: Record<string, TendbhaModel>;
    selectedTreeNode?: BizModuleTopoTree
  }

  interface Emits {
    (e: 'change', value: Record<string, TendbhaModel>): void;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

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

  const {
    columnAttrs,
    searchAttrs,
    searchValue,
    columnCheckedMap,
    clearSearchValue,
    columnFilterChange,
    validateSearchValues,
    handleSearchValueChange,
  } = useLinkQueryColumnSerach(
    ClusterTypes.TENDBHA,
    ['cluster_type', 'db_module_id', 'bk_cloud_id'],
    () => fetchResources(),
  );

  const checkedMap = shallowRef({} as Record<string, TendbhaModel>);

  const params = computed<{ bk_biz_id?: number; db_module_id?: number }>(() => {
    const base = {}
    if (!props.selectedTreeNode) return base
    const { id, nodeType } =  props.selectedTreeNode as BizModuleTopoTree
    if (!id) return base
    return Object.assign(base, nodeType === 'biz' ? {
      bk_biz_id: id
    }: {
      db_module_id: id
    })
  });

  const {
    isLoading,
    data: tableData,
    pagination,
    fetchResources,
    handleChangePage,
    handeChangeLimit,
  } = useTableData(searchValue, params);

  const isSelectedAll = computed(() => (
    tableData.value.length > 0
    && tableData.value.length === tableData.value
      .filter(item => checkedMap.value[item.master_domain]).length
  ));

  const columns = computed(() => [
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
            model-value={Boolean(checkedMap.value[data.master_domain])}
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
        checked: columnCheckedMap.value.cluster_type,
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
      filter: {
        list: columnAttrs.value.db_module_id,
        checked: columnCheckedMap.value.db_module_id,
      },
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
        checked: columnCheckedMap.value.status,
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
      filter: {
        list: columnAttrs.value.bk_cloud_id,
        checked: columnCheckedMap.value.bk_cloud_id,
      },
      render: ({ data }: DataRow) => <span>{data.bk_cloud_name ?? '--'}</span>,
    },
  ]);

  watch(() => props.checked, (value) => {
    checkedMap.value = {...value}
  }, { immediate: true, deep: true });

  watch(() => params.value, () => fetchResources(), {
    immediate: true,
  });

  const handleSelectPageAll = (checked: boolean) => {
    const list = tableData.value;
    for (const item of list) {
      handleTableSelectOne(checked, item);
    }
  };

  const handleTableSelectOne = (checked: boolean, data: TendbhaModel) => {
    const lastCheckMap = { ...checkedMap.value };
    if (checked) {
      lastCheckMap[data.master_domain] = data;
    } else {
      delete lastCheckMap[data.master_domain];
    }
    checkedMap.value = lastCheckMap;
    emits('change', lastCheckMap);
  };

  defineExpose({
    getCheckedMap: () => checkedMap.value,
  });
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
