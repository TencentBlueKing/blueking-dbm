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
      <RenderTargetSpec
        ref="specRef"
        :data="data.currentSpec"
        :is-loading="data.isLoading"
        :select-list="selectList" />
    </td>
    <td style="padding: 0">
      <RenderTargetNumber
        ref="numRef"
        :data="data.targetNum"
        :disabled="!data.clusterName"
        :is-loading="data.isLoading"
        :min="data.shardNum" />
    </td>
    <OperateColumn
      :removeable="removeable"
      @add="handleAppend"
      @remove="handleRemove" />
  </tr>
</template>
<script lang="ts">
  import OperateColumn from '@components/render-table/columns/operate-column/index.vue';
  import RenderText from '@components/render-table/columns/text-plain/index.vue';

  import RenderTargetCluster from '@views/mongodb-manage/components/edit-field/ClusterName.vue';
  import type { SpecInfo } from '@views/mongodb-manage/components/edit-field/spec-select/components/Panel.vue';
  import type { IListItem } from '@views/mongodb-manage/components/edit-field/spec-select/components/Select.vue';
  import RenderTargetSpec from '@views/mongodb-manage/components/edit-field/spec-select/Index.vue';

  import { random } from '@utils';

  import RenderTargetNumber from './RenderTargetNumber.vue';

  export interface IDataRow {
    rowKey: string;
    isLoading: boolean;
    clusterName: string;
    clusterId: number;
    shardNum: number;
    machineNum: number;
    currentSpec?: SpecInfo;
    targetNum?: string;
  }

  export interface InfoItem {
    cluster_id: number;
    role: string;
    resource_spec: {
      mongos: {
        spec_id: number;
        count: number;
      };
    };
  }

  // 创建表格数据
  export const createRowData = (): IDataRow => ({
    rowKey: random(),
    isLoading: false,
    clusterName: '',
    shardNum: 0,
    machineNum: 0,
    clusterId: 0,
  });
</script>
<script setup lang="ts">
  interface Props {
    data: IDataRow;
    selectList: IListItem[];
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
  const specRef = ref<InstanceType<typeof RenderTargetSpec>>();
  const numRef = ref<InstanceType<typeof RenderTargetNumber>>();

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
      return await Promise.all([specRef.value!.getValue(), numRef.value!.getValue()]).then((data) => {
        const [specId, targetNum] = data;
        return {
          cluster_id: props.data.clusterId,
          role: 'mongos',
          resource_spec: {
            mongos: {
              spec_id: specId,
              count: (targetNum - props.data.shardNum) * props.data.machineNum,
            },
          },
        };
      });
    },
  });
</script>
