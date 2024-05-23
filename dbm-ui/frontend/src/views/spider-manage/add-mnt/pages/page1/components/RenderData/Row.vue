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
        <RenderCluster
          ref="clusterRef"
          :model-value="data.clusterData"
          @id-change="handleClusterIdChange"
          @input-create="handleCreate" />
      </td>
      <td style="padding: 0">
        <RenderNet
          ref="netRef"
          :cluster-id="localClusterId"
          @cluster-change="handleClusterDataChange" />
      </td>
      <td style="padding: 0">
        <RenderHost
          ref="proxyRef"
          :cluster-data="localClusterData"
          :cluster-id="localClusterId" />
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

  export interface IHostData {
    bk_host_id: number;
    bk_cloud_id: number;
    ip: string;
  }

  export interface IDataRow {
    rowKey: string;
    clusterData?: {
      id: number;
      domain: string;
    };
    bkCloudId?: number;
    spiderIpList?: {
      ip: string;
      bk_cloud_id: number;
      bk_host_id: number;
    }[];
  }

  // 创建表格数据
  export const createRowData = (data = {} as Partial<IDataRow>) => ({
    rowKey: random(),
    clusterData: data.clusterData,
    bkCloudId: data.bkCloudId,
    spiderIpList: data.spiderIpList,
  });
</script>
<script setup lang="ts">
  import type SpiderModel from '@services/model/spider/spider';

  import RenderCluster from './RenderCluster.vue';
  import RenderHost from './RenderHost.vue';
  import RenderNet from './RenderNet.vue';

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

  const clusterRef = ref();
  const netRef = ref();
  const proxyRef = ref();

  const localClusterId = ref(0);
  const localClusterData = ref<SpiderModel>();

  watch(
    () => props.data,
    () => {
      if (props.data.clusterData) {
        localClusterId.value = props.data.clusterData.id;
      }
    },
    {
      immediate: true,
    },
  );
  const handleClusterIdChange = (id: number) => {
    localClusterId.value = id;
  };
  const handleClusterDataChange = (data: SpiderModel) => {
    localClusterData.value = data;
  };
  const handleCreate = (list: Array<string>) => {
    emits(
      'add',
      list.map((domain) =>
        createRowData({
          clusterData: {
            id: 0,
            domain,
          },
        }),
      ),
    );
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
      return Promise.all([clusterRef.value.getValue(), netRef.value.getValue(), proxyRef.value.getValue()]).then(
        ([clusterData, netData, proxyData]) => ({
          ...clusterData,
          ...netData,
          ...proxyData,
        }),
      );
    },
  });
</script>
