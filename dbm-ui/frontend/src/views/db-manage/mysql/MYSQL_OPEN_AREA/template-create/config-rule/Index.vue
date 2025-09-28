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
  <EditableTable
    ref="table"
    class="mt-16 mb-16"
    :model="tableData">
    <EditableRow
      v-for="(item, index) in tableData"
      :key="index">
      <CloneDbColumn
        v-model="item.source_db"
        v-bind="props" />
      <EditableColumn
        :label="t('克隆表结构')"
        :min-width="200"
        readonly>
        <EditableBlock>
          {{ t('所有表') }}
        </EditableBlock>
      </EditableColumn>
      <TableNameColumn
        v-model="item.schema_tblist"
        :cluster-id="props.clusterId"
        field="schema_tblist"
        :label="t('克隆表数据')" />
      <DbPatternColumn
        v-model="item.target_db_pattern"
        v-bind="props" />
    </EditableRow>
  </EditableTable>
</template>

<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';

  import TableNameColumn from '@views/db-manage/mysql/common/edit-table-column/TableNameColumn.vue';

  import CloneDbColumn from './components/CloneDbColumn.vue';
  import DbPatternColumn from './components/DbPatternColumn.vue';

  interface RowData {
    data_tblist: string[];
    schema_tblist: string[];
    source_db: string;
    target_db_pattern: string;
  }

  interface Props {
    clusterId: number;
    data: RowData[];
  }

  interface Exposes {
    getValue: () => Promise<RowData[]>;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');

  const createTableRow = (data = {} as DeepPartial<RowData>) => ({
    data_tblist: (data.data_tblist || []) as RowData['data_tblist'],
    schema_tblist: (data.schema_tblist || []) as RowData['schema_tblist'],
    source_db: data.source_db || '',
    target_db_pattern: data.target_db_pattern || '',
  });

  const tableData = ref<RowData[]>([createTableRow()]);

  watch(
    () => props.data,
    () => {
      if (props.data.length) {
        tableData.value = props.data.map((item) => createTableRow(item));
      }
    },
    {
      immediate: true,
    },
  );

  defineExpose<Exposes>({
    async getValue() {
      const valid = await tableRef.value?.validate();
      if (!valid) {
        return Promise.reject([]);
      }
      return tableData.value as RowData[];
    },
  });
</script>
