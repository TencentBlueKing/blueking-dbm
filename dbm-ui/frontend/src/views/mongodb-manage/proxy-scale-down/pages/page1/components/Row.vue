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
      <RenderTargetCluster
        ref="clusterRef"
        :data="data.clusterName"
        @input-finish="handleInputFinish" />
    </td>
    <td style="padding: 0">
      <RenderText data="mongos" />
    </td>
    <td style="padding: 0">
      <RenderSpec
        :data="data.currentSpec"
        :is-loading="data.isLoading" />
    </td>
    <td style="padding: 0">
      <RenderTargetNumber
        ref="targetNumRef"
        :data="data.targetNum"
        :disabled="!data.clusterName"
        :is-loading="data.isLoading"
        :max="data.currentSpec?.count"
        @change="handleReduceNumChange" />
    </td>
    <td style="padding: 0">
      <RenderIpSelect
        ref="selectRef"
        :disabled="!data.clusterName || !reduceNum"
        :is-check-affinity="data.affinity === 'CROS_SUBZONE'"
        :is-loading="data.isLoading"
        :max="reduceNum"
        :select-list="data.reduceIpList" />
    </td>
    <OperateColumn
      :removeable="removeable"
      @add="handleAppend"
      @remove="handleRemove" />
  </tr>
</template>
<script lang="ts">
  import OperateColumn from '@components/render-table/columns/operate-column/index.vue';
  import RenderSpec from '@components/render-table/columns/spec-display/Index.vue';
  import type { SpecInfo } from '@components/render-table/columns/spec-display/Panel.vue';
  import RenderText from '@components/render-table/columns/text-plain/index.vue';

  import RenderTargetCluster from '@views/mongodb-manage/components/edit-field/ClusterName.vue';

  import { random } from '@utils';

  import RenderIpSelect, { type IListItem } from './RenderIpSelect.vue';
  import RenderTargetNumber from './RenderTargetNumber.vue';

  export interface IDataRow {
    rowKey: string;
    isLoading: boolean;
    clusterName: string;
    clusterId: number;
    shardNum: number;
    machineNum: number;
    reduceIpList: IListItem[];
    affinity: string;
    currentSpec?: SpecInfo;
    targetNum?: string;
  }

  export interface InfoItem {
    cluster_id: number;
    role: string;
    reduce_nodes: {
      ip: string;
      bk_cloud_id: number;
      bk_host_id: number;
    }[];
  }

  // 创建表格数据
  export const createRowData = (): IDataRow => ({
    rowKey: random(),
    isLoading: false,
    clusterName: '',
    clusterId: 0,
    shardNum: 0,
    machineNum: 0,
    reduceIpList: [],
    affinity: '',
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
    (e: 'clusterInputFinish', value: string): void;
  }

  interface Exposes {
    getValue: () => Promise<InfoItem>;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const clusterRef = ref<InstanceType<typeof RenderTargetCluster>>();
  const targetNumRef = ref<InstanceType<typeof RenderTargetNumber>>();
  const selectRef = ref<InstanceType<typeof RenderIpSelect>>();

  const reduceNum = ref<number>();

  const handleReduceNumChange = (value: number) => {
    if (props.data.currentSpec?.count) {
      reduceNum.value = props.data.currentSpec.count - value;
      return;
    }
    reduceNum.value = value;
  };

  const handleInputFinish = (value: string) => {
    emits('clusterInputFinish', value);
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
    async getValue() {
      await clusterRef.value!.getValue();
      await targetNumRef.value!.getValue();
      return selectRef.value!.getValue().then((data) => ({
        cluster_id: props.data.clusterId,
        role: 'mongos',
        ...data,
      }));
    },
  });
</script>
