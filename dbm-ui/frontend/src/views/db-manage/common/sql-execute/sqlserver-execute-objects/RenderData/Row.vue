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
  <tbody>
    <tr>
      <FixedColumn fixed="left">
        <RenderDbName
          ref="dbnamesRef"
          v-model="localDbnames" />
      </FixedColumn>
      <td style="padding: 0">
        <RenderIgnoreDbName
          ref="ignoreDbnamesRef"
          v-model="localIgnoreDbnames"
          :db-names="localDbnames" />
      </td>
      <td style="padding: 0">
        <RenderSql
          ref="sqlFielsRef"
          v-model="localSqlFiles"
          v-model:import-mode="localImportMode"
          :cluster-version-list="clusterVersionList"
          :db-names="localDbnames"
          :ignore-db-names="localIgnoreDbnames" />
      </td>
      <OperateColumn
        :removeable="removeable"
        @add="handleAppend"
        @remove="handleRemove" />
    </tr>
  </tbody>
</template>
<script lang="ts">
  import { ref } from 'vue';
  import type { ComponentProps } from 'vue-component-type-helpers';

  import FixedColumn from '@components/render-table/columns/fixed-column/index.vue';
  import OperateColumn from '@components/render-table/columns/operate-column/index.vue';

  import RenderSql from '@views/db-manage/common/sql-execute/common/RenderSql/Index.vue';

  import { random } from '@utils';

  import RenderDbName from './RenderDbName.vue';
  import RenderIgnoreDbName from './RenderIgnoreDbName.vue';

  export interface IDataRow {
    rowKey: string;
    dbnames: string[];
    ignore_dbnames: string[];
    sql_files: string[];
    import_mode: ComponentProps<typeof RenderSql>['importMode'];
  }

  // 创建表格数据
  export const createRowData = (data = {} as Partial<IDataRow>) => ({
    rowKey: random(),
    dbnames: data.dbnames || [],
    ignore_dbnames: data.ignore_dbnames || [],
    sql_files: data.sql_files || [],
    import_mode: data.import_mode || 'manual',
  });

  interface Props {
    data: IDataRow;
    removeable: boolean;
    clusterVersionList: string[];
  }
  interface Emits {
    (e: 'add' | 'change', params: IDataRow): void;
    (e: 'remove'): void;
  }

  interface Exposes {
    getValue: () => Promise<IDataRow>;
  }
</script>
<script setup lang="ts">
  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const dbnamesRef = ref();
  const ignoreDbnamesRef = ref();
  const sqlFielsRef = ref();
  const localDbnames = ref<IDataRow['dbnames']>([]);
  const localIgnoreDbnames = ref<IDataRow['ignore_dbnames']>([]);
  const localSqlFiles = ref<IDataRow['sql_files']>([]);
  const localImportMode = ref<IDataRow['import_mode']>('manual');

  watch(
    () => props.data,
    () => {
      localDbnames.value = props.data.dbnames;
      localIgnoreDbnames.value = props.data.ignore_dbnames;
      localImportMode.value = props.data.import_mode || 'manual';
      localSqlFiles.value = props.data.sql_files;
    },
    {
      immediate: true,
    },
  );

  watch([localDbnames, localIgnoreDbnames, localSqlFiles], () => {
    emits('change', {
      rowKey: props.data.rowKey,
      dbnames: localDbnames.value,
      ignore_dbnames: localIgnoreDbnames.value,
      import_mode: localImportMode.value,
      sql_files: localSqlFiles.value,
    });
  });

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
        dbnamesRef.value.getValue(),
        ignoreDbnamesRef.value.getValue(),
        sqlFielsRef.value.getValue(),
      ]).then(([dbnamesData, ignoreDbnamesData, sqlFielsData]) => ({
        ...dbnamesData,
        ...ignoreDbnamesData,
        ...sqlFielsData,
      }));
    },
  });
</script>
<style lang="less" scoped>
  .action-box {
    display: flex;
    align-items: center;

    .action-btn {
      display: flex;
      font-size: 14px;
      color: #c4c6cc;
      cursor: pointer;
      transition: all 0.15s;

      &:hover {
        color: #979ba5;
      }

      &.disabled {
        color: #dcdee5;
        cursor: not-allowed;
      }

      & ~ .action-btn {
        margin-left: 18px;
      }
    }
  }
</style>
