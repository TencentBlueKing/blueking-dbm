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
        :data="data.databases" />
    </td>
    <td style="padding: 0">
      <RenderDbName
        ref="ignoreDbsRef"
        :compare-data="localTablesIgnore"
        :data="localDatabasesIgnore"
        :required="false"
        @change="handleDatabasesIgnoreChange" />
    </td>
    <td style="padding: 0">
      <RenderTableName
        ref="tablePatternsRef"
        :data="data.tables" />
    </td>
    <td style="padding: 0">
      <RenderTableName
        ref="ignoreTablesRef"
        :compare-data="localDatabasesIgnore"
        :data="localTablesIgnore"
        :required="false"
        @change="handleTablesIgnoreChange" />
    </td>
  </tr>
</template>
<script lang="ts">
  import { random } from '@utils';

  export interface IDataRow {
    rowKey: string;
    clusterName: string;
    databases?: string[];
    databasesIgnore?: string[];
    tables?: string[];
    tablesIgnore?: string[];
  }

  // 创建表格数据
  export const createRowData = () => ({
    rowKey: random(),
    clusterName: '',
  });

  interface Props {
    data: IDataRow;
  }

  interface Exposes {
    getValue: () => Promise<any>;
  }
</script>
<script setup lang="ts">
  import RenderDbName from '@views/db-manage/mongodb/components/edit-field/DbName.vue';
  import RenderTableName from '@views/db-manage/mongodb/components/edit-field/TableName.vue';

  const props = defineProps<Props>();

  const dbPatternsRef = ref<InstanceType<typeof RenderDbName>>();
  const ignoreDbsRef = ref<InstanceType<typeof RenderDbName>>();
  const tablePatternsRef = ref<InstanceType<typeof RenderTableName>>();
  const ignoreTablesRef = ref<InstanceType<typeof RenderTableName>>();

  const localDatabasesIgnore = ref<string[]>([]);
  const localTablesIgnore = ref<string[]>([]);

  watchEffect(() => {
    localDatabasesIgnore.value = props.data.databasesIgnore || [];
  });

  watchEffect(() => {
    localTablesIgnore.value = props.data.tablesIgnore || [];
  });

  const handleDatabasesIgnoreChange = (value: string[]) => {
    localDatabasesIgnore.value = value;
  };

  const handleTablesIgnoreChange = (value: string[]) => {
    localTablesIgnore.value = value;
  };

  defineExpose<Exposes>({
    getValue() {
      return Promise.all([
        dbPatternsRef.value!.getValue('db_patterns'),
        ignoreDbsRef.value!.getValue('ignore_dbs', true),
        tablePatternsRef.value!.getValue('table_patterns'),
        ignoreTablesRef.value!.getValue('ignore_tables', true),
      ]).then(([databasesData, tablesData, databasesIgnoreData, tablesIgnoreData]) => ({
        ...databasesData,
        ...tablesData,
        ...databasesIgnoreData,
        ...tablesIgnoreData,
      }));
    },
  });
</script>
