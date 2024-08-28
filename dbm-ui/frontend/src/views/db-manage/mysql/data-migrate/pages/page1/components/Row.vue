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
        ref="sourceClusterRef"
        :model-value="data.clusterData"
        @id-change="handleClusterIdChange" />
    </FixedColumn>
    <td style="padding: 0">
      <RenderClusterNameWithSelector
        ref="targetClustersRef"
        :data="data.targetClusters"
        :source-cluster-id="data.clusterData.id"
        @change="handleTargetClusterChange" />
    </td>
    <td style="padding: 0">
      <RenderCloneType
        ref="cloneTypeRef"
        :model-value="data.cloneType" />
    </td>
    <td style="padding: 0">
      <RenderDbName
        ref="dbPatternsRef"
        check-not-exist
        :cluster-id="data.clusterData.id"
        :model-value="rowInfo.dbs"
        required
        @change="handleDbsChange" />
    </td>
    <td style="padding: 0">
      <RenderDbName
        ref="ignoreDbsRef"
        :cluster-id="data.clusterData.id"
        :model-value="rowInfo.ignoreDbs"
        :required="false"
        @change="handleIgnoreDbsChange" />
    </td>
    <td style="padding: 0">
      <RenderTargetDb
        ref="targetDbsRef"
        :data="rowInfo"
        @change="handleTargetDbsChange" />
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
  import FixedColumn from '@components/render-table/columns/fixed-column/index.vue';
  import OperateColumn from '@components/render-table/columns/operate-column/index.vue';

  import { random } from '@utils';

  export interface IDataRow {
    rowKey: string;
    clusterData: {
      id: number;
      domain: string;
      type: string;
    };
    cloneType?: string;
    dbPatterns?: string[];
    ignoreDbs?: string[];
    targetClusters?: string;
  }

  export interface InfoItem {
    source_cluster: number;
    target_clusters: number[];
    db_list: string[];
  }

  // 创建表格数据
  export const createRowData = (clusterData?: IDataRow['clusterData']) => ({
    rowKey: random(),
    clusterData: clusterData
      ? clusterData
      : {
          id: 0,
          domain: '',
          type: '',
        },
  });
</script>
<script setup lang="ts">
  import RenderCluster from '@views/db-manage/mysql/common/edit-field/ClusterName.vue';
  import RenderDbName from '@views/db-manage/mysql/common/edit-field/DbName.vue';

  import RenderClusterNameWithSelector from './render-target-clusters/Index.vue';
  import RenderTargetDb from './render-target-db/Index.vue';
  import { type DbsType } from './render-target-db/TargetDbPreview.vue';
  import RenderCloneType from './RenderCloneType.vue';

  interface Props {
    data: IDataRow;
    removeable: boolean;
  }

  interface Emits {
    (e: 'add', params: Array<IDataRow>): void;
    (e: 'remove'): void;
    (e: 'clone', value: IDataRow): void;
    (e: 'clusterInputFinish', value: number): void;
  }

  interface Exposes {
    getValue: () => Promise<InfoItem>;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const sourceClusterRef = ref<InstanceType<typeof RenderCluster>>();
  const targetClustersRef = ref<InstanceType<typeof RenderClusterNameWithSelector>>();
  const cloneTypeRef = ref<InstanceType<typeof RenderCloneType>>();
  const dbPatternsRef = ref<InstanceType<typeof RenderDbName>>();
  const ignoreDbsRef = ref<InstanceType<typeof RenderDbName>>();
  const targetDbsRef = ref<InstanceType<typeof RenderTargetDb>>();

  const rowInfo = reactive({
    sourceCluster: '',
    sourceClusterId: 0,
    targetClusters: [] as number[],
    dbs: [] as string[],
    ignoreDbs: [] as string[],
  });

  watch(
    () => props.data.clusterData,
    (clusterData) => {
      rowInfo.sourceClusterId = clusterData.id;
      rowInfo.sourceCluster = clusterData.domain;
    },
    {
      immediate: true,
      deep: true,
    },
  );

  watch(
    () => [props.data?.dbPatterns, props.data?.ignoreDbs],
    ([dbPatterns, ignoreDbs]) => {
      if (dbPatterns) {
        rowInfo.dbs = dbPatterns;
      }
      if (ignoreDbs) {
        rowInfo.ignoreDbs = ignoreDbs;
      }
    },
    {
      immediate: true,
    },
  );

  const handleTargetClusterChange = (list: { id: number }[]) => {
    rowInfo.targetClusters = list.map((item) => item.id);
  };

  const handleClusterIdChange = (clusterId: number) => {
    emits('clusterInputFinish', clusterId);
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

  const handleDbsChange = (list: string[]) => {
    rowInfo.dbs = list;
  };

  const handleIgnoreDbsChange = (list: string[]) => {
    rowInfo.ignoreDbs = list;
  };

  const handleTargetDbsChange = (dbs: DbsType) => {
    rowInfo.dbs = dbs.dbs;
    rowInfo.ignoreDbs = dbs.ignoreDbs;
  };

  const getRowData = () => [
    sourceClusterRef.value!.getValue(),
    targetClustersRef.value!.getValue(),
    dbPatternsRef.value!.getValue('db_patterns'),
    ignoreDbsRef.value!.getValue('ignore_dbs'),
  ];

  const handleClone = () => {
    Promise.allSettled(getRowData()).then((rowData) => {
      const rowInfo = rowData.map((item) => (item.status === 'fulfilled' ? item.value : item.reason));
      emits('clone', {
        ...createRowData(props.data.clusterData),
        dbPatterns: rowInfo[2].db_patterns,
        ignoreDbs: rowInfo[3].ignore_dbs,
      });
    });
  };

  defineExpose<Exposes>({
    async getValue() {
      await Promise.all([
        sourceClusterRef.value!.getValue(),
        targetClustersRef.value!.getValue(),
        dbPatternsRef.value!.getValue('db_patterns'),
        ignoreDbsRef.value!.getValue('ignore_dbs'),
      ]);
      return Promise.all([targetDbsRef.value!.getValue(), cloneTypeRef.value!.getValue()]).then(
        ([dbList, cloneTypeInfo]) => ({
          source_cluster: rowInfo.sourceClusterId,
          target_clusters: rowInfo.targetClusters,
          db_list: dbList,
          ...cloneTypeInfo,
        }),
      );
    },
  });
</script>
