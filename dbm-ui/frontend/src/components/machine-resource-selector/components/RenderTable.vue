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
  <div class="machine-resource-selector-render-table">
    <DbQuickSearch
      v-model="searchSelectValue"
      class="mb-12"
      :data="searchSelectData"
      parse-url />
    <DbTable
      ref="table"
      :data-source="dataSource"
      fixed-pagination
      :height="540"
      row-key="ip"
      selectable
      :selected="selected"
      @filter-change="handleFilter"
      @selection="handleSelect">
      <TableColumn
        col-key="ip"
        :min-width="150"
        :title="t('目标 IP')" />
      <TableColumn
        col-key="instance_role"
        :min-width="120"
        :title="t('角色类型')" />
      <TableColumn
        col-key="status"
        :filter="{
          list: statusFilterList,
          showConfirmAndReset: true,
          type: 'multiple',
        }"
        :min-width="120"
        :title="t('状态')">
        <template #default="{ row }: { row: IValue }">
          <DbStatus
            v-if="row.related_instances[0]?.status === 'running'"
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
      <TableColumn
        col-key="related_clusters"
        :min-width="220"
        :title="t('所属集群')">
        <template #default="{ row }: { row: IValue }">
          {{ row.related_clusters[0]?.immute_domain || '--' }}
        </template>
      </TableColumn>
    </DbTable>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { getGlobalMachine } from '@services/source/dbbase';

  import { useGlobalBizs } from '@stores';

  import DbTable from '@components/db-table/IndexNew.vue';

  type Parameters = ServiceParameters<typeof getGlobalMachine>;
  export type IValue = ServiceReturnType<typeof getGlobalMachine>['results'][0];

  interface Props {
    params: Parameters;
  }

  const props = defineProps<Props>();

  const selected = defineModel<Partial<IValue>[]>('selected', {
    required: true,
  });

  const { t } = useI18n();
  const { getBizInfoById } = useGlobalBizs();

  const searchSelectData = [
    {
      id: 'ip',
      name: 'IP',
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

  const searchSelectValue = ref<Record<string, string>>({});
  const dbTableRef = useTemplateRef('table');

  watchEffect(() => {
    dbTableRef.value?.fetchData(searchSelectValue.value);
  });

  const dataSource = (params: Parameters) =>
    getGlobalMachine({
      ...props.params,
      ...params,
    });

  const handleFilter = (filterValue: Record<string, string[]>) => {
    dbTableRef.value?.fetchData({
      status: filterValue.status?.join(','),
    });
  };

  const handleSelect = (_values: string[], rows: IValue[]) => {
    selected.value = rows;
  };
</script>

<style lang="less">
  .machine-resource-selector-render-table {
    padding: 12px 24px;

    .t-table__body {
      tr {
        cursor: pointer;
      }
    }
  }
</style>
