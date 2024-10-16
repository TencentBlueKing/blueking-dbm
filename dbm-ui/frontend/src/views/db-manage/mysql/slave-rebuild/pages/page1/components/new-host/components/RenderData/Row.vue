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
      <RenderOldSlave
        ref="slaveRef"
        v-model="localOldSlave" />
    </FixedColumn>
    <td style="padding: 0">
      <RenderCluster
        ref="clusterRef"
        :data="localOldSlave"
        role="slave" />
    </td>
    <td style="padding: 0">
      <RenderNewSlave
        ref="newSlaveRef"
        :new-slave="localNewSlave"
        :old-slave="localOldSlave" />
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
  import type { ComponentExposed } from 'vue-component-type-helpers';

  import FixedColumn from '@components/render-table/columns/fixed-column/index.vue';
  import OperateColumn from '@components/render-table/columns/operate-column/index.vue';

  import RenderCluster from '@views/db-manage/common/RenderRelatedClusters.vue';

  import { random } from '@utils';

  import RenderNewSlave from './RenderNewSlave.vue';
  import RenderOldSlave from './RenderOldSlave.vue';

  export interface IDataRow {
    rowKey: string;
    oldSlave?: {
      bkCloudId: number;
      bkCloudName: string;
      bkHostId: number;
      ip: string;
      port: number;
      instanceAddress: string;
      clusterId: number;
    };
    clusterId?: number;
    newSlave?: {
      bkBizId: number;
      bkCloudId: number;
      bkHostId: number;
      ip: string;
      // port: number;
    };
  }

  // 创建表格数据
  export const createRowData = (data = {} as Partial<IDataRow>) => ({
    rowKey: random(),
    oldSlave: data.oldSlave,
    clusterId: data.clusterId,
    newSlave: data.newSlave,
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
    (e: 'clone', value: IDataRow): void;
  }

  interface Exposes {
    getValue: () => Promise<any>;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const slaveRef = ref<InstanceType<typeof RenderOldSlave>>();
  const clusterRef = ref<ComponentExposed<typeof RenderCluster>>();
  const newSlaveRef = ref<InstanceType<typeof RenderNewSlave>>();

  const localOldSlave = ref<IDataRow['oldSlave']>();
  const localNewSlave = ref<IDataRow['newSlave']>();

  watch(
    () => props.data,
    () => {
      if (props.data) {
        localOldSlave.value = props.data.oldSlave;
        localNewSlave.value = props.data.newSlave;
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

  const getRowData = () => [slaveRef.value!.getValue(), clusterRef.value!.getValue(), newSlaveRef.value!.getValue()];
  const handleClone = () => {
    Promise.allSettled(getRowData()).then((rowData) => {
      const rowInfo = rowData.map((item) => (item.status === 'fulfilled' ? item.value : item.reason));
      const newSlaveData = rowInfo[2];
      emits(
        'clone',
        createRowData({
          oldSlave: localOldSlave.value,
          clusterId: rowInfo[0]?.old_slave.cluster_id,
          newSlave: newSlaveData
            ? {
                bkBizId: newSlaveData.new_slave.bk_biz_id,
                bkCloudId: newSlaveData.new_slave.bk_cloud_id,
                bkHostId: newSlaveData.new_slave.bk_host_id,
                ip: newSlaveData.new_slave.ip,
              }
            : undefined,
        }),
      );
    });
  };

  defineExpose<Exposes>({
    getValue() {
      return Promise.all(getRowData()).then(([sourceData, clusterData, newSlaveData]) => ({
        ...sourceData,
        ...clusterData,
        ...newSlaveData,
      }));
    },
  });
</script>
