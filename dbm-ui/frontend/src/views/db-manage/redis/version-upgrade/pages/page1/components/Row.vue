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
      <RenderTargetCluster
        ref="clusterRef"
        :data="data"
        @input-finish="handleClusterInputFinish" />
    </td>
    <td style="padding: 0">
      <RenderText
        :data="data.clusterType"
        :is-loading="data.isLoading"
        :placeholder="t('输入集群后自动生成')" />
    </td>
    <td style="padding: 0">
      <RenderNodeType
        ref="nodeTypeRef"
        :cluster-type="data.clusterType"
        :data="data.nodeType"
        @change="handleNodeTypeChange" />
    </td>
    <td style="padding: 0">
      <RenderCurrentVersion
        :data="data"
        @list-change="handleCurrentListChange" />
    </td>
    <td style="padding: 0">
      <RenderTargetVersion
        ref="targetVersionRef"
        :current-list="currentVersionList"
        :data="data" />
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
  import { useI18n } from 'vue-i18n';

  import RedisModel from '@services/model/redis/redis';

  import OperateColumn from '@components/render-table/columns/operate-column/index.vue';
  import RenderText from '@components/render-table/columns/text-plain/index.vue';

  import { random } from '@utils';

  import RenderTargetCluster from './RenderCluster.vue';
  import RenderCurrentVersion from './RenderCurrentVersion.vue';
  import RenderNodeType from './RenderNodeType.vue';
  import RenderTargetVersion from './RenderTargetVersion.vue';

  export interface IDataRow {
    rowKey: string;
    isLoading: boolean;
    cluster: string;
    clusterId: number;
    nodeType: string;
    clusterType?: string;
    targetVersion?: string;
  }

  export type IDataRowBatchKey = keyof Pick<IDataRow, 'nodeType' | 'targetVersion'>;

  export interface InfoItem {
    cluster_ids: number[];
    node_type: string;
    current_versions: string[];
    target_version: string;
  }

  // 创建表格数据
  export const createRowData = (): IDataRow => ({
    rowKey: random(),
    isLoading: false,
    cluster: '',
    clusterId: 0,
    nodeType: 'Proxy',
  });
</script>
<script setup lang="ts">
  interface Props {
    data: IDataRow;
    removeable: boolean;
    // inputedClusters?: string[];
  }

  interface Emits {
    (e: 'add', params: Array<IDataRow>): void;
    (e: 'remove'): void;
    (e: 'clone', value: IDataRow): void;
    (e: 'nodeTypeChange', value: string): void;
    (e: 'clusterInputFinish', value: RedisModel): void;
  }

  interface Exposes {
    getValue: () => Promise<InfoItem>;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const clusterRef = ref<InstanceType<typeof RenderTargetCluster>>();
  const nodeTypeRef = ref<InstanceType<typeof RenderNodeType>>();
  const targetVersionRef = ref<InstanceType<typeof RenderTargetVersion>>();
  const currentVersionList = ref<string[]>([]);

  const handleCurrentListChange = (versions: string[]) => {
    currentVersionList.value = versions;
  };

  const handleNodeTypeChange = (value: string) => {
    emits('nodeTypeChange', value);
  };

  const handleClusterInputFinish = (value: RedisModel) => {
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

  const handleClone = () => {
    Promise.allSettled([
      clusterRef.value!.getValue(),
      nodeTypeRef.value!.getValue(),
      targetVersionRef.value!.getValue(),
    ]).then((rowData) => {
      const rowInfo = rowData.map((item) => (item.status === 'fulfilled' ? item.value : item.reason));
      emits('clone', {
        ...props.data,
        rowKey: random(),
        isLoading: false,
        nodeType: rowInfo[1],
        targetVersion: rowInfo[2],
      });
    });
  };

  defineExpose<Exposes>({
    getValue() {
      return Promise.all([clusterRef.value!.getValue(true), targetVersionRef.value!.getValue()]).then(
        ([clusterIds, targetVersion]) => ({
          cluster_ids: clusterIds,
          node_type: props.data.nodeType,
          current_versions: currentVersionList.value,
          target_version: targetVersion,
        }),
      );
    },
  });
</script>
