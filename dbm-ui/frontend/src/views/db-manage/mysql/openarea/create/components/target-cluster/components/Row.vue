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
      <ColumnCluster
        ref="clusterRef"
        :model-value="localClusterData"
        @cluster-input-finish="handleClusterInputFinish" />
    </td>
    <td
      v-for="variableName in variableList"
      :key="variableName"
      style="padding: 0">
      <ColumnVariable
        ref="variableRefs"
        :data="data.vars[variableName]"
        :name="variableName" />
    </td>
    <td
      v-if="showIpCloumn"
      style="padding: 0">
      <ColumnHost
        ref="hostRef"
        :cluster-data="localClusterData"
        :data="data.authorizeIps" />
    </td>
    <OperateColumn
      :removeable="removeable"
      show-clone
      @add="handleAppend"
      @clone="handleClone"
      @remove="handleRemove" />
  </tr>
</template>
<script lang="ts">
  import OperateColumn from '@components/render-table/columns/operate-column/index.vue';

  import { random } from '@utils';

  // 创建表格数据
  export const createRowData = (data = {} as Partial<IDataRow>) => ({
    authorizeIps: data.authorizeIps,
    clusterData: data.clusterData,
    rowKey: random(),
    vars: data.vars ?? {},
  });
</script>
<script setup lang="ts">
  import { watch } from 'vue';

  import TendbhaModel from '@services/model/mysql/tendbha';

  import ColumnCluster from './ColumnCluster.vue';
  import ColumnHost from './ColumnHost.vue';
  import ColumnVariable from './ColumnVariable.vue';

  export interface IData {
    authorizeIps?: string[];
    clusterData?: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_cloud_name: string;
      id: number;
      master_domain: string;
    };
    vars: Record<string, string>;
  }

  export interface IDataRow extends IData {
    rowKey: string;
  }

  interface Props {
    data: IDataRow;
    removeable: boolean;
    showIpCloumn: boolean;
    variableList: string[];
  }

  interface Emits {
    (e: 'add', params: Array<IDataRow>): void;
    (e: 'remove'): void;
    (e: 'clone', value: IDataRow): void;
    (e: 'clusterInputFinish', value: TendbhaModel): void;
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

  const handleClusterInputFinish = (value: TendbhaModel) => {
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

  const handleClone = () => {
    Promise.allSettled([
      clusterRef.value!.getValue(true),
      Promise.allSettled(variableRefs.value.map((item) => item.getValue())),
      hostRef.value?.getValue(),
    ]).then((rowData) => {
      const rowInfo = rowData.map((item) => (item.status === 'fulfilled' ? item.value : item.reason));
      emits(
        'clone',
        createRowData({
          authorizeIps: props.showIpCloumn ? rowInfo[2].authorize_ips : [],
          clusterData: props.data.clusterData,
          vars: (rowInfo[1] as PromiseSettledResult<Record<string, string>>[])
            .map<Record<string, string>>((item) => (item.status === 'fulfilled' ? item.value : item.reason))
            .reduce<Record<string, string>>((result, item) => Object.assign(result, item), {}),
        }),
      );
    });
  };

  defineExpose<Exposes>({
    getValue() {
      return Promise.all([
        clusterRef.value!.getValue(true),
        Promise.all(variableRefs.value.map((item) => item.getValue())),
        hostRef.value?.getValue(),
      ]).then(([clusterData, variableData, hostData]) =>
        props.showIpCloumn
          ? {
              ...clusterData,
              ...hostData,
              vars: variableData.reduce((result, item) => Object.assign(result, item), {} as Record<string, string>),
            }
          : {
              ...clusterData,
              authorize_ips: [],
              vars: variableData.reduce((result, item) => Object.assign(result, item), {} as Record<string, string>),
            },
      );
    },
  });
</script>
