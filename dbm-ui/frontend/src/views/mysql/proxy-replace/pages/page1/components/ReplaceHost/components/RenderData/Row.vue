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
      <RenderOriginalProxy
        ref="targetRef"
        :model-value="data.originProxy?.ip"
        @input-finish="handleOriginProxyInputFinish" />
    </td>
    <td style="padding: 0">
      <RenderRelatedInstances
        ref="relatedInstancesRef"
        :list="localRelatedInstances" />
    </td>
    <td style="padding: 0">
      <RenderTargetProxy
        ref="originRef"
        :cloud-id="data.originProxy?.bk_cloud_id ?? null"
        :disabled="!data.originProxy?.ip"
        :model-value="data.targetProxy"
        :target-ip="data.originProxy?.ip" />
    </td>
    <OperateColumn
      :removeable="removeable"
      @add="handleAppend"
      @remove="handleRemove" />
  </tr>
</template>
<script lang="ts">
  import { random } from '@utils';

  export interface IProxyData {
    ip: string;
    bk_cloud_id: number | null;
    bk_host_id: number;
    bk_biz_id: number;
    port: number;
  }

  export interface IRelatedInstanceItem {
    cluster_id: number;
    instance: string;
  }

  export interface IHostData {
    bk_cloud_id: number | null;
    bk_host_id: number;
    bk_biz_id: number;
    cluster_id: number;
    port: number;
    ip: string;
    instance_address: string;
  }

  export interface IDataRow {
    rowKey: string;
    originProxy?: IProxyData;
    relatedInstances?: IRelatedInstanceItem[];
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
      } as IDataRow['originProxy']),
    relatedInstances: data.relatedInstances || [],
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
  import RenderRelatedInstances from './RenderRelatedInstances.vue';
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
  const relatedInstancesRef = ref();
  const originRef = ref();

  const localRelatedInstances = ref<IDataRow['relatedInstances']>([]);

  const handleOriginProxyInputFinish = (value: IDataRow['relatedInstances']) => {
    localRelatedInstances.value = value;
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
    () => props.data.relatedInstances,
    (newValue) => {
      localRelatedInstances.value = newValue || [];
    },
    {
      immediate: true,
    },
  );

  defineExpose<Exposes>({
    getValue() {
      return Promise.all([
        targetRef.value.getValue(),
        relatedInstancesRef.value.getValue(),
        originRef.value.getValue(),
      ]).then(([targetData, relatedInstancesData, originData]) => ({
        ...targetData,
        ...relatedInstancesData,
        ...originData,
      }));
    },
  });
</script>
