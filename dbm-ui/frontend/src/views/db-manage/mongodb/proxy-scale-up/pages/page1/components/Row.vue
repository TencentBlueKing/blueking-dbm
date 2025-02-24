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
        :is-loading="data.isLoading" />
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

  import RenderTargetCluster from '@views/db-manage/mongodb/components/edit-field/ClusterName.vue';
  import type { SpecInfo } from '@views/db-manage/mongodb/components/edit-field/spec-select/components/Panel.vue';
  import type { IListItem } from '@views/db-manage/mongodb/components/edit-field/spec-select/components/Select.vue';
  import RenderTargetSpec from '@views/db-manage/mongodb/components/edit-field/spec-select/Index.vue';

  import { random } from '@utils';

  import RenderTargetNumber from './RenderTargetNumber.vue';

  export interface IDataRow {
    clusterId: number;
    clusterName: string;
    // mongosNum: number;
    currentSpec?: SpecInfo;
    isLoading: boolean;
    machineNum: number;
    rowKey: string;
    shardNum: number;
    targetNum?: string;
  }

  export interface InfoItem {
    cluster_id: number;
    resource_spec: {
      mongos: {
        count: number;
        spec_id: number;
      };
    };
    role: string;
  }

  // 创建表格数据
  export const createRowData = (): IDataRow => ({
    clusterId: 0,
    clusterName: '',
    isLoading: false,
    machineNum: 0,
    rowKey: random(),
    shardNum: 0,
    // mongosNum: 0,
  });
</script>
<script setup lang="ts">
  interface Props {
    data: IDataRow;
    removeable: boolean;
    selectList: IListItem[];
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
          resource_spec: {
            mongos: {
              count: targetNum,
              spec_id: specId,
            },
          },
          role: 'mongos',
        };
      });
    },
  });
</script>
