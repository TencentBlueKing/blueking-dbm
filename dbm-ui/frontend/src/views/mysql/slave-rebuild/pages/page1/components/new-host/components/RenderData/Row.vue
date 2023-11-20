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
      <td style="padding: 0;">
        <RenderOldSlave
          ref="slaveRef"
          v-model="localOldSlave" />
      </td>
      <td style="padding: 0;">
        <RenderCluster
          ref="clusterRef"
          :old-slave="localOldSlave" />
      </td>
      <td style="padding: 0;">
        <RenderNewSlave
          ref="newSlaveRef"
          :old-slave="localOldSlave" />
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

  import RenderCluster from './RenderCluster.vue';
  import RenderNewSlave from './RenderNewSlave.vue';
  import RenderOldSlave from './RenderOldSlave.vue';

  export interface IDataRow {
    rowKey: string;
    oldSlave?: {
      bkCloudId: number,
      bkCloudName: string,
      bkHostId: number,
      ip: string,
      port: number,
      instanceAddress: string,
      clusterId: number,
    },
    clusterId?: number,
    newSlave?: {
      bkCloudId: number,
      bkHostId: number,
      ip: string,
      port: number,
    }
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
    data: IDataRow,
    removeable: boolean,
  }
  interface Emits {
    (e: 'add', params: Array<IDataRow>): void,
    (e: 'remove'): void,
  }

  interface Exposes{
    getValue: () => Promise<any>
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const slaveRef = ref();
  const clusterRef = ref();
  const newSlaveRef = ref();

  const localOldSlave = ref<IDataRow['oldSlave']>();

  watch(() => props.data, () => {
    if (props.data) {
      localOldSlave.value = props.data.oldSlave;
    }
  }, {
    immediate: true,
  });

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
        slaveRef.value.getValue('master_ip'),
        clusterRef.value.getValue(),
        newSlaveRef.value.getValue(),
      ]).then(([sourceData, moduleData, newSlaveData]) => ({
        ...sourceData,
        ...moduleData,
        ...newSlaveData,
      }));
    },
  });
</script>

