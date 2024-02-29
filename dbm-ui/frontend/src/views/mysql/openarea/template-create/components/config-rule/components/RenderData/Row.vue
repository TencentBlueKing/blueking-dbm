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
        <RenderSourceDb
          ref="sourceDbRef"
          v-model="localRowData.source_db"
          :cluster-id="clusterId" />
      </td>
      <td style="padding: 0">
        <RenderSchmalTable
          ref="schmalTableRef"
          v-model="localRowData.schema_tblist"
          :cluster-id="clusterId"
          :source-db="localRowData.source_db" />
      </td>
      <td style="padding: 0">
        <RenderTableData
          ref="tableDataRef"
          v-model="localRowData.data_tblist"
          :cluster-id="clusterId"
          :source-db="localRowData.source_db" />
      </td>
      <td style="padding: 0">
        <RenderTargetDbPattern
          ref="targetDbPatternRef"
          v-model="localRowData.target_db_pattern" />
      </td>
      <td style="padding: 0">
        <RenderPrivData
          ref="privDataRef"
          v-model="localRowData.priv_data"
          :cluster-id="clusterId" />
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
    source_db: data.source_db || '',
    schema_tblist: data.schema_tblist || [],
    data_tblist: data.data_tblist || [],
    target_db_pattern: data.target_db_pattern || '',
    priv_data: data.priv_data || [],
  });
</script>
<script setup lang="ts">
  import RenderPrivData from './RenderPrivData.vue';
  import RenderSchmalTable from './RenderSchmalTable.vue';
  import RenderSourceDb from './RenderSourceDb.vue';
  import RenderTableData from './RenderTableData.vue';
  import RenderTargetDbPattern from './RenderTargetDbPattern.vue';

  export interface IData {
    source_db: string;
    schema_tblist: string[];
    data_tblist: string[];
    target_db_pattern: string;
    priv_data: number[];
  }

  export interface IDataRow extends IData {
    rowKey: string;
  }

  interface Props {
    data: IDataRow;
    removeable: boolean;
    clusterId: number;
  }

  interface Emits {
    (e: 'add', params: Array<IDataRow>): void;
    (e: 'remove'): void;
  }

  interface Exposes {
    getValue: () => Promise<Required<IData>>;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const sourceDbRef = ref<InstanceType<typeof RenderSourceDb>>();
  const schmalTableRef = ref<InstanceType<typeof RenderSchmalTable>>();
  const tableDataRef = ref<InstanceType<typeof RenderTableData>>();
  const targetDbPatternRef = ref<InstanceType<typeof RenderTargetDbPattern>>();
  const privDataRef = ref<InstanceType<typeof RenderPrivData>>();

  const localRowData = reactive(createRowData());

  watch(
    () => props.data,
    () => {
      Object.assign(localRowData, props.data);
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
        (sourceDbRef.value as InstanceType<typeof RenderSourceDb>).getValue(),
        (schmalTableRef.value as InstanceType<typeof RenderSchmalTable>).getValue(),
        (tableDataRef.value as InstanceType<typeof RenderTableData>).getValue(),
        (targetDbPatternRef.value as InstanceType<typeof RenderTargetDbPattern>).getValue(),
        (privDataRef.value as InstanceType<typeof RenderPrivData>).getValue(),
      ]).then(([sourceDbData, schmalTableData, tableDataData, targetDbPatternData, privDataData]) => ({
        ...sourceDbData,
        ...schmalTableData,
        ...tableDataData,
        ...targetDbPatternData,
        ...privDataData,
      }));
    },
  });
</script>
