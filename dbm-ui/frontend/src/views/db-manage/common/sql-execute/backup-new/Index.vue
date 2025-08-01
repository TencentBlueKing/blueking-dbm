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
  <BkFormItem :label="t('执行前备份')">
    <BkSwitcher
      v-model="isNeedBackup"
      size="small"
      theme="primary"
      @change="handleNeedBackupChange" />
  </BkFormItem>
  <BkFormItem
    v-if="isNeedBackup"
    :label="t('备份设置')"
    property="backup"
    required>
    <EditableTable
      ref="editableTable"
      :model="modelValue">
      <EditableRow
        v-for="(rowData, index) in modelValue"
        :key="index">
        <DbNameColumn
          v-model="rowData.db_patterns"
          field="db_patterns"
          :label="t('备份DB')"
          :min-width="300"
          required
          @batch-edit="handleColumnBatchEdit" />
        <BackupSourceColumn
          v-model="rowData.backup_on"
          @batch-edit="handleColumnBatchEdit" />
        <TableNameColumn
          v-model="rowData.table_patterns"
          :disabled-method="() => false"
          field="table_patterns"
          :label="t('备份表名')"
          @batch-edit="handleColumnBatchEdit" />
        <OperationColumn
          :create-row-method="createRowData"
          :table-data="modelValue" />
      </EditableRow>
    </EditableTable>
  </BkFormItem>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import DbNameColumn from '@views/db-manage/mysql/common/toolbox-field/db-name-column/Index.vue';
  import TableNameColumn from '@views/db-manage/mysql/common/toolbox-field/table-name-column/Index.vue';

  import BackupSourceColumn from './components/BackupSourceColumn.vue';

  interface IDataRow {
    backup_on: string;
    db_patterns: string[];
    table_patterns: string[];
  }

  interface Exposes {
    validate: () => Promise<boolean>;
  }

  const modelValue = defineModel<Array<IDataRow>>({
    required: true,
  });

  const { t } = useI18n();

  // 创建表格数据
  const createRowData = (data = {} as Partial<IDataRow>) => ({
    backup_on: 'remote',
    db_patterns: data.db_patterns || [],
    table_patterns: data.table_patterns || [],
  });

  const editableTableRef = useTemplateRef('editableTable');

  const isNeedBackup = ref(false);

  watch(modelValue, () => {
    isNeedBackup.value = modelValue.value.length > 0;
  });

  // 切换开启备份
  const handleNeedBackupChange = (checked: boolean) => {
    if (checked) {
      modelValue.value = [createRowData()];
    } else {
      modelValue.value = [];
    }
  };

  const handleColumnBatchEdit = (value: string[] | string, field: string) => {
    modelValue.value.forEach((item) => {
      Object.assign(item, { [field]: value });
    });
    window.changeConfirm = true;
  };

  defineExpose<Exposes>({
    validate: () => (isNeedBackup.value ? editableTableRef.value!.validate() : Promise.resolve(true)),
  });
</script>
