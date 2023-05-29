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
        :data="data.clusterData?.domain"
        @input-finish="handleInputFinish" />
      <RenderClusterNameWithSelector
        v-else
        ref="clustersRef"
        :cluster-type="clusterType" />
    </td>
    <td
      v-if="isShardCluster && backupType === 'mongos'"
      style="padding: 0">
      <RenderHost
        ref="hostRef"
        :cluster-data="data.rowData" />
    </td>

    <td style="padding: 0">
      <RenderDbName
        ref="dbPatternsRef"
        :cluster-id="localClusterId" />
    </td>
    <td style="padding: 0">
      <RenderDbName
        ref="ignoreDbsRef"
        :cluster-id="localClusterId"
        :required="false" />
    </td>
    <td style="padding: 0">
      <RenderTableName
        ref="tablePatternsRef"
        :cluster-id="localClusterId" />
    </td>
    <td style="padding: 0">
      <RenderTableName
        ref="ignoreTablesRef"
        :cluster-id="localClusterId"
        :required="false" />
    </td>
    <OperateColumn
      :removeable="removeable"
      @add="handleAppend"
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
    dbPatterns?: string[];
    tablePatterns?: string[];
    ignoreDbs?: string[];
    ignoreTables?: string[];
    rowData?: MongoDBModel;
  }

  export interface InfoItem {
    backup_host?: string;
    cluster_ids: number[];
    cluster_type: string;
    ns_filter: {
      db_patterns: string[];
      ignore_dbs: string[];
      table_patterns: string[];
      ignore_tables: string[];
    };
  }

  // 创建表格数据
  export const createRowData = (): IDataRow => ({
    rowKey: random(),
  });
</script>
<script setup lang="ts">
  import MongoDBModel from '@services/model/mongodb/mongodb';

  import { ClusterTypes } from '@common/const';

  import RenderCluster from '@views/mongodb-manage/components/edit-field/ClusterName.vue';
  import RenderClusterNameWithSelector from '@views/mongodb-manage/components/edit-field/clusters-with-selector/Index.vue';
  import RenderDbName from '@views/mongodb-manage/components/edit-field/DbName.vue';
  import RenderTableName from '@views/mongodb-manage/components/edit-field/TableName.vue';

  import RenderHost from './RenderHost.vue';

  interface Props {
    data: IDataRow;
    removeable: boolean;
    clusterType: ClusterTypes;
    backupType: string;
    isShardCluster: boolean;
  }
  interface Emits {
    (e: 'add', params: Array<IDataRow>): void;
    (e: 'remove'): void;
    (e: 'clusterInputFinish', value: string): void;
  }

  interface Exposes {
    getValue: () => Promise<InfoItem>;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const clusterRef = ref<InstanceType<typeof RenderCluster>>();
  const clustersRef = ref<InstanceType<typeof RenderClusterNameWithSelector>>();
  const hostRef = ref<InstanceType<typeof RenderHost>>();
  const dbPatternsRef = ref<InstanceType<typeof RenderDbName>>();
  const ignoreDbsRef = ref<InstanceType<typeof RenderDbName>>();
  const tablePatternsRef = ref<InstanceType<typeof RenderTableName>>();
  const ignoreTablesRef = ref<InstanceType<typeof RenderTableName>>();
  const localClusterId = ref(0);

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

  const handleInputFinish = (value: string) => {
    emits('clusterInputFinish', value);
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

  defineExpose<Exposes>({
    getValue() {
      return Promise.all([
        clusterRef.value?.getValue(),
        clustersRef.value?.getValue(),
        hostRef.value?.getValue(),
        dbPatternsRef.value!.getValue('db_patterns'),
        ignoreDbsRef.value!.getValue('ignore_dbs'),
        tablePatternsRef.value!.getValue('table_patterns'),
        ignoreTablesRef.value!.getValue('ignore_tables'),
      ]).then(
        ([clusterId, clusterIds, hostInfo, dbPatternsData, ignoreDbsData, tablePatternsData, ignoreTablesData]) =>
          ({
            cluster_ids: props.isShardCluster ? [clusterId] : clusterIds,
            cluster_type: props.clusterType,
            ns_filter: {
              ...dbPatternsData,
              ...tablePatternsData,
              ...ignoreDbsData,
              ...ignoreTablesData,
            },
            ...hostInfo,
          }) as InfoItem,
      );
    },
  });
</script>
