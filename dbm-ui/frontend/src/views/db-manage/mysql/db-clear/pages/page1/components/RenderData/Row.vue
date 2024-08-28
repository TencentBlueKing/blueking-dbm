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
    <FixedColumn fixed="left">
      <RenderCluster
        ref="clusterRef"
        :cluster-types="clusterTypes"
        :model-value="data.clusterData"
        only-one-type
        @id-change="handleClusterIdChange" />
    </FixedColumn>
    <td style="padding: 0">
      <RenderTruncateDataType
        ref="truncateDataTypeRef"
        :model-value="data.truncateDataType"
        @change="handleTruncateDataTypeChange" />
    </td>
    <td style="padding: 0">
      <RenderDbName
        ref="dbPatternsRef"
        check-not-exist
        :cluster-id="localClusterId"
        :model-value="data.dbPatterns" />
    </td>
    <td style="padding: 0">
      <RenderDbName
        ref="ignoreDbsRef"
        :allow-asterisk="false"
        :cluster-id="localClusterId"
        :model-value="data.ignoreDbs"
        :required="false"
        @change="handleIgnoreDbsChange" />
    </td>
    <td style="padding: 0">
      <RenderTableName
        ref="tablePatternsRef"
        :cluster-id="localClusterId"
        :disabled="isDropDatabase"
        :model-value="tablePatterns" />
    </td>
    <td style="padding: 0">
      <RenderTableName
        ref="ignoreTablesRef"
        :allow-asterisk="false"
        :cluster-id="localClusterId"
        :disabled="isDropDatabase"
        :model-value="ignoreTables"
        :required="false" />
    </td>
    <OperateColumn
      :removeable="removeable"
      show-clone
      @add="handleAppend"
      @clone="handleClone"
      @remove="handleRemove" />
  </tr>
</template>
<script lang="ts">
  import OperateColumn from '@components/render-table/columns/operate-column/index.vue';

  import { random } from '@utils';

  export interface IDataRow {
    rowKey: string;
    clusterData?: {
      id: number;
      domain: string;
      type: string;
    };
    truncateDataType: string;
    dbPatterns?: string[];
    tablePatterns?: string[];
    ignoreDbs?: string[];
    ignoreTables?: string[];
  }

  // 创建表格数据
  export const createRowData = (data = {} as Partial<IDataRow>): IDataRow => ({
    rowKey: random(),
    clusterData: data.clusterData,
    truncateDataType: data.truncateDataType || '',
    dbPatterns: data.dbPatterns,
    tablePatterns: data.tablePatterns,
    ignoreDbs: data.ignoreDbs,
    ignoreTables: data.ignoreTables,
  });

  export type IDataRowBatchKey = keyof Omit<IDataRow, 'rowKey' | 'clusterData'>;
</script>
<script setup lang="ts">
  import FixedColumn from '@components/render-table/columns/fixed-column/index.vue';

  import RenderCluster from '@views/db-manage/mysql/common/edit-field/ClusterName.vue';
  import RenderDbName from '@views/db-manage/mysql/common/edit-field/DbName.vue';
  import RenderTableName from '@views/db-manage/mysql/common/edit-field/TableName.vue';

  import RenderTruncateDataType from './RenderTruncateDataType.vue';

  interface Props {
    data: IDataRow;
    removeable: boolean;
    clusterTypes?: string[];
  }
  interface Emits {
    (e: 'add', params: Array<IDataRow>): void;
    (e: 'remove'): void;
    (e: 'clone', value: IDataRow): void;
    (e: 'clusterInputFinish', value: number): void;
  }

  interface Exposes {
    getValue: () => Promise<any>;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const clusterRef = ref();
  const truncateDataTypeRef = ref();
  const dbPatternsRef = ref();
  const ignoreDbsRef = ref();
  const tablePatternsRef = ref();
  const ignoreTablesRef = ref();
  const localClusterId = ref(0);
  const currentTruncateDataType = ref('');
  const tablePatterns = ref<string[]>([]);
  const ignoreTables = ref<string[]>([]);

  const isDropDatabase = computed(() => currentTruncateDataType.value === 'drop_database');

  watch(
    () => props.data.clusterData,
    () => {
      if (props.data.clusterData) {
        localClusterId.value = props.data.clusterData.id;
      }
    },
    {
      immediate: true,
    },
  );

  watchEffect(() => {
    tablePatterns.value = props.data.tablePatterns ?? [];
  });

  watchEffect(() => {
    ignoreTables.value = props.data.ignoreTables ?? [];
  });

  const handleClusterIdChange = (clusterId: number) => {
    localClusterId.value = clusterId;
    emits('clusterInputFinish', clusterId);
  };

  const handleTruncateDataTypeChange = (value: string) => {
    currentTruncateDataType.value = value;
    if (value === 'drop_database') {
      tablePatterns.value = ['*'];
    }
  };

  const handleIgnoreDbsChange = (value: string[]) => {
    // if (isDropDatabase.value && value.length > 0) {
    //   ignoreTables.value = ['*'];
    //   return;
    // }
    ignoreTables.value = [];
  };

  const handleAppend = () => {
    emits('add', [createRowData()]);
  };

  const handleRemove = () => {
    if (props.removeable) {
      return;
    }
    emits('remove');
  };

  const handleClone = () => {
    Promise.allSettled([
      clusterRef.value.getValue(),
      truncateDataTypeRef.value.getValue(),
      dbPatternsRef.value.getValue('db_patterns'),
      tablePatternsRef.value.getValue('table_patterns'),
      ignoreDbsRef.value.getValue('ignore_dbs'),
      ignoreTablesRef.value.getValue('ignore_tables'),
    ]).then((rowData) => {
      const rowInfo = rowData.map((item) => (item.status === 'fulfilled' ? item.value : item.reason));
      emits(
        'clone',
        createRowData({
          rowKey: random(),
          clusterData: props.data.clusterData,
          truncateDataType: rowInfo[1].truncate_data_type,
          dbPatterns: rowInfo[2].db_patterns,
          tablePatterns: rowInfo[3].table_patterns,
          ignoreDbs: rowInfo[4].ignore_dbs,
          ignoreTables: rowInfo[5].ignore_tables,
        }),
      );
    });
  };

  defineExpose<Exposes>({
    getValue() {
      return Promise.all([
        clusterRef.value.getValue(),
        truncateDataTypeRef.value.getValue(),
        dbPatternsRef.value.getValue('db_patterns'),
        tablePatternsRef.value.getValue('table_patterns'),
        ignoreDbsRef.value.getValue('ignore_dbs'),
        ignoreTablesRef.value.getValue('ignore_tables'),
      ]).then(
        ([clusterData, truncateDataTypeData, dbPatternsData, tablePatternsData, ignoreDbsData, ignoreTablesData]) => ({
          ...clusterData,
          ...truncateDataTypeData,
          ...dbPatternsData,
          ...tablePatternsData,
          ...ignoreDbsData,
          ...ignoreTablesData,
        }),
      );
    },
  });
</script>
