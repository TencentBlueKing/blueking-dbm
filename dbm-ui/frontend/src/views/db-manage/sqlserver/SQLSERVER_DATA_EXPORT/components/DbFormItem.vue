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
  <BkFormItem
    :label="t('目标DB')"
    property="execute_objects"
    required>
    <EditableTable
      ref="editableTableRef"
      :model="modelValue">
      <EditableRow
        v-for="(rowData, index) in modelValue"
        :key="index">
        <DbNameColumn
          v-model="rowData.dbnames"
          :append-rules="dbnamesRules"
          field="dbnames"
          :label="t('查询 DB')"
          :min-width="300"
          required
          :validate-master="false"
          @batch-edit="handleColumnBatchEdit" />
        <TableNameColumn
          v-model="rowData.ignore_dbnames"
          :disabled-method="() => false"
          field="ignore_dbnames"
          :label="t('忽略 DB')"
          :required="false"
          @batch-edit="handleColumnBatchEdit" />
      </EditableRow>
    </EditableTable>
  </BkFormItem>
</template>
<script setup lang="tsx">
  import { watch } from 'vue';
  import { useI18n } from 'vue-i18n';

  import type { Sqlserver } from '@services/model/ticket/ticket';

  import DbNameColumn from '@views/db-manage/sqlserver/common/toolbox-field/db-name-column/Index.vue';
  import TableNameColumn from '@views/db-manage/sqlserver/common/toolbox-field/table-name-column/Index.vue';

  interface Props {
    validateMaster?: boolean;
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<Sqlserver.DataExport['execute_objects']>({
    required: true,
  });

  const { t } = useI18n();

  const editableTableRef = useTemplateRef('editableTableRef');

  const dbnamesRules = [
    {
      message: t('有 master 时只允许一个'),
      trigger: 'change',
      validator: (value: string[]) => {
        if (!props.validateMaster) {
          return true;
        }
        return !(value.includes('master') && value.length > 1);
      },
    },
    {
      message: t('DB名不允许重复'),
      trigger: 'change',
      validator: (value: string[]) => {
        const allDbnames = modelValue.value.flatMap((item) => item.dbnames);
        for (const item of value) {
          if (allDbnames.filter((allItem) => allItem === item).length > 1) {
            return false;
          }
        }
        return true;
      },
    },
  ];

  // 创建表格数据
  const createRowData = (data = {} as Partial<(typeof modelValue.value)[0]>) => ({
    dbnames: data.dbnames || [],
    ignore_dbnames: data.ignore_dbnames || [],
    sql_files: data.sql_files || [],
  });

  watch(
    modelValue,
    () => {
      if (modelValue.value.length < 1) {
        modelValue.value = [createRowData()];
      }
    },
    {
      immediate: true,
    },
  );

  const handleColumnBatchEdit = (value: string[] | string, field: string) => {
    modelValue.value.forEach((item) => {
      Object.assign(item, { [field]: value });
    });
  };

  defineExpose({
    validate: () => editableTableRef.value!.validate(),
  });
</script>
