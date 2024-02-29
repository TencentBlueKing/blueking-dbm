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
        <ColumnCluster
          ref="clusterRef"
          :model-value="localClusterData" />
      </td>
      <ColumnVariable
        v-for="variableName in variableList"
        :key="variableName"
        ref="variableRefs"
        :name="variableName" />
      <td style="padding: 0">
        <ColumnHost
          ref="hostRef"
          :cluster-data="localClusterData" />
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

  // 创建表格数据
  export const createRowData = (data = {} as Partial<IDataRow>) => ({
    rowKey: random(),
    clusterData: data.clusterData,
    vars: data.vars,
    authorizeIps: data.authorizeIps,
  });
</script>
<script setup lang="ts">
  import { watch } from 'vue';

  import ColumnCluster from './ColumnCluster.vue';
  import ColumnHost from './ColumnHost.vue';
  import ColumnVariable from './ColumnVariable.vue';

  export interface IData {
    clusterData?: {
      id: number;
      master_domain: string;
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_cloud_name: string;
    };
    vars?: Record<string, string>;
    authorizeIps?: string[];
  }

  export interface IDataRow extends IData {
    rowKey: string;
  }

  interface Props {
    data: IDataRow;
    removeable: boolean;
    variableList: string[];
  }

  interface Emits {
    (e: 'add', params: Array<IDataRow>): void;
    (e: 'remove'): void;
  }

  interface Exposes {
    getValue: () => Promise<Record<string, any>>;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const clusterRef = ref<InstanceType<typeof ColumnCluster>>();
  const variableRefs = ref<InstanceType<typeof ColumnVariable>[]>([]);
  const hostRef = ref<InstanceType<typeof ColumnHost>>();

  const localClusterData = ref<IData['clusterData']>();

  watch(
    () => props.data,
    () => {
      localClusterData.value = props.data.clusterData;
    },
    {
      immediate: true,
    },
  );

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
        (clusterRef.value as InstanceType<typeof ColumnCluster>).getValue(),
        Promise.all(variableRefs.value.map((item) => item.getValue())),
        (hostRef.value as InstanceType<typeof ColumnHost>).getValue(),
      ]).then(([clusterData, variableData, hostData]) => ({
        ...clusterData,
        ...hostData,
        vars: variableData.reduce((result, item) => Object.assign(result, item), {} as Record<string, string>),
      }));
    },
  });
</script>
