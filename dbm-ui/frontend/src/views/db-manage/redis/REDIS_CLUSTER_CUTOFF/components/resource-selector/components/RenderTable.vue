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
  <div class="resource-selector-render-table">
    <DbSearchSelect
      v-model="searchSelectValue"
      class="mb-12"
      :data="searchSelectData" />
    <DbTable
      ref="table"
      :data-source="dataSource"
      fixed-pagination
      :height="550"
      row-key="ip"
      selectable
      :selected="selected"
      @filter-change="handleFilter"
      @selection="handleSelect">
      <TableColumn
        col-key="ip"
        :min-width="120"
        title="IP" />
      <TableColumn
        col-key="instance_role"
        :filter="{
          list: instanceRoleFilterList,
          showConfirmAndReset: true,
          type: 'multiple',
        }"
        :min-width="120"
        :title="t('角色类型')" />
      <TableColumn
        col-key="bk_cloud_name"
        :min-width="100"
        :title="t('云区域')" />
      <TableColumn
        col-key="agent_status"
        :min-width="120"
        :title="t('Agent 状态')">
        <template #default="{ row }: { row: IValue }">
          <DbStatus
            v-if="row.host_info?.alive === 1"
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
        col-key="cluster_type_name"
        :min-width="120"
        :title="t('架构类型')" />
    </DbTable>
  </div>
</template>
<script setup lang="ts">
  import type { SearchSelect } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';

  import { getRedisMachineList } from '@services/source/redis';

  import DbTable from '@components/db-table/IndexNew.vue';

  import { getSearchSelectorParams } from '@utils';

  import { type TopoTreeNode } from './TopoTree.vue';

  type SearchSelectProps = InstanceType<typeof SearchSelect>['$props'];
  type Parameters = ServiceParameters<typeof getRedisMachineList>;
  export type IValue = ServiceReturnType<typeof getRedisMachineList>['results'][0];

  interface Props {
    node?: TopoTreeNode;
  }

  const props = defineProps<Props>();

  const selected = defineModel<Partial<IValue>[]>('selected', {
    required: true,
  });

  const { t } = useI18n();

  const searchSelectData = [
    {
      id: 'ip',
      name: 'IP',
    },
  ];

  const instanceRoleFilterList = [
    {
      label: 'redis_master',
      value: 'redis_master',
    },
    {
      label: 'redis_slave',
      value: 'redis_slave',
    },
    {
      label: 'proxy',
      value: 'proxy',
    },
  ];

  const searchSelectValue = ref<NonNullable<SearchSelectProps['modelValue']>>([]);
  const dbTableRef = useTemplateRef('table');

  const getNodeParams = (node?: TopoTreeNode) => (node?.obj === 'cluster' ? `${node?.id}` : undefined);

  watchEffect(() => {
    dbTableRef.value?.fetchData({
      ...getSearchSelectorParams(searchSelectValue.value),
      cluster_ids: getNodeParams(props.node),
    });
  });

  const dataSource = (params: Parameters) =>
    new Promise((resolve) => {
      getRedisMachineList({
        ...params,
        cluster_ids: getNodeParams(props.node),
      }).then((data) => {
        if (params.cluster_ids === getNodeParams(props.node)) {
          resolve(data);
        }
      });
    });

  const handleFilter = (filterValue: Record<string, string[]>) => {
    const columnFilterParams = Object.keys(filterValue).reduce<Record<string, string>>((result, key) => {
      if (filterValue[key]?.length) {
        Object.assign(result, {
          [key]: filterValue[key].join(','),
        });
      }
      return result;
    }, {});
    dbTableRef.value?.fetchData(columnFilterParams);
  };

  const handleSelect = (_values: string[], rows: IValue[]) => {
    selected.value = rows;
  };
</script>

<style lang="less">
  .resource-selector-render-table {
    padding: 24px;

    .t-table__body {
      tr {
        cursor: pointer;
      }
    }
  }
</style>
