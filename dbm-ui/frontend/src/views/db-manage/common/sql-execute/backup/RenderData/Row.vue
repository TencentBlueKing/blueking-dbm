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
  <tr>
    <td style="padding: 0">
      <RenderDbName
        ref="dbPatternsRef"
        :cluster-id="0"
        :model-value="data.db_patterns"
        @change="handleDbPatternsChange" />
    </td>
    <td style="padding: 0">
      <RenderBackupSource
        ref="backupOnRef"
        :model-value="data.backup_on"
        @change="handleBackupOnChange" />
    </td>
    <td style="padding: 0">
      <RenderTableName
        ref="tablePatternsRef"
        :cluster-id="0"
        :model-value="data.table_patterns"
        @change="handleTablePatternsChange" />
    </td>
    <OperateColumn
      :removeable="removeable"
      @add="handleAppend"
      @remove="handleRemove" />
  </tr>
</template>
<script lang="ts">
  import { random } from '@utils';

  export interface IDataRow {
    rowKey?: string;
    db_patterns: string[];
    backup_on: string;
    table_patterns: string[];
  }

  // 创建表格数据
  export const createRowData = (data = {} as Partial<IDataRow>) => ({
    rowKey: random(),
    db_patterns: data.db_patterns || [],
    backup_on: '',
    table_patterns: data.table_patterns || [],
  });
</script>
<script setup lang="ts">
  import OperateColumn from '@components/render-table/columns/operate-column/index.vue';

  import RenderDbName from '@views/db-manage/mysql/common/edit-field/DbName.vue';
  import RenderTableName from '@views/db-manage/mysql/common/edit-field/TableName.vue';

  import RenderBackupSource from './RenderBackupSource.vue';

  interface Props {
    data: IDataRow;
    removeable: boolean;
  }

  interface Emits {
    (e: 'add', params: IDataRow): void;
    (e: 'remove'): void;
    (e: 'change', value: IDataRow): void;
  }

  interface Exposes {
    getValue: () => Promise<any[]>;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const dbPatternsRef = ref();
  const backupOnRef = ref();
  const tablePatternsRef = ref();

  const dbPatterns = ref();
  const backupOn = ref('');
  const tablePatterns = ref();

  const triggerChange = () => {
    emits('change', {
      rowKey: props.data.rowKey,
      db_patterns: dbPatterns.value,
      backup_on: backupOn.value,
      table_patterns: tablePatterns.value,
    });
  };

  const handleDbPatternsChange = (value: string[]) => {
    dbPatterns.value = value;
    triggerChange();
  };
  const handleBackupOnChange = (value: string) => {
    backupOn.value = value;
    triggerChange();
  };
  const handleTablePatternsChange = (value: string[]) => {
    tablePatterns.value = value;
    triggerChange();
  };

  const handleAppend = () => {
    emits('add', createRowData());
  };

  const handleRemove = () => {
    if (props.removeable) {
      return;
    }
    emits('remove');
  };

  defineExpose<Exposes>({
    getValue() {
      return Promise.all([
        dbPatternsRef.value.getValue('db_patterns'),
        backupOnRef.value.getValue('backup_on'),
        tablePatternsRef.value.getValue('table_patterns'),
      ]);
    },
  });
</script>
