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
      <td style="padding: 0">
        <RenderOriginalProxy
          ref="targetRef"
          :model-value="data.originProxy?.instance_address"
          @input-finish="handleOriginProxyInputFinish" />
      </td>
      <td style="padding: 0">
        <RenderRelatedClusters
          ref="relatedClustersRef"
          :list="localRelatedClusters" />
      </td>
      <td style="padding: 0">
        <RenderTargetProxy
          ref="originRef"
          :cloud-id="data.originProxy?.bk_cloud_id ?? null"
          :disabled="!data.originProxy?.instance_address"
          :model-value="data.targetProxy"
          :target-ip="data.originProxy?.ip" />
      </td>
      <td>
        <div class="action-box">
          <div
            class="action-btn"
            @click="handleAppend">
            <DbIcon type="plus-fill" />
          </div>
          <div
            class="action-btn"
            :class="{
              disabled: removeable,
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
  import { random } from '@utils';

  export interface IProxyData {
    cluster_id: number;
    ip: string;
    bk_cloud_id: number | null;
    bk_host_id: number;
    bk_biz_id: number;
    port: number;
    instance_address: string;
  }

  export interface IRelatedClusterItem {
    cluster_id: number;
    domain: string;
  }

  export interface IHostData {
    ip: string;
    bk_cloud_id: number | null;
    bk_host_id: number;
    bk_biz_id: number;
  }

  export interface IDataRow {
    rowKey: string;
    originProxy?: IProxyData;
    relatedClusters?: IRelatedClusterItem[];
    targetProxy?: IHostData;
  }

  // 创建表格数据
  export const createRowData = (data = {} as Partial<IDataRow>) => ({
    rowKey: random(),
    originProxy:
      data.originProxy ??
      ({
        ip: '',
        bk_cloud_id: null,
        bk_host_id: 0,
        bk_biz_id: 0,
        port: 0,
        instance_address: '',
      } as IDataRow['originProxy']),
    relatedClusters: data.relatedClusters || [],
    targetProxy:
      data.targetProxy ??
      ({
        ip: '',
        bk_cloud_id: null,
        bk_host_id: 0,
        bk_biz_id: 0,
        port: 0,
      } as IDataRow['targetProxy']),
  });
</script>
<script setup lang="ts">
  import { ref } from 'vue';

  import RenderOriginalProxy from './RenderOriginalProxy.vue';
  import RenderRelatedClusters from './RenderRelatedClusters.vue';
  import RenderTargetProxy from './RenderTargetProxy.vue';

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

  const targetRef = ref();
  const relatedClustersRef = ref();
  const originRef = ref();

  const localRelatedClusters = ref<IDataRow['relatedClusters']>([]);

  const handleOriginProxyInputFinish = (value: IDataRow['relatedClusters']) => {
    localRelatedClusters.value = value;
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

  watch(
    () => props.data.relatedClusters,
    (newValue) => {
      localRelatedClusters.value = newValue || [];
    },
    {
      immediate: true,
    },
  );

  defineExpose<Exposes>({
    getValue() {
      return Promise.all([
        targetRef.value.getValue(),
        relatedClustersRef.value.getValue(),
        originRef.value.getValue(),
      ]).then(([targetData, relatedClustersData, originData]) => ({
        ...targetData,
        ...relatedClustersData,
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
