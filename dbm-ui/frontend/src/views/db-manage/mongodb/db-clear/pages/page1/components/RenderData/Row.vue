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
        v-if="isShardCluster"
        ref="clusterRef"
        :data="data.clusterName"
        @input-finish="handleInputFinish" />
      <RenderClusterNameWithSelector
        v-else
        ref="clustersRef"
        :cluster-type="clusterType" />
    </td>
    <td style="padding: 0">
      <RenderDropType ref="dropTypeRef" />
    </td>
    <td style="padding: 0">
      <RenderDropIndex ref="dropIndexRef" />
    </td>
    <td style="padding: 0">
      <RenderDbName
        ref="dbPatternsRef"
        :data="data.dbPatterns" />
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
        :data="data.tablePatterns" />
    </td>
    <td style="padding: 0">
      <RenderTableName
        ref="ignoreTablesRef"
        :compare-data="localDatabasesIgnore"
        :data="localTablesIgnore"
        :required="false"
        @change="handleTablesIgnoreChange" />
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
    rowKey: string;
    clusterName: string;
    clusterId: number;
    clusterType: string;
    dbPatterns?: string[];
    tablePatterns?: string[];
    ignoreDbs?: string[];
    ignoreTables?: string[];
  }

  // 创建表格数据
  export const createRowData = () => ({
    rowKey: random(),
    clusterName: '',
    clusterId: 0,
    clusterType: '',
  });
</script>
<script setup lang="ts">
  import { ClusterTypes } from '@common/const';

  import OperateColumn from '@components/render-table/columns/operate-column/index.vue';

  import RenderCluster from '@views/db-manage/mongodb/components/edit-field/ClusterName.vue';
  import RenderClusterNameWithSelector from '@views/db-manage/mongodb/components/edit-field/clusters-with-selector/Index.vue';
  import RenderDbName from '@views/db-manage/mongodb/components/edit-field/DbName.vue';
  import RenderTableName from '@views/db-manage/mongodb/components/edit-field/TableName.vue';

  import RenderDropIndex from './RenderDropIndex.vue';
  import RenderDropType from './RenderDropType.vue';

  interface Props {
    data: IDataRow;
    removeable: boolean;
    clusterType: ClusterTypes;
    isShardCluster: boolean;
  }

  interface Emits {
    (e: 'add'): void;
    (e: 'remove'): void;
    (e: 'clusterInputFinish', value: string): void;
  }

  interface InfoItem {
    cluster_id: number[];
    cluster_type: string;
    ns_filter: {
      db_patterns: string[];
      ignore_dbs: string[];
      table_patterns: string[];
      ignore_tables: string[];
    };
  }

  interface Exposes {
    getValue: () => Promise<InfoItem>;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const clusterRef = ref<InstanceType<typeof RenderCluster>>();
  const clustersRef = ref<InstanceType<typeof RenderClusterNameWithSelector>>();
  const dropTypeRef = ref<InstanceType<typeof RenderDropType>>();
  const dropIndexRef = ref<InstanceType<typeof RenderDropIndex>>();
  const dbPatternsRef = ref<InstanceType<typeof RenderDbName>>();
  const ignoreDbsRef = ref<InstanceType<typeof RenderDbName>>();
  const tablePatternsRef = ref<InstanceType<typeof RenderTableName>>();
  const ignoreTablesRef = ref<InstanceType<typeof RenderTableName>>();
  const localClusterId = ref(0);

  const localDatabasesIgnore = ref<string[]>([]);
  const localTablesIgnore = ref<string[]>([]);

  watchEffect(() => {
    localDatabasesIgnore.value = props.data.ignoreDbs || [];
  });

  watchEffect(() => {
    localTablesIgnore.value = props.data.ignoreTables || [];
  });

  const handleDatabasesIgnoreChange = (value: string[]) => {
    localDatabasesIgnore.value = value;
  };

  const handleTablesIgnoreChange = (value: string[]) => {
    localTablesIgnore.value = value;
  };

  watch(
    () => props.data,
    () => {
      if (props.data.clusterId) {
        localClusterId.value = props.data.clusterId;
      }
    },
    {
      immediate: true,
    },
  );

  const handleInputFinish = (value: string) => {
    emits('clusterInputFinish', value);
  };

  const handleAppend = () => {
    emits('add');
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
        clusterRef.value?.getValue(),
        clustersRef.value?.getValue(),
        dropTypeRef.value!.getValue(),
        dropIndexRef.value!.getValue(),
        dbPatternsRef.value!.getValue('db_patterns'),
        tablePatternsRef.value!.getValue('table_patterns'),
        ignoreDbsRef.value!.getValue('ignore_dbs', true),
        ignoreTablesRef.value!.getValue('ignore_tables', true),
      ]).then(
        ([
          clusterId,
          clusterIds,
          dropType,
          dropIndex,
          dbPatternsData,
          tablePatternsData,
          ignoreDbsData,
          ignoreTablesData,
        ]) =>
          ({
            cluster_ids: props.isShardCluster ? [clusterId] : clusterIds,
            cluster_type: props.clusterType,
            ns_filter: {
              ...dbPatternsData,
              ...tablePatternsData,
              ...ignoreDbsData,
              ...ignoreTablesData,
            },
            ...dropType,
            ...dropIndex,
          }) as unknown as InfoItem,
      );
    },
  });
</script>
