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
        <RenderSource
          ref="sourceRef"
          v-model:cluser-id="localClusterId"
          :model-value="data.source" />
      </td>
      <td style="padding: 0;">
        <RenderCluster
          ref="clusterRef"
          v-model:clusterData="localClusterData"
          :cluster-id="localClusterId" />
      </td>
      <td style="padding: 0;">
        <RenderModule :cluster-data="localClusterData" />
      </td>
      <td style="padding: 0;">
        <RenderTarget
          ref="targetRef"
          :cloud-id="localClusterId"
          :cluster-data="localClusterData"
          :model-value="data.target" />
      </td>
      <td :class="{'shadow-column': isFixed}">
        <div class="action-box">
          <div
            class="action-btn"
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
  import {  random } from '@utils';

  export interface IProxyData {
    cluster_id: number,
    bk_host_id: number,
    bk_cloud_id: number,
    port: number,
    ip: string,
    instance_address: string
  }

  export interface IDataRow {
    rowKey: string;
    source?: IProxyData,
    target?: IProxyData
  }

  // 创建表格数据
  export const createRowData = (data = {} as Partial<IDataRow>) => ({
    rowKey: random(),
    source: data.source,
    target: data.target,
  });

</script>
<script setup lang="ts">
  import type SpiderModel from '@services/model/spider/spider';

  import RenderCluster from './RenderCluster.vue';
  import RenderModule from './RenderModule.vue';
  import RenderSource from './RenderSource.vue';
  import RenderTarget from './RenderTarget.vue';

  interface Props {
    data: IDataRow,
    removeable: boolean,
    isFixed?: boolean,
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

  const sourceRef = ref();
  const clusterRef = ref();
  const targetRef = ref();

  const localClusterId = ref(0);
  const localClusterData = ref<SpiderModel>();

  watch(() => props.data, () => {
    if (props.data.source) {
      localClusterId.value = props.data.source.cluster_id;
    }
  }, {
    immediate: true,
  });

  watch(localClusterId, () => {
    localClusterData.value = undefined;
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
        sourceRef.value.getValue(),
        clusterRef.value.getValue(),
        targetRef.value.getValue(),
      ]).then(([targetData, clusterData, originData]) => ({
        ...targetData,
        ...clusterData,
        ...originData,
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
