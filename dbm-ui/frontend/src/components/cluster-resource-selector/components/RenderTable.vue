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
  <div class="cluster-resource-selector-render-table">
    <DbSearchSelect
      v-model="searchSelectValue"
      class="mb-12"
      :data="searchSelectData" />
    <DbTable
      ref="table"
      :data-source="dataSource"
      fixed-pagination
      :height="540"
      row-key="id"
      selectable
      :selected="selected"
      @filter-change="handleFilter"
      @selection="handleSelect">
      <TableColumn
        col-key="master_domain"
        :min-width="240"
        :title="t('目标集群')" />
      <TableColumn
        col-key="cluster_type_name"
        :min-width="160"
        :title="t('集群类型')" />
      <TableColumn
        col-key="phase"
        :filter="{
          list: statusFilterList,
          showConfirmAndReset: true,
          type: 'multiple',
        }"
        :min-width="120"
        :title="t('状态')">
        <template #default="{ row }: { row: IValue }">
          <DbStatus
            v-if="row.phase === 'online'"
            theme="success">
            {{ t('正常') }}
          </DbStatus>
          <DbStatus
            v-else
            theme="danger">
            {{ t('异常') }}
          </DbStatus>
        </template>
      </TableColumn>
      <TableColumn
        col-key="bk_biz_id"
        :min-width="120"
        :title="t('所属业务')">
        <template #default="{ row }: { row: IValue }">
          {{ getBizInfoById(row.bk_biz_id)?.name || '--' }}
        </template>
      </TableColumn>
    </DbTable>
  </div>
</template>
<script setup lang="ts">
  import type { SearchSelect } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';

  import { getGlobalCluster } from '@services/source/dbbase';

  import { useGlobalBizs } from '@stores';

  import DbTable from '@components/db-table/IndexNew.vue';

  import { getSearchSelectorParams } from '@utils';

  type SearchSelectProps = InstanceType<typeof SearchSelect>['$props'];
  type Parameters = ServiceParameters<typeof getGlobalCluster>;
  export type IValue = ServiceReturnType<typeof getGlobalCluster>[0];

  interface Props {
    params: Parameters;
  }

  const props = defineProps<Props>();

  const selected = defineModel<IValue[]>('selected', {
    required: true,
  });

  const { t } = useI18n();
  const { getBizInfoById } = useGlobalBizs();

  const searchSelectData = [
    {
      id: 'domain',
      name: t('域名'),
    },
  ];

  const statusFilterList = [
    {
      label: t('正常'),
      value: 'running',
    },
    {
      label: t('异常'),
      value: 'unavailable',
    },
  ];

  const searchSelectValue = ref<NonNullable<SearchSelectProps['modelValue']>>([]);
  const dbTableRef = useTemplateRef('table');

  watchEffect(() => {
    dbTableRef.value?.fetchData(getSearchSelectorParams(searchSelectValue.value));
  });

  const dataSource = (params: Parameters) =>
    getGlobalCluster({
      ...props.params,
      ...params,
    });

  const handleFilter = (filterValue: Record<string, string[]>) => {
    dbTableRef.value?.fetchData({
      status: filterValue.phase?.join(','),
    });
  };

  const handleSelect = (_values: string[], rows: IValue[]) => {
    selected.value = rows;
  };
</script>

<style lang="less">
  .cluster-resource-selector-render-table {
    padding: 12px 24px;

    .t-table__body {
      tr {
        cursor: pointer;
      }
    }
  }
</style>
