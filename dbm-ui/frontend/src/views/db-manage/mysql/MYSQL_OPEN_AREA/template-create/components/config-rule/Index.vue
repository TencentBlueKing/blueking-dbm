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
  <BatchInput
    :config="batchInputConfig"
    :disabled="!clusterId"
    :tooltips-content="t('请先选择源集群')"
    @change="handleBatchInput" />
  <EditableTable
    :key="tableKey"
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
        field="schema_tblist"
        :label="t('克隆表结构')"
        :min-width="200"
        readonly>
        <EditableBlock>
          {{ t('所有表') }}
        </EditableBlock>
      </EditableColumn>
      <TableNameColumn
        v-model="item.data_tblist"
        :cluster-id="props.clusterId"
        field="data_tblist"
        :label="t('克隆表数据')"
        :placeholder="t('留空表示不克隆表数据')"
        :single="false"
        @batch-edit="handleBatchEdit" />
      <DbPatternColumn
        v-model="item.target_db_pattern"
        :source-db="item.source_db"
        v-bind="props"
        @batch-edit="handleBatchEdit" />
      <OperationColumn
        v-model:table-data="tableData"
        :create-row-method="createTableRow" />
    </EditableRow>
  </EditableTable>
</template>

<script lang="ts" setup>
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { batchSplitRegex } from '@common/regex';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import TableNameColumn from '@views/db-manage/mysql/common/toolbox-field/table-name-column/Index.vue';

  import { random } from '@utils';

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
    reset: () => void;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');

  const createTableRow = (data = {} as DeepPartial<RowData>) => ({
    data_tblist: (data.data_tblist || []) as RowData['data_tblist'],
    schema_tblist: ['*'],
    source_db: data.source_db || '',
    target_db_pattern: data.target_db_pattern || '',
  });

  const tableKey = ref(random());
  const tableData = ref<RowData[]>([createTableRow()]);

  const batchInputConfig = [
    {
      case: 'db1',
      key: 'source_db',
      label: t('克隆 DB'),
    },
    {
      case: 'table1',
      key: 'data_tblist',
      label: t('克隆表数据'),
    },
    {
      case: 'db_{ID}',
      key: 'target_db_pattern',
      label: t('生成的目标DB名'),
    },
  ];

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

  const handleBatchEdit = (value: any, field: string) => {
    tableData.value.forEach((item) => {
      Object.assign(item, { [field]: _.cloneDeep(value) });
    });
  };

  const handleBatchInput = (data: Record<string, any>[], isClear: boolean) => {
    const dataList = data.map((item) =>
      createTableRow({
        data_tblist: item.data_tblist ? item.data_tblist.split(batchSplitRegex) : [],
        source_db: item.source_db || '',
        target_db_pattern: item.target_db_pattern || '',
      }),
    );
    if (isClear) {
      tableKey.value = random();
      tableData.value = [...dataList];
    } else {
      tableData.value = [...(tableData.value[0].source_db ? tableData.value : []), ...dataList];
    }
    setTimeout(() => {
      tableRef.value?.validate();
    }, 200);
  };

  defineExpose<Exposes>({
    getValue() {
      return tableRef.value!.validate().then(() => {
        return tableData.value as RowData[];
      });
    },
    reset() {
      tableData.value = [createTableRow()];
    },
  });
</script>
