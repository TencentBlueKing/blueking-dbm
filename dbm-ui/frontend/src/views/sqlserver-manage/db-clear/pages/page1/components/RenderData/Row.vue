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
      <td style="padding: 0">
        <RenderCluster
          ref="clusterRef"
          v-model="localClusterData" />
      </td>
      <td style="padding: 0">
        <RenderClearMode
          ref="clearModeRef"
          :model-value="data.cleanMode" />
      </td>
      <td style="padding: 0">
        <RenderDbName
          ref="dbPatternsRef"
          v-model="localCleanDbsPatterns"
          check-not-exist
          :cluster-id="localClusterData?.id" />
      </td>
      <td style="padding: 0">
        <RenderDbName
          ref="ignoreDbsRef"
          v-model="localCleanIgnoreDbsPatterns"
          check-not-exist
          :cluster-id="localClusterData?.id"
          :required="false" />
      </td>
      <td style="padding: 0">
        <RenderTableName
          ref="tablePatternsRef"
          :cluster-id="localClusterData?.id"
          :model-value="data.cleanTables" />
      </td>
      <td style="padding: 0">
        <RenderTableName
          ref="ignoreTablesRef"
          :cluster-id="localClusterData?.id"
          :model-value="data.ignoreCleanTables"
          :required="false" />
      </td>
      <td style="padding: 0">
        <RenderClearDbName
          ref="ignoreTablesRef"
          v-model:cleanDbsPatterns="localCleanDbsPatterns"
          v-model:cleanIgnoreDbsPatterns="localCleanIgnoreDbsPatterns"
          :cluster-data="localClusterData" />
      </td>
      <OperateColumn
        :removeable="removeable"
        @add="handleAppend"
        @remove="handleRemove" />
    </tr>
  </tbody>
</template>
<script lang="ts">
  import OperateColumn from '@components/render-table/columns/operate-column/index.vue';

  import { random } from '@utils';

  export interface IDataRow {
    rowKey: string;
    clusterData?: {
      id: number;
      domain: string;
      cloudId: number;
    };
    cleanMode: string;
    cleanDbsPatterns: string[];
    cleanIgnoreDbsPatterns: string[];
    cleanTables: string[];
    ignoreCleanTables: string[];
    cleanDbs: string[];
  }

  // 创建表格数据
  export const createRowData = (data = {} as Partial<IDataRow>): IDataRow => ({
    rowKey: random(),
    clusterData: data.clusterData,
    cleanMode: data.cleanMode || '',
    cleanDbsPatterns: data.cleanDbsPatterns || [],
    cleanIgnoreDbsPatterns: data.cleanIgnoreDbsPatterns || [],
    cleanTables: data.cleanTables || [],
    ignoreCleanTables: data.ignoreCleanTables || [],
    cleanDbs: data.cleanDbs || [],
  });
</script>
<script setup lang="ts">
  import RenderDbName from '@views/mysql/common/edit-field/DbName.vue';
  import RenderTableName from '@views/mysql/common/edit-field/TableName.vue';

  import RenderClearDbName from './RenderClearDbName.vue';
  import RenderClearMode from './RenderClearMode.vue';
  import RenderCluster from './RenderCluster.vue';

  interface Props {
    data: IDataRow;
    removeable: boolean;
  }
  interface Emits {
    (e: 'add', params: Array<IDataRow>): void;
    (e: 'remove'): void;
  }

  interface Exposes {
    getValue: () => Promise<any>;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const clusterRef = ref();
  const clearModeRef = ref();
  const dbPatternsRef = ref();
  const ignoreDbsRef = ref();
  const tablePatternsRef = ref();
  const ignoreTablesRef = ref();

  const localClusterData = ref<IDataRow['clusterData']>();
  const localCleanDbsPatterns = ref<IDataRow['cleanDbsPatterns']>([]);
  const localCleanIgnoreDbsPatterns = ref<IDataRow['cleanIgnoreDbsPatterns']>([]);

  watch(
    () => props.data,
    () => {
      if (props.data.clusterData) {
        localClusterData.value = props.data.clusterData;
      }
      if (props.data.cleanDbsPatterns) {
        localCleanDbsPatterns.value = props.data.cleanDbsPatterns;
      }
      if (props.data.cleanIgnoreDbsPatterns) {
        localCleanIgnoreDbsPatterns.value = props.data.cleanIgnoreDbsPatterns;
      }
    },
    {
      immediate: true,
    },
  );

  const handleAppend = () => {
    emits('add', [createRowData()]);
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
        clusterRef.value.getValue(),
        clearModeRef.value.getValue(),
        dbPatternsRef.value.getValue('clean_dbs_patterns'),
        tablePatternsRef.value.getValue('clean_ignore_dbs_patterns'),
        ignoreDbsRef.value.getValue('clean_tables'),
        ignoreTablesRef.value.getValue('ignore_clean_tables'),
      ]).then(([clusterData, clearModeData, dbPatternsData, tablePatternsData, ignoreDbsData, ignoreTablesData]) => ({
        ...clusterData,
        ...clearModeData,
        ...dbPatternsData,
        ...tablePatternsData,
        ...ignoreDbsData,
        ...ignoreTablesData,
      }));
    },
  });
</script>
