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
  <div class="mysql-execute-objects-content">
    <BkForm form-type="vertical">
      <BkFormItem
        class="mb-24"
        label=""
        required>
        <EditableTable
          ref="editableTable"
          :model="tableData"
          :rules="dbTableRules">
          <EditableRow
            v-for="(rowData, index) in tableData"
            :key="index">
            <DbNameColumn
              v-model="rowData.dbnames"
              field="dbnames"
              :label="t('变更 DB')"
              required
              :show-batch-edit="false" />
            <DbNameColumn
              v-model="rowData.ignore_dbnames"
              field="ignore_dbnames"
              :label="t('忽略 DB ')"
              :show-batch-edit="false" />
          </EditableRow>
        </EditableTable>
      </BkFormItem>
      <RenderSql
        ref="renderSqlRef"
        v-model="localSqlFiles"
        v-model:grammar-check-result="grammarCheckResult"
        v-model:has-grammar-check="hasGrammarCheck"
        v-model:import-mode="localImportMode"
        :cluster-version-list="clusterVersionList"
        :db-names="localDbnames"
        :ignore-dbnames="localIgnoreDbnames" />
    </BkForm>
  </div>
</template>
<script setup lang="ts">
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import type SqlFileModel from '@views/db-manage/common/mysql-sql-execute/model/SqlFile';
  import DbNameColumn from '@views/db-manage/mysql/common/toolbox-field/db-name-column/Index.vue';

  import RenderSql from './components/RenderSql.vue';

  interface IDataRow {
    dbnames: string[];
    ignore_dbnames: string[];
  }

  interface Props {
    allDbnames: string[];
    clusterVersionList: string[];
    data?: {
      dbnames: string[];
      ignore_dbnames: string[];
      import_mode: ComponentProps<typeof RenderSql>['importMode'];
      sql_files: string[];
    };
  }

  type Emits = (
    e: 'change',
    data: {
      rowData: NonNullable<Props['data']>;
      sqlFileData: Record<string, SqlFileModel>;
    },
  ) => void;

  interface Exposes {
    setInit: (cacheData: Record<string, SqlFileModel>) => void;
    submit: () => Promise<any>;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const disabledConfirm = defineModel<boolean | string>('disabledConfirm', {
    required: true,
  });

  const { t } = useI18n();

  const createRowData = (data = {} as Partial<IDataRow>) => ({
    dbnames: data.dbnames || [],
    ignore_dbnames: data.ignore_dbnames || [],
  });

  const dbTableRules = {
    dbnames: [
      {
        message: t('DB名不允许重复'),
        trigger: 'change',
        validator: (value: string[]) => {
          for (const item of value) {
            if (props.allDbnames.filter((allItem) => allItem === item).length > 0) {
              return false;
            }
          }
          return true;
        },
      },
    ],
  };

  const editableTableRef = useTemplateRef('editableTable');
  const renderSqlRef = useTemplateRef('renderSqlRef');

  const localSqlFiles = ref<NonNullable<Props['data']>['sql_files']>([]);
  const localImportMode = ref<NonNullable<Props['data']>['import_mode']>('manual');
  const tableData = ref<IDataRow[]>([createRowData()]);

  const hasGrammarCheck = ref(false);
  const grammarCheckResult = ref(false);

  const localDbnames = computed(() => tableData.value[0].dbnames);
  const localIgnoreDbnames = computed(() => tableData.value[0].ignore_dbnames);

  const submitButtonTips = computed(() => {
    if (localSqlFiles.value.length < 1) {
      return t('请添加 SQL');
    }

    if (!hasGrammarCheck.value) {
      return t('先执行语法检测');
    }
    if (!grammarCheckResult.value) {
      return t('语法检测失败');
    }

    return false;
  });

  watch(
    () => props.data,
    () => {
      if (props.data) {
        Object.assign(tableData.value[0], createRowData(props.data));
        localImportMode.value = props.data.import_mode || 'manual';
        localSqlFiles.value = props.data.sql_files;
      }
    },
    {
      immediate: true,
    },
  );

  watchEffect(() => {
    disabledConfirm.value = submitButtonTips.value;
  });

  defineExpose<Exposes>({
    setInit(cacheData: Record<string, SqlFileModel>) {
      renderSqlRef.value!.setInit(cacheData);
    },
    submit() {
      return editableTableRef.value!.validate().then((validateResult) => {
        if (validateResult) {
          emits('change', {
            rowData: {
              dbnames: tableData.value[0].dbnames,
              ignore_dbnames: tableData.value[0].ignore_dbnames,
              import_mode: localImportMode.value,
              sql_files: localSqlFiles.value,
            },
            sqlFileData: renderSqlRef.value!.getFileData(),
          });
          return Promise.resolve(true);
        }
        return Promise.resolve(false);
      });
    },
  });
</script>

<style lang="less">
  .mysql-execute-objects-content {
    padding: 20px 24px;
  }
</style>
