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
      <FixedColumn fixed="left">
        <RenderMaster
          ref="masterHostRef"
          :model-value="data.masterData"
          @change="handleMasterHostChange" />
      </FixedColumn>
      <td style="padding: 0">
        <RenderHost
          ref="slaveHostRef"
          :cluster-list="localClusterIdList"
          :model-value="data.slaveData" />
      </td>
      <td style="padding: 0">
        <RenderCluster
          ref="clusterRef"
          :data="localMasterData"
          @change="handleClusterChange" />
      </td>
      <OperateColumn
        :removeable="removeable"
        @add="handleAppend"
        @remove="handleRemove" />
    </tr>
  </tbody>
</template>
<script lang="ts">
  import { ref, shallowRef, watch } from 'vue';
  import type { ComponentExposed } from 'vue-component-type-helpers';

  import FixedColumn from '@components/render-table/columns/fixed-column/index.vue';
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
    clusterIdList: number[];
  }

  // 创建表格数据
  export const createRowData = (data = {} as Partial<IDataRow>) => ({
    rowKey: random(),
    masterData: data.masterData,
    slaveData: data.slaveData,
    clusterIdList: data.clusterIdList || [],
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
  const localClusterIdList = shallowRef<number[]>([]);

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

  const handleClusterChange = (data: number[]) => {
    localClusterIdList.value = data;
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
        masterHostRef.value!.getValue(),
        slaveHostRef.value!.getValue(),
        clusterRef.value!.getValue(),
      ]).then(([masterHostData, slaveHostData, clusterData]) => ({
        ...masterHostData,
        ...slaveHostData,
        ...clusterData,
      }));
    },
  });
</script>
<style lang="less" scoped>
  .action-box {
    display: flex;
    align-items: center;

    .action-btn {
      display: flex;
      font-size: 14px;
      color: #c4c6cc;
      cursor: pointer;
      transition: all 0.15s;

      &:hover {
        color: #979ba5;
      }

      &.disabled {
        color: #dcdee5;
        cursor: not-allowed;
      }

      & ~ .action-btn {
        margin-left: 18px;
      }
    }
  }
</style>
