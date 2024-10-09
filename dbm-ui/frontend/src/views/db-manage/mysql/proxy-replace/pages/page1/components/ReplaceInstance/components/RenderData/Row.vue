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
      <RenderOriginalProxyInst
        ref="originRef"
        v-model="localInstanceAddress"
        @input-finish="handleOriginProxyInputFinish" />
    </FixedColumn>
    <td style="padding: 0">
      <RenderRelatedClusters
        ref="relatedClustersRef"
        :list="localRelatedClusters" />
    </td>
    <td style="padding: 0">
      <RenderTargetProxy
        ref="targetRef"
        :cloud-id="data.originProxy.bk_cloud_id"
        :disabled="!localInstanceAddress"
        :model-value="data.targetProxy"
        :target-ip="data.originProxy.ip" />
    </td>
    <OperateColumn
      :removeable="removeable"
      @add="handleAppend"
      @remove="handleRemove" />
  </tr>
</template>
<script lang="ts">
  import { random } from '@utils';

  export interface IDataRow {
    rowKey: string;
    originProxy: {
      cluster_id: number;
      ip: string;
      bk_cloud_id: number | null;
      bk_host_id: number;
      bk_biz_id: number;
      port?: number;
      instance_address: string;
    };
    relatedClusters: {
      cluster_id: number;
      domain: string;
    }[];
    targetProxy: {
      ip: string;
      bk_cloud_id: number | null;
      bk_host_id: number;
      bk_biz_id: number;
    };
  }

  interface Props {
    data: IDataRow;
    removeable: boolean;
  }

  interface Emits {
    (e: 'add', params: IDataRow[]): void;
    (e: 'remove'): void;
  }

  interface Exposes {
    getValue: () => Promise<{
      cluster_ids: number[];
      origin_proxy: {
        ip: string;
        bk_cloud_id: number | null;
        bk_host_id: number;
        bk_biz_id: number;
        port?: number;
      };
      target_proxy: {
        ip: string;
        bk_cloud_id: number | null;
        bk_host_id: number;
        bk_biz_id: number;
        port?: number;
      };
    }>;
  }

  // 创建表格数据
  export const createRowData = (data = {} as Partial<IDataRow>) => ({
    rowKey: random(),
    originProxy:
      data.originProxy ||
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
      data.targetProxy ||
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

  import FixedColumn from '@components/render-table/columns/fixed-column/index.vue';
  import OperateColumn from '@components/render-table/columns/operate-column/index.vue';

  import RenderTargetProxy from '../../../common/RenderTargetProxy.vue';
  import RenderOriginalProxyInst from '../RenderOriginalProxyInst.vue';
  import RenderRelatedClusters from '../RenderRelatedClusters.vue';

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const originRef = ref<InstanceType<typeof RenderOriginalProxyInst>>();
  const relatedClustersRef = ref<InstanceType<typeof RenderRelatedClusters>>();
  const targetRef = ref<InstanceType<typeof RenderTargetProxy>>();

  const localInstanceAddress = ref('');
  const localRelatedClusters = ref<IDataRow['relatedClusters']>([]);

  watch(
    () => props.data,
    () => {
      localInstanceAddress.value = props.data.originProxy.instance_address;
    },
    {
      immediate: true,
    },
  );

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

  defineExpose<Exposes>({
    getValue() {
      return Promise.all([
        originRef.value!.getValue(),
        relatedClustersRef.value!.getValue(),
        targetRef.value!.getValue(),
      ]).then(([originData, relatedClustersData, targetData]) => ({
        ...originData,
        ...relatedClustersData,
        ...targetData,
      }));
    },
  });
</script>
