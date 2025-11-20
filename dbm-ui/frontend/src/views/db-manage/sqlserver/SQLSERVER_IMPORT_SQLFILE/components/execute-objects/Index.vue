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
  <DbFormItem
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
          :label="t('变更的 DB')"
          :min-width="300"
          required
          :validate-master="false"
          @batch-edit="handleColumnBatchEdit">
          <template #tooltip>
            <span style="font-size: 12px; font-weight: normal; color: #8a8f99">
              （{{ t('如果变更 SQL 是“create database ...”，这个请填写 master') }}）
            </span>
          </template>
        </DbNameColumn>
        <TableNameColumn
          v-model="rowData.ignore_dbnames"
          :disabled-method="() => false"
          field="ignore_dbnames"
          :label="t('忽略的 DB')"
          :required="false"
          @batch-edit="handleColumnBatchEdit" />
        <RenderSql
          v-model="rowData.sql_files"
          v-model:import-mode="rowData.import_mode"
          :cluster-version-list="clusterVersionList"
          :db-names="rowData.dbnames"
          :ignore-db-names="rowData.ignore_dbnames" />
        <OperationColumn
          :create-row-method="createRowData"
          :table-data="modelValue" />
      </EditableRow>
    </EditableTable>
  </DbFormItem>
</template>
<script setup lang="tsx">
  import { watch } from 'vue';
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import { useSqlImport } from '@stores';

  import { DBTypes } from '@common/const';

  import DbNameColumn from '@views/db-manage/sqlserver/common/toolbox-field/db-name-column/Index.vue';
  import TableNameColumn from '@views/db-manage/sqlserver/common/toolbox-field/table-name-column/Index.vue';

  import RenderSql from './components/RenderSql/Index.vue';

  interface IDataRow {
    dbnames: string[];
    ignore_dbnames: string[];
    import_mode: ComponentProps<typeof RenderSql>['importMode'];
    sql_files: string[];
  }

  interface Props {
    clusterVersionList: string[];
    dbType: DBTypes;
    uploadFilePath: string;
  }

  interface Exposes {
    validate: () => Promise<boolean>;
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<Array<IDataRow>>({
    default: () => [],
  });

  const { t } = useI18n();
  const { updateDbType, updateUploadFilePath } = useSqlImport();

  const dbnamesRules = [
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
  const createRowData = (data = {} as Partial<IDataRow>) => ({
    dbnames: data.dbnames || [],
    ignore_dbnames: data.ignore_dbnames || [],
    import_mode: data.import_mode || 'manual',
    sql_files: data.sql_files || [],
  });

  const editableTableRef = useTemplateRef('editableTableRef');

  watch(
    () => [props.uploadFilePath, props.dbType],
    () => {
      updateUploadFilePath(props.uploadFilePath);
      updateDbType(props.dbType);
    },
    {
      immediate: true,
    },
  );

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
    window.changeConfirm = true;
  };

  defineExpose<Exposes>({
    validate: () => editableTableRef.value!.validate(),
  });
</script>
