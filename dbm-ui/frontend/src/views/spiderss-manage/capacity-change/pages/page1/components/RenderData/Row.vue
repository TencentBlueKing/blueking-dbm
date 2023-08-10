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
      <td
        style="padding: 0;">
        <RenderCluster
          ref="clusterRef"
          :model-value="data.clusterData"
          @id-change="handleClusterIdChange" />
      </td>
      <td
        style="padding: 0;">
        <RenderResourceSpec
          ref="resourceSpecRef"
          :cluster-id="localClusterId"
          @cluster-change="handleClusterDataChange" />
      </td>
      <td style="padding: 0;">
        <RenderShardNum :cluster-data="localClusterData" />
      </td>
      <td style="padding: 0;">
        <RenderMachinePairCnt :cluster-data="localClusterData" />
      </td>
      <td style="padding: 0;">
        <RenderCapacity :cluster-data="localClusterData" />
      </td>
      <td style="padding: 0;">
        <RenderTargetResourceSpec
          ref="targetResourceSpecRef"
          :cluster-data="localClusterData" />
      </td>
      <td>
        <div class="action-box">
          <div
            class="action-btn ml-2"
            @click="handleAppend">
            <DbIcon type="plus-fill" />
          </div>
          <div
            class="action-btn"
            :class="{
              disabled: removeable
            }"
            @click="handleRemove">
            <DbIcon type="minus-fill" />
          </div>
        </div>
      </td>
    </tr>
  </tbody>
</template>
<script lang="ts">
  import SpiderModel from '@services/model/spider/spider';

  import { random } from '@utils';

  export interface IDataRow {
    rowKey: string;
    clusterData?: {
      id: number,
      domain: string,
    },
    resourceSpec?: {
      id: number,
      name: string,
    },
    clusterShardNum?: number,
    clusterCapacity?: string,
    machinePairCnt?: number,
    resource_spec?: {
      backend_group: {
        spec_id: number,
        count: number,
        affinity: ''
      }
    },
  }

  // 创建表格数据
  export const createRowData = (data = {} as Partial<IDataRow>): IDataRow => ({
    rowKey: random(),
    clusterData: data.clusterData,
    resourceSpec: data.resourceSpec,
    clusterShardNum: data.clusterShardNum,
    clusterCapacity: data.clusterCapacity,
    machinePairCnt: data.machinePairCnt,
    resource_spec: data.resource_spec,
  });

</script>
<script setup lang="ts">
  import {
    ref,
    watch,
  } from 'vue';

  import RenderCapacity from './RenderCapacity.vue';
  import RenderCluster from './RenderCluster.vue';
  import RenderMachinePairCnt from './RenderMachinePairCnt.vue';
  import RenderResourceSpec from './RenderResourceSpec.vue';
  import RenderShardNum from './RenderShardNum.vue';
  import RenderTargetResourceSpec from './RenderTargetResourceSpec.vue';

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

  const clusterRef = ref();
  const resourceSpecRef = ref();
  const targetResourceSpecRef = ref();

  const localClusterId = ref(0);
  const localClusterData = ref<SpiderModel>();

  watch(() => props.data, () => {
    if (props.data.clusterData) {
      localClusterId.value = props.data.clusterData.id;
    }
  }, {
    immediate: true,
  });

  const handleClusterIdChange = (clusterId: number) => {
    localClusterId.value = clusterId;
  };
  const handleClusterDataChange = (clusterData: SpiderModel) => {
    localClusterData.value = clusterData;
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
        clusterRef.value.getValue(),
        resourceSpecRef.value.getValue(),
        targetResourceSpecRef.value.getValue(),
      ]).then(([
        clusterData,
        resourceSpecData,
        targetResourceSpecData,
      ]) => ({
        ...clusterData,
        ...resourceSpecData,
        ...targetResourceSpecData,
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
