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
      <RenderMaster
        ref="masterHostRef"
        :model-value="localMasterData"
        @change="handleMasterHostChange" />
    </td>
    <td style="padding: 0">
      <RenderHost
        ref="slaveHostRef"
        :master-data="localMasterData"
        :model-value="data.slaveData" />
    </td>
    <td style="padding: 0">
      <RenderCluster
        ref="clusterRef"
        :data="localMasterData" />
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

  import OperateColumn from '@components/render-table/columns/operate-column/index.vue';

  import RenderCluster from '@views/db-manage/common/RenderRelatedClusters.vue';

  import { random } from '@utils';

  import RenderMaster from './RenderMaster.vue';
  import RenderHost from './RenderSlave.vue';

  export type IHostData = {
    bk_host_id: number;
    bk_cloud_id: number;
    ip: string;
  };

  export interface IDataRow {
    rowKey: string;
    masterData?: IHostData;
    slaveData?: IHostData;
    clusterData?: {
      id: number;
      domain: string;
    };
  }

  // 创建表格数据
  export const createRowData = (data = {} as Partial<IDataRow>) => ({
    rowKey: random(),
    masterData: data.masterData,
    slaveData: data.slaveData,
    clusterData: data.clusterData,
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

  const masterHostRef = ref<InstanceType<typeof RenderMaster>>();
  const slaveHostRef = ref<InstanceType<typeof RenderHost>>();
  const clusterRef = ref<ComponentExposed<typeof RenderCluster>>();

  const localMasterData = ref<IHostData>();

  watch(
    () => props.data,
    () => {
      localMasterData.value = props.data.masterData;
    },
    {
      immediate: true,
    },
  );

  const handleMasterHostChange = (data: IHostData) => {
    localMasterData.value = data;
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
      masterHostRef.value!.getValue(),
      slaveHostRef.value!.getValue(),
      clusterRef.value!.getValue(),
    ]).then((rowData) => {
      const [masterHostData, slaveHostData, clusterData] = rowData.map((item) =>
        item.status === 'fulfilled' ? item.value : item.reason,
      );
      emits(
        'clone',
        createRowData({
          masterData: masterHostData.master,
          slaveData: slaveHostData.slave,
          clusterData: {
            id: clusterData.cluster_ids[0],
            domain: '',
          },
        }),
      );
    });
  };

  defineExpose<Exposes>({
    getValue() {
      return Promise.all([
        masterHostRef.value!.getValue(),
        slaveHostRef.value!.getValue(),
        clusterRef.value!.getValue(),
      ]).then(([masterHostData, slaveHostData, clusterData]) => ({
        cluster_id: clusterData.cluster_ids[0],
        switch_tuples: [
          {
            ...masterHostData,
            ...slaveHostData,
          },
        ],
      }));
    },
  });
</script>
