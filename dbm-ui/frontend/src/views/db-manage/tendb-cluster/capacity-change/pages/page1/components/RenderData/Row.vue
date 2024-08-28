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
        v-model="localClusterData" />
    </td>
    <td style="padding: 0">
      <RenderResourceSpec
        ref="resourceSpecRef"
        :cluster-data="localClusterData" />
    </td>
    <td style="padding: 0">
      <RenderShardNum
        ref="shardNumRef"
        :cluster-data="localClusterData" />
    </td>
    <td style="padding: 0">
      <RenderMachinePairCnt
        ref="machinePairCntRef"
        :cluster-data="localClusterData" />
    </td>
    <td style="padding: 0">
      <RenderCapacity
        ref="capacityRef"
        :cluster-data="localClusterData" />
    </td>
    <td style="padding: 0">
      <RenderTargetResourceSpec
        ref="targetResourceSpecRef"
        :cluster-data="localClusterData"
        :row-data="data" />
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
      bkCloudId: number;
      clusterCapacity: number;
      clusterShardNum: number;
      clusterSpec: {
        spec_name: string;
      };
      dbModuleId: number;
      id: number;
      machinePairCnt: number;
      masterDomain: string;
      remoteShardNum: number;
    };
    resourceSpec?: {
      id: number;
      name: string;
    };
    resource_spec?: {
      backend_group: {
        spec_id: number;
        count: number;
        affinity: string;
        futureCapacity: number;
        specName: string;
      };
    };
  }

  // 创建表格数据
  export const createRowData = (data = {} as Partial<IDataRow>): IDataRow => ({
    rowKey: random(),
    clusterData: data.clusterData,
    resourceSpec: data.resourceSpec,
    resource_spec: data.resource_spec,
  });
</script>
<script setup lang="ts">
  import { ref, watch } from 'vue';

  import RenderCapacity from './RenderCapacity.vue';
  import RenderCluster from './RenderCluster.vue';
  import RenderMachinePairCnt from './RenderMachinePairCnt.vue';
  import RenderResourceSpec from './RenderResourceSpec.vue';
  import RenderShardNum from './RenderShardNum.vue';
  import RenderTargetResourceSpec from './RenderTargetResourceSpec.vue';

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

  const clusterRef = ref<InstanceType<typeof RenderCluster>>();
  const shardNumRef = ref<InstanceType<typeof RenderShardNum>>();
  const machinePairCntRef = ref<InstanceType<typeof RenderMachinePairCnt>>();
  const capacityRef = ref<InstanceType<typeof RenderCapacity>>();
  const resourceSpecRef = ref<InstanceType<typeof RenderResourceSpec>>();
  const targetResourceSpecRef = ref<InstanceType<typeof RenderTargetResourceSpec>>();

  const localClusterData = ref<IDataRow['clusterData']>();

  watch(
    () => props.data,
    () => {
      if (props.data.clusterData) {
        localClusterData.value = props.data.clusterData;
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

  const getRowData = () => [
    clusterRef.value!.getValue(),
    resourceSpecRef.value!.getValue(),
    targetResourceSpecRef.value!.getValue(),
  ];

  const handleClone = () => {
    Promise.allSettled(getRowData()).then((rowData) => {
      const rowInfo = rowData.map((item) => (item.status === 'fulfilled' ? item.value : item.reason));
      emits(
        'clone',
        createRowData({
          clusterData: localClusterData.value,
          resourceSpec: {
            id: 0,
            name: localClusterData.value?.clusterSpec.spec_name ?? '',
          },
          resource_spec: rowInfo[2].resource_spec,
        }),
      );
    });
  };

  defineExpose<Exposes>({
    getValue() {
      return Promise.all(getRowData()).then(([clusterData, resourceSpecData, targetResourceSpecData]) => ({
        ...clusterData,
        ...targetResourceSpecData,
        prev_machine_pair: props.data.clusterData!.machinePairCnt,
        prev_cluster_spec_name: props.data.clusterData!.clusterSpec.spec_name,
      }));
    },
  });
</script>
