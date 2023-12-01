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
      <td style="padding: 0;">
        <RenderCluster
          ref="clusterRef"
          :inputed-clusters="inputedClusters"
          :model-value="data.clusterData"
          @input-cluster-finish="handleInputFinish"
          @input-create="handleCreate" />
      </td>
      <td style="padding: 0;">
        <RenderBackupLocal
          ref="backupLocalRef"
          :cluster-data="data.clusterData"
          :model-value="data.backupLocal" />
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

  export interface IDataRow {
    rowKey: string;
    clusterData?: {
      id: number,
      domain: string,
    },
    backupLocal: string,
  }

  // 创建表格数据
  export const createRowData = (data = {} as Partial<IDataRow>): IDataRow => ({
    rowKey: random(),
    clusterData: data.clusterData,
    backupLocal: data.backupLocal || '',
  });

</script>
<script setup lang="ts">
  import RenderBackupLocal from './RenderBackupLocal.vue';
  import RenderCluster from './RenderCluster.vue';

  interface Props {
    data: IDataRow,
    removeable: boolean,
    inputedClusters?: string[]
  }
  interface Emits {
    (e: 'add', params: Array<IDataRow>): void,
    (e: 'remove'): void,
    (e: 'inputClusterFinish', value: IDataRow): void,
  }

  interface Exposes{
    getValue: () => Promise<any>
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const clusterRef = ref();
  const backupLocalRef = ref();

  const handleCreate = (list: Array<string>) => {
    emits('add', list.map(domain => createRowData({
      clusterData: {
        id: 0,
        domain,
      },
    })));
  };

  const handleInputFinish = (domain: string) => {
    emits('inputClusterFinish', createRowData({
      clusterData: {
        id: 0,
        domain,
      },
    }));
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
        clusterRef.value.getValue(),
        backupLocalRef.value.getValue(),
      ]).then(([
        clusterData,
        backupLocalData,
      ]) => ({
        ...clusterData,
        ...backupLocalData,
      }));
    },
  });
</script>
