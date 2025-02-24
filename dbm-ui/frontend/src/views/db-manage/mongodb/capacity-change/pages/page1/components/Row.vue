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
        :data="data.clusterName"
        @input-finish="handleInputFinish" />
    </td>
    <td style="padding: 0">
      <RenderCurrentCapacity
        :data="data"
        :is-loading="data.isLoading"
        :spec="data.spec" />
    </td>
    <td style="padding: 0">
      <RenderTargetCapacity
        ref="targetCapacityRef"
        :is-disabled="!data.clusterName"
        :is-loading="data.isLoading"
        :row-data="data" />
    </td>
    <OperateColumn
      :removeable="removeable"
      @add="handleAppend"
      @remove="handleRemove" />
  </tr>
</template>
<script lang="ts">
  import MongoDBModel from '@services/model/mongodb/mongodb';

  import OperateColumn from '@components/render-table/columns/operate-column/index.vue';

  import RenderTargetCluster from '@views/db-manage/mongodb/components/edit-field/ClusterName.vue';

  import { random } from '@utils';

  import RenderCurrentCapacity from './RenderCurrentCapacity.vue';
  import RenderTargetCapacity from './RenderTargetCapacity.vue';

  export interface IDataRow {
    bkCloudId: number;
    clusterId: number;
    clusterName: string;
    clusterType: string;
    currentCapacity: {
      total: number;
      used: number;
    };
    currentSepc: string;
    groupNum?: number;
    isLoading: boolean;
    machineNum: number;
    machinePair: number;
    machineType: string;
    rowKey: string;
    shardNodeCount: number;
    shardNum: number;
    shardSpecName: string;
    spec?: MongoDBModel['mongodb'][number]['spec_config'];
    targetCapacity?: {
      current: number;
      total: number;
      used: number;
    };
    targetGroupNum: number;
    targetShardNum: number;
  }

  export interface InfoItem {
    cluster_id: number;
    resource_spec: {
      mongodb: {
        count: number;
        spec_id: number;
      };
    };
    shard_machine_group: number;
    shard_node_count: number;
    shards_num: number;
  }

  // 创建表格数据
  export const createRowData = (): IDataRow => ({
    bkCloudId: 0,
    clusterId: 0,
    clusterName: '',
    clusterType: '',
    currentCapacity: {
      total: 0,
      used: 0,
    },
    currentSepc: '',
    isLoading: false,
    machineNum: 0,
    machinePair: 0,
    machineType: '',
    rowKey: random(),
    shardNodeCount: 0,
    shardNum: 0,
    shardSpecName: '',
    targetGroupNum: 0,
    targetShardNum: 0,
  });
</script>
<script setup lang="ts">
  interface Props {
    data: IDataRow;
    removeable: boolean;
  }

  interface Emits {
    (e: 'add', params: Array<IDataRow>): void;
    (e: 'remove'): void;
    (e: 'clusterInputFinish', value: string): void;
  }

  interface Exposes {
    getValue: () => Promise<InfoItem>;
  }

  defineProps<Props>();

  const emits = defineEmits<Emits>();

  const clusterRef = ref<InstanceType<typeof RenderTargetCluster>>();
  const targetCapacityRef = ref<InstanceType<typeof RenderTargetCapacity>>();

  const handleInputFinish = (value: string) => {
    emits('clusterInputFinish', value);
  };

  const handleAppend = () => {
    emits('add', [createRowData()]);
  };

  const handleRemove = () => {
    emits('remove');
  };

  defineExpose<Exposes>({
    async getValue() {
      return await Promise.all([clusterRef.value!.getValue(), targetCapacityRef.value!.getValue()]).then((data) => {
        const [clusterId, targetCapacity] = data;
        return {
          cluster_id: clusterId,
          ...targetCapacity,
        };
      });
    },
  });
</script>
