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
      <RenderCluster
        ref="clusterRef"
        :model-value="data.clusterData"
        @id-change="handleClusterIdChange"
        @input-create="handleCreate" />
    </td>
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
    };
    truncateDataType: string;
    dbPatterns?: string[];
    tablePatterns?: string[];
    ignoreDbs?: string[];
    ignoreTables?: string[];
  }

  export type IDataRowBatchKey = keyof Omit<IDataRow, 'rowKey' | 'clusterData'>;

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
</script>
<script setup lang="ts">
  import RenderDbName from '@views/db-manage/mysql/common/edit-field/DbName.vue';
  import RenderTableName from '@views/db-manage/mysql/common/edit-field/TableName.vue';

  import RenderCluster from './RenderCluster.vue';
  import RenderTruncateDataType from './RenderTruncateDataType.vue';

  interface Props {
    data: IDataRow;
    removeable: boolean;
  }
  interface Emits {
    (e: 'add', params: Array<IDataRow>): void;
    (e: 'remove'): void;
    (e: 'clone', value: IDataRow): void;
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
    () => props.data,
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

  const handleCreate = (list: Array<string>) => {
    emits(
      'add',
      list.map((domain) =>
        createRowData({
          clusterData: {
            id: 0,
            domain,
          },
        }),
      ),
    );
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

  const getRowData = () => [
    clusterRef.value.getValue(),
    truncateDataTypeRef.value.getValue(),
    dbPatternsRef.value.getValue('db_patterns'),
    tablePatternsRef.value.getValue('table_patterns'),
    ignoreDbsRef.value.getValue('ignore_dbs'),
    ignoreTablesRef.value.getValue('ignore_tables'),
  ];

  const handleClone = () => {
    Promise.allSettled(getRowData()).then((rowData) => {
      const [clusterData, truncateDataTypeData, dbPatternsData, tablePatternsData, ignoreDbsData, ignoreTablesData] =
        rowData.map((item) => (item.status === 'fulfilled' ? item.value : item.reason));
      emits(
        'clone',
        createRowData({
          clusterData: {
            id: clusterData.cluster_id,
            domain: '',
          },
          truncateDataType: truncateDataTypeData.truncate_data_type,
          dbPatterns: dbPatternsData.db_patterns,
          tablePatterns: tablePatternsData.table_patterns,
          ignoreDbs: ignoreDbsData.ignore_dbs,
          ignoreTables: ignoreTablesData.ignore_tables,
        }),
      );
    });
  };

  defineExpose<Exposes>({
    getValue() {
      return Promise.all(getRowData()).then(
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
