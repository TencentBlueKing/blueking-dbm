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
        :model-value="data"
        @id-change="handleClusterIdChange" />
    </td>
    <td style="padding: 0">
      <RenderSlaveHost
        ref="hostRef"
        :cloud-id="cloudId"
        :disabled="!localClusterId"
        :domain="data.clusterData?.domain"
        :model-value="data.newSlaveIp" />
    </td>
    <OperateColumn
      :removeable="removeable"
      @add="handleAppend"
      @remove="handleRemove" />
  </tr>
</template>
<script lang="ts">
  import TendbhaModel from '@services/model/mysql/tendbha';

  import OperateColumn from '@components/render-table/columns/operate-column/index.vue';

  import { random } from '@utils';

  export interface IHostData {
    bk_biz_id: number;
    bk_host_id: number;
    ip: string;
    bk_cloud_id: number;
  }
  export interface IDataRow {
    rowKey: string;
    clusterData?: {
      id: number;
      domain: string;
      cloudId: number | null;
    };
    clusterRelated: TendbhaModel[];
    checkedRelated: TendbhaModel[];
    newSlaveIp: string;
  }

  // 创建表格数据
  export const createRowData = (data = {} as Partial<IDataRow>) => ({
    rowKey: random(),
    clusterData: data.clusterData,
    clusterRelated: data.clusterRelated ?? [],
    checkedRelated: data.checkedRelated ?? [],
    newSlaveIp: data.newSlaveIp ?? '',
  });
</script>
<script setup lang="ts">
  import RenderCluster from './render-cluster/Index.vue';
  import RenderSlaveHost from './RenderSlaveHost.vue';

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

  const clusterRef = ref<InstanceType<typeof RenderSlaveHost>>();
  const hostRef = ref<InstanceType<typeof RenderSlaveHost>>();
  const localClusterId = ref(0);

  const cloudId = ref<number | null>(null);

  watch(
    () => props.data,
    () => {
      if (props.data.clusterData) {
        localClusterId.value = props.data.clusterData.id;
        cloudId.value = props.data.clusterData.cloudId;
      }
    },
    {
      immediate: true,
    },
  );

  const handleClusterIdChange = (idData: { id: number; cloudId: number | null }) => {
    localClusterId.value = idData.id;
    cloudId.value = idData.cloudId;
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
      return Promise.all([clusterRef.value!.getValue(), hostRef.value!.getValue()]).then(([clusterData, hostData]) => ({
        ...clusterData,
        ...hostData,
      }));
    },
  });
</script>
